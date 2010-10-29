"""
mcm_amss ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app
from lib import index_dict
from lib import image
from lib import build
from lib import http
from lib.misc import get_check_key, ctime
import os.path
import time
import shutil
import cherrypy
from cherrypy import TimeoutError


class app(base_app):
    """ mcm_amss app """

    title = "Finite Difference Schemes for MCM and AMSS"

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.tiff' # input image expected extension (ie file format)
    is_test = True

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

       # select the base_app steps to expose
        # index() is generic
        base_app.index.im_func.exposed = True
        # input_xxx() are modified from the template
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True


    def build(self):
        """
        program build/update
        """
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        # MCM
        # store common file path in variables
        mcm_tgz_file = self.dl_dir + "fds_mcm.tar.gz"
        mcm_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_mcm.tar.gz"
        mcm_prog_file = self.bin_dir + "mcm"
        mcm_log = self.base_dir + "build_mcm.log"
        # get the latest source archive
        build.download(mcm_tgz_url, mcm_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(mcm_prog_file)
            and ctime(mcm_tgz_file) < ctime(mcm_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(mcm_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s mcm"
                      % (self.src_dir + os.path.join("fds_mcm", "mcm"))
                      + " CC='ccache cc'"
                      + " OMP=1 -j4", stdout=mcm_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_mcm", "mcm", "mcm"),
                        mcm_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        # AMSS
        # store common file path in variables
        amss_tgz_file = self.dl_dir + "fds_amss.tar.gz"
        amss_tgz_url = \
            "http://www.ipol.im/pub/algo/cm_fds_mcm_amss/fds_amss.tar.gz"
        amss_prog_file = self.bin_dir + "amss"
        amss_log = self.base_dir + "build_amss.log"
        # get the latest source archive
        build.download(amss_tgz_url, amss_tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(amss_prog_file)
            and ctime(amss_tgz_file) < ctime(amss_prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(amss_tgz_file, self.src_dir)
            # build the program
            build.run("make -C %s amss"
                      % (self.src_dir + os.path.join("fds_amss", "amss"))
                      + " CC='ccache cc'"
                      + " OMP=1 -j4", stdout=amss_log)
            # save into bin dir
            shutil.copy(self.src_dir + os.path.join("fds_amss", "amss", "amss"),
                        amss_prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @get_check_key
    def grid(self, step, scaleR, grid_step=0, action=None, x=0, y=0):
        """
        handle the grid drawing and selection
        """
        if action == 'Run':
            # use the whole image
            img = image(self.key_dir + 'input_0.png')
            img.save(self.key_dir + 'input' + self.input_ext)
            img.save(self.key_dir + 'input.png')
            # go to the wait page, with the key and scale
            http.redir_303(self.base_url
                           + "wait?key=%s&scaleR=%s&step=%s" 
                           % (self.key, scaleR, step))
            return
        elif action == 'Redraw':
            # draw the grid
            step = int(step)
            if 0 < step:
                img = image(self.key_dir + 'input_0.png')
                img.draw_grid(step)
                img.save(self.key_dir + 'input_grid.png')
                input=[self.key_url + 'input_grid.png'
                       + '?step=%i' % step]
                grid=True
            else:
                input=[self.key_url + 'input_0.png']
                grid=False
            return self.tmpl_out("params.html",
                                 input=input, step=step, grid=grid)
        else:
            # use a part of the image
            x = int(x)
            y = int(y)
            # get the step used to draw the grid
            step = int(grid_step)
            assert step > 0
            # cut the image section
            img = image(self.key_dir + 'input_0.png')
            x0 = (x / step) * step
            y0 = (y / step) * step
            x1 = min(img.size[0], x0 + step)
            y1 = min(img.size[1], y0 + step)
            img.crop((x0, y0, x1, y1))
            # zoom and save image
            img.resize((400, 400), method="nearest")
            img.save(self.key_dir + 'input' + self.input_ext)
            img.save(self.key_dir + 'input.png')
            # go to the wait page, with the key and scale
            http.redir_303(self.base_url
                           + "wait?key=%s&scaleR=%s&step=%s" 
                           % (self.key, scaleR, step))
            return

    #
    # EXECUTION AND RESULTS
    #

    @cherrypy.expose
    @get_check_key
    def wait(self, scaleR, step):
        """
        params handling and run redirection
        """
        # read parameters
        try:
            params_file = index_dict(self.key_dir)
            params_file['params'] = {'scale_r' : float(scaleR),
                                     'grid_step' : int(step),
                                     'zoom_factor' : (400.0 / int(step)
                                                      if int(step) > 0
                                                      else 1.)}
            params_file.save()
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="Wrong input parameters")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",
                             input=[self.key_url
                                    + 'input.png?step=%s' % step])

    @cherrypy.expose
    @get_check_key
    def run(self):
        """
        algo execution
        """
        # read the parameters
        params_file = index_dict(self.key_dir)
        scale_r = float(params_file['params']['scale_r'])
        grid_step = int(params_file['params']['grid_step'])
        zoom_factor = float(params_file['params']['zoom_factor'])

        # denormalize the scale
        scale_r *= zoom_factor

        # run the algorithm
        stdout = open(self.key_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(scale_r, stdout=stdout)
            params_file['params']['run_time'] = time.time() - run_time
            params_file.save()
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")

    def run_algo(self, scale_r, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """             

        # process image
        p1 = self.run_proc(['mcm', str(scale_r),
                            self.key_dir + 'input' + self.input_ext,
                            self.key_dir + 'output_MCM' + self.input_ext])
        p2 = self.run_proc(['amss', str(scale_r),
                            self.key_dir + 'input' + self.input_ext, 
                            self.key_dir + 'output_AMSS' + self.input_ext]) 
        self.wait_proc([p1, p2], timeout)
        im = image(self.key_dir + 'output_MCM' + self.input_ext)
        im.save(self.key_dir + 'output_MCM.png')
        im = image(self.key_dir + 'output_AMSS' + self.input_ext)
        im.save(self.key_dir + 'output_AMSS.png')

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # read the parameters
        params_file = index_dict(self.key_dir)
        scale_r = float(params_file['params']['scale_r'])
        grid_step = int(params_file['params']['grid_step'])
        zoom_factor = float(params_file['params']['zoom_factor'])

        return self.tmpl_out("result.html",
                             input=[self.key_url 
                                    + 'input.png?step=%s' % grid_step],
                             output=[self.key_url + 'output_MCM.png',
                                     self.key_url + 'output_AMSS.png'],
                             run_time=float(params_file['params']['run_time']),
                             scaleRnorm="%2.2f" % scale_r,
                             zoomfactor="%2.2f" % zoom_factor, 
			     sizeY="%i" % image(self.key_dir
                                                + 'input.png').size[1])

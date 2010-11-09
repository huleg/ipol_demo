"""
empty IPOL demo web app
this class handles all the backend : paths, archives, indexes, ...
"""
# pylint: disable=C0103

#
# EMPTY APP
#

import hashlib
from datetime import datetime
from random import random

import os
import time
from subprocess import Popen
import sqlite3

from cherrypy import TimeoutError
import cherrypy

from . import archive
from . import config

class empty_app(object):
    """
    This app only contains configuration and tools, no actions.
    """

    def __init__(self, base_dir):
        """
        app setup

        @param base_dir: the base directory for this demo, used to
        look for special subfolders (input, tmp, ...)
        """
        # the demo ID is the folder name
        self.base_dir = os.path.abspath(base_dir) + os.path.sep
        self.id = os.path.basename(base_dir)
        # TODO: better key initialization
        self.key = ''
        self.cfg = {}

        # create the missing subfolders
        for static_dir in [self.input_dir, self.tmp_dir, self.archive_dir]:
            if not os.path.isdir(static_dir):
                os.mkdir(static_dir)

        # TODO : metge with getattr
        self.archive_index = os.path.join(self.archive_dir, "index.db")
        # initialize the index if needed
        if not os.path.isfile(self.archive_index):
            self.make_archive_index()
                
        # static folders
        # cherrypy.tools.staticdir is a decorator,
        # ie a function modifier
        self.input = cherrypy.tools.staticdir(dir=self.input_dir)\
            (lambda x : None)
        self.tmp = cherrypy.tools.staticdir(dir=self.tmp_dir)\
            (lambda x : None)
        self.arc = cherrypy.tools.staticdir(dir=self.archive_dir)\
            (lambda x : None)


    def __getattr__(self, attr):
        """
        direct access to some class attributes
        """

        # subfolder patterns
        # TODO: "path" is the correct syntax
        dir_pattern = {'input_dir' : 'input',
                       'dl_dir' : 'dl',
                       'src_dir' : 'src',
                       'bin_dir' : 'bin',
                       'tmp_dir' : 'tmp',
                       'work_dir' : os.path.join('tmp', self.key),
                       'archive_dir' : 'archive'}
        url_pattern = {'base_url' : '/',
                       'input_url' : '/input/',
                       'tmp_url' : '/tmp/',
                       'work_url' : '/tmp/%s/' % self.key,
                       'archive_url' : '/arc/'}

        # subfolders
        if attr in dir_pattern:
            value = os.path.join(self.base_dir,
                                 dir_pattern[attr])
            value = os.path.abspath(value) + os.path.sep
        # url
        elif attr in url_pattern:
            value = cherrypy.url(path=url_pattern[attr])
        # real attribute
        else:
            value = object.__getattribute__(self, attr)
        return value

    def init_key(self, key):
        """
        reinitialize the key between 2 page calls
        """
        # delete key
        self.key = ''
        # regenerate key-related attributes
        self.new_key(key)

    def init_cfg(self):
        """
        reinitialize the config dictionary between 2 page calls
        """
        # delete cfg
        self.cfg = {}
        # read the config dict
        self.cfg = config.file_dict(self.work_dir)
        self.cfg.setdefault('param', {})
        self.cfg.setdefault('info', {})
        self.cfg.setdefault('meta', {})

    #
    # UPDATE
    #

    def build(self):
        """
        virtual function, to be overriden by subclasses
        """
        cherrypy.log("warning: no build method",
                     context='SETUP/%s' % self.id, traceback=False)

    #
    # KEY MANAGEMENT
    #

    def new_key(self, key=None):
        """
        create a key if needed, and the key-related attributes
        """
        if key is None:
            keygen = hashlib.md5()
            seeds = [cherrypy.request.remote.ip,
                     # use port to improve discrimination
                     # for proxied or NAT clients 
                     cherrypy.request.remote.port, 
                     datetime.now(),
                     random()]
            for seed in seeds:
                keygen.update(str(seed))
            key = keygen.hexdigest()
        
        self.key = key

        # check key
        if not (self.key
                and self.key.isalnum()
                and (self.tmp_dir == 
                     os.path.commonprefix([self.work_dir, self.tmp_dir]))):
            # HTTP Bad Request
            raise cherrypy.HTTPError(400, "The key is invalid")

        if not os.path.isdir(self.work_dir):
            os.mkdir(self.work_dir)

        return

    #
    # LOGS
    #

    def log(self, msg):
        """
        simplified log handler

        @param msg: the log message string
        """
        cherrypy.log(msg, context="DEMO/%s/%s" % (self.id, self.key),
                     traceback=False)
        return

    #
    # SUBPROCESS
    #

    def run_proc(self, args, stdin=None, stdout=None, stderr=None):
        """
        execute a sub-process from the 'tmp' folder
        """
        # update the environment
        newenv = os.environ.copy()
        # TODO clear the PATH, hard-rewrite the exec arg0
        # TODO use shell-string execution
        newenv.update({'PATH' : self.bin_dir})
        # run
        return Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                     env=newenv, cwd=self.work_dir)

    def wait_proc(self, process, timeout=False):
        """
        wait for the end of a process execution with an optional timeout
        timeout: False (no timeout) or a numeric value (seconds)
        process: a process or a process list, tuple, ...
        """

        if not (cherrypy.config['server.environment'] == 'production'):
            # no timeout if just testing
            timeout = False
        if isinstance(process, Popen):
            # require a list
            process_list = [process]
        else:
            # duck typing, suppose we have an iterable
            process_list = process
        if not timeout:
            # timeout is False, None or 0
            # wait until everything is finished
            for p in process_list:
                p.wait()
        else:
            # http://stackoverflow.com/questions/1191374/
            # wainting for better : http://bugs.python.org/issue5673
            start_time = time.time()
            run_time = 0
            while True:
                if all([p.poll() is not None for p in process_list]):
                    # all processes have terminated
                    break
                run_time = time.time() - start_time
                if run_time > timeout:
                    for p in process_list:
                        try:
                            p.terminate()
                        except OSError:
                            # could not stop the process
                            # probably self-terminated
                            pass
                    raise TimeoutError
                time.sleep(0.1)
        if any([0 != p.returncode for p in process_list]):
            raise RuntimeError
        return

    #
    # ARCHIVE
    #

    def make_archive(self):
        """
        create an archive bucket
        """
        ar = archive.bucket(path=self.archive_dir,
                            cwd=self.work_dir,
                            key=self.key)
        date = ar.cfg['meta']['date']
        # add to the index
        db = sqlite3.connect(self.archive_index)
        c = db.cursor()
        c.execute("insert or replace into buckets (key, date) values (?, ?)",
                  (self.key, date))
        db.commit()
        c.close()
        return ar

    def make_archive_index(self):
        """
        create an index of the archive buckets
        """
        cherrypy.log("(re)creating the archive index",
                     context='SETUP/%s' % self.id, traceback=False)
        db = sqlite3.connect(self.archive_index)
        c = db.cursor()
        # (re)create table
        c.execute("drop table if exists buckets")
        # TODO : check SQL index usage
        c.execute("drop index if exists buckets_by_date")
        c.execute("create table buckets (key text unique, date text)")
        c.execute("create index buckets_by_date on buckets (date)")
        # populate the db
        for key in archive.list_key(self.archive_dir):
            bucket = archive.bucket(path=self.archive_dir,
                                    key=key)
            date = bucket.cfg['meta']['date']
            c.execute("""insert into buckets (key, date) values (?, ?)""",
                      (key, date))
        db.commit()
        c.close()

    def get_archive_key_by_date(self, limit=50, offset=0):
        """
        get some keys from the index
        """
        # TODO: use iterators
        db = sqlite3.connect(self.archive_index)
        c = db.cursor()
        c.execute("select key from buckets order by date desc "
                  + "limit ? offset ?",
                  (limit, offset))
        return [key[0] for key in c]


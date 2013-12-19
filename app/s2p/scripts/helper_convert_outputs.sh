#!/bin/bash

# horrible hack to add the folder bin/bin to the path
# in order to use qauto and iion
export PATH=/usr/bin:/usr/local/bin:/bin:$PATH
BINBIN=`dirname \`which s2p.py\``/bin
export PATH=$BINBIN:$PATH

iion s2p_results/roi_color_ref.tif s2p_results/roi_color_ref_preview.png
qauto s2p_results/roi_ref.tif s2p_results/roi_ref_preview.png

if [ ! -d left ] ; then
    qauto s2p_results/dem_fusion.tif s2p_results/dem_fusion_preview.png
    for f in s2p_results/{left,right}/tile_*
    do
        qauto $f/dem.tif $f/dem_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_height.tif $f/rectified_height_preview.png &
        wait
    done
else
    qauto s2p_results/dem.tif s2p_results/dem_fusion_preview.png
    for f in s2p_results/tile_*
    do
        qauto $f/dem.tif $f/dem_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_height.tif $f/rectified_height_preview.png &
        wait
    done
fi

# cp output files in the root output folder for archive
cp s2p_results/dem_fusion_preview.png .
cp s2p_results/roi_color_ref_preview.png .
cp s2p_results/roi_ref_preview.png .

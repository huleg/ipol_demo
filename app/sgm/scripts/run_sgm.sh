#/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin:.

#load params
. params

# Subpixel parameter
# export SUBPIXEL=$subpixel

# 1. Block-matching
sgm left_image.tif right_image.tif disp_sgm.tif $min_disparity $max_disparity $lr 15 $nb_iter $P1 $P2

# 2. Filtering
# flatH left_image.tif filt_flat_std_bm.png $win_w
# stereoLRRL2 disp_std_bm.tif dispR_std_bm.tif filt_LRRL_std_bm.png 1
# if [ "${ground_truth_mask}" != "" ]; then
# intersection $ground_truth_mask filt_LRRL_std_bm.png filt_flat_std_bm.png filt_std_bm.tif
# else
# intersection filt_LRRL_std_bm.png filt_flat_std_bm.png filt_std_bm.tif
# fi
# save_png_mask.sh filt_std_bm.tif filt_std_bm.png

# 4. Generate png images for html display
save_png.sh disp_sgm.tif disp_sgm.png $min_disparity $max_disparity
#save_png.sh cost_std_bm.tif cost_std_bm.png 0 100


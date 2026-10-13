#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Exact existing menu colors; the hardware palette duplicates #BBBBAA at
# indices 0 and 11 because index 0 is transparent. There are 15 unique RGBs.
convert -size 1x1 xc:'#BBBBAA' xc:'#111111' xc:'#EEDDBB' xc:'#CCAA77' \
    xc:'#998855' xc:'#665533' xc:'#EEBB44' xc:'#444455' xc:'#666677' \
    xc:'#889999' xc:'#AAAA99' xc:'#333333' xc:'#555544' xc:'#DDDDDD' \
    xc:'#EEEEEE' +append source/palette.png
convert source/marshals-orders-prussian-v2.png -resize '640x480!' -alpha off \
    \( +clone -crop '640x154+0+0' +repage -resize '640x136!' \) \
    -geometry +0+0 -compose Over -composite \
    +dither -remap source/palette.png -fill '#BBBBAA' \
    -draw 'rectangle 0,136 639,335 rectangle 0,416 639,479' \
    PNG8:marshals-orders-prussian-v2.png
python3 verify.py

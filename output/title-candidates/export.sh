#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
convert -size 1x1 xc:'#111111' xc:'#445555' xc:'#DDBB66' xc:'#BB3322' +append source/palette.png
for name in 01-the-marshal 01-the-marshal-v2 02-the-charge 03-the-war-table; do
    # Preserve the artwork's stipple/engraving patterns; avoid adding red
    # error-diffusion speckles to solid gold letters during palette mapping.
    convert "source/$name.png" -resize '640x480!' -alpha off +dither \
        -remap source/palette.png "PNG8:$name.png"
done
# The generator's warm gold shading can map to red. Restrict the fourth
# color to the two standing collar panels; map every other region to ink,
# slate and gold so the eagle, lapels and trim cannot acquire red speckles.
convert -size 1x1 xc:'#111111' xc:'#445555' xc:'#DDBB66' +append source/three-color-palette.png
convert -size 640x480 xc:black +antialias -fill white \
    -draw 'polygon 435,250 480,267 500,311 434,288 polygon 576,257 562,268 552,313 575,300' \
    source/collar-mask.png
convert source/01-the-marshal-v3.png -resize '640x480!' -alpha off +dither \
    -remap source/three-color-palette.png source/marshal-v3-three-color.png
convert source/01-the-marshal-v3.png -resize '640x480!' -alpha off +dither \
    -remap source/palette.png source/marshal-v3-four-color.png
convert source/marshal-v3-three-color.png source/marshal-v3-four-color.png \
    source/collar-mask.png -composite PNG8:01-the-marshal-v3.png
python3 ../../assets/scripts/splash_footer.py 01-the-marshal-v3.png 01-the-marshal-v4.png
python3 ../../assets/scripts/splash_frame.py 01-the-marshal-v4.png 01-the-marshal-frame.png
python3 verify.py

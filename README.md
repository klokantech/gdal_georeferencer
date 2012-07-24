gdal_georeferencer
==================

Use this to georeference and warp local raster image of a map
that is on the Georeferencer.org site.

Example:

    $ python gdal_georeferencer.py \
            -srs epsg:4326 \
            4I8A6MZxOzQeiWpo2S37aZ \
            komensky.jp2 \
            komensky_warped.tif

This will read GCPs and cutline from Georeferencer and reproject
the source raster into a new GeoTiff file. You can set the output
format with the `-of` option. Use `-of vrt` to create a VRT warped
file.

You need to have an account on the site. The script uses OAuth
to authenticate and will ask you to validate the authentication
in you browser the first time it runs.

Needs GDAL with Python support.

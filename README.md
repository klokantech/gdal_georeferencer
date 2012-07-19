georeferencer_gdal
==================

Use this to georeference and warp local raster image of a map
that is on the Georeferencer.org site.

Example:

    $ python georeferencer_gdal.py \
            -s_srs epsg:4326 \
            -t_srs epsg:900913 \
            -map 4I8A6MZxOzQeiWpo2S37aZ \
            komensky.jp2 \
            komensky_georeferenced.vrt \
            komensky_warped.vrt

This will read GCPs and cutline from Georeferencer and create
two VRT files. One with the georeference, one already warped
with default settings.

You need to have an account on the site. The script uses OAuth
to authenticate and will ask you to validate the authentication
in you browser the first time it runs.

Needs GDAL with Python support and the oauth2 module.

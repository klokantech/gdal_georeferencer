#!/usr/bin/env python

# Copyright (C) 2012 Klokan Technologies GmbH
# Vaclav "Keo" Klusak <vaclav.klusak@klokantech.com>


from __future__ import with_statement

import json
import oauth2 as oauth
from osgeo import gdal
from osgeo import osr


# Values from the Google API Console, don't change.
consumer_key = '829338221358.apps.googleusercontent.com'
consumer_secret = 'bVNqpXTMDtnOEDhR8IzapwL6'


def main(argc, argv):
    s_srs = None
    t_srs = None
    map_name = None
    token_path = None

    i = 1
    while i < argc:
        if argv[i] == '-s_srs' and i + 1 < argc:
            s_srs = sanitize_srs(argv[i + 1])
            i += 2
        elif argv[i] == '-t_srs' and i + 1 < argc:
            t_srs = sanitize_srs(argv[i + 1])
            i += 2
        elif argv[i] == '-map' and i + 1 < argc:
            map_name = argv[i + 1]
            i += 2
        elif argv[i] == '-token' and i + 1 < argc:
            token_path = argv[i + 1]
            i += 2
        elif argv[i] == '-help':
            print_usage(argv[0])
            return
        else:
            break

    if i + 2 < argc:
        src_path = argv[i]
        georef_path = argv[i + 1]
        warped_path = argv[i + 2]
    else:
        print_usage(argv[0])
        return

    if t_srs is None:
        raise Exception('No target SRS')
    if map_name is None:
        raise Exception('No map name')
    if token_path is None:
        import os.path
        token_path = os.path.expanduser('~/.georeferencer_gdal')

    src = gdal.Open(src_path)
    if src is None:
        raise Exception("Can't open " + src_path)

    if s_srs is None:
        s_srs = sanitize_srs(src.GetProjection())
        if s_srs is None:
            raise Exception('No source SRS')

    georef = read_georeference(map_name, token_path, src.RasterXSize, src.RasterYSize)
    gcps = transform_gcps(georef['control_points'], s_srs)
    if len(gcps) < 3:
        raise Exception('Not enough GCPs')

    vrt_driver = gdal.GetDriverByName("VRT")
    vrt = vrt_driver.CreateCopy(georef_path, src)
    vrt.SetProjection(s_srs)
    vrt.SetGCPs(gcps, s_srs)
    dst = gdal.AutoCreateWarpedVRT(vrt, s_srs, t_srs)
    if dst is None:
        raise Exception("Can't warp")
    dst.SetDescription(warped_path)
    del dst
    del vrt

    if georef['cutline']:
        add_cutline(warped_path, georef['cutline'])


def sanitize_srs(text):
    obj = osr.SpatialReference()
    if obj.SetFromUserInput(text) != 0:
        raise Exception('Invalid SRS ' + text)
    return obj.ExportToWkt()


def transform_gcps(gcps, srs):
    src = osr.SpatialReference()
    src.ImportFromEPSG(4326)
    dst = osr.SpatialReference()
    dst.ImportFromWkt(srs)
    tr = osr.CoordinateTransformation(src, dst)
    ret = []
    for gcp in gcps:
        x, y, z = tr.TransformPoint(gcp['longitude'], gcp['latitude'], 0.0)
        ret.append(gdal.GCP(x, y, z, gcp['pixel_x'], gcp['pixel_y']))
    return ret


def add_cutline(path, cutline):
    with open(path, 'rb') as f:
        text = f.read()
    wkt = ('MULTIPOLYGON (((' +
           ','.join('%.15f %.15f' % (x, y) for (x, y) in cutline) +
           ')))')
    text = text.replace('</GDALWarpOptions>',
                        '<Cutline>%s</Cutline></GDALWarpOptions>' % (wkt,))
    with open(path, 'wb') as f:
        f.write(text)


def read_georeference(map_name, token_path, x_size, y_size):
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    token = read_token(token_path)
    if token is None:
        print 'Fetching request token ...'
        gen = get_access_token(consumer, "georeferencer3")
        url = gen.next()

        print
        print "Authentication page will be opened in your browser."
        print "Press enter after you are done with it."
        print
        import webbrowser
        webbrowser.open(url)
        raw_input('Continue? ')

        print 'Fetching access token ...'
        token = gen.next()
        write_token(token_path, token)

    import urllib
    client = oauth.Client(consumer, token)

    params = urllib.urlencode({
        'map': map_name,
        'x_size': x_size,
        'y_size': y_size
    })
    georef_url = 'http://georeferencer3.appspot.com/api/georeference?' + params

    print 'Fetching georeference ...'
    resp, content = client.request(georef_url, 'GET')
    if resp['status'] != '200':
        raise Exception("Invalid response %s" % (resp['status'],))
    return json.loads(content)


def get_access_token(consumer, app_name):
    import urlparse

    request_token_url = 'https://%s.appspot.com/_ah/OAuthGetRequestToken' % (app_name,)
    authorize_url = 'https://%s.appspot.com/_ah/OAuthAuthorizeToken' % (app_name,)
    access_token_url = 'https://%s.appspot.com/_ah/OAuthGetAccessToken' % (app_name,)

    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, 'GET')
    if resp['status'] != '200':
        raise Exception("Invalid response %s" % (resp['status'],))
    request_token = dict(urlparse.parse_qsl(content))

    yield '%s?oauth_token=%s' % (authorize_url, request_token['oauth_token'])

    token = oauth.Token(request_token['oauth_token'],
                        request_token['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urlparse.parse_qsl(content))
    yield oauth.Token(access_token['oauth_token'],
                      access_token['oauth_token_secret'])


def read_token(path):
    try:
        with open(path, 'rb') as f:
            obj = json.load(f)
        return oauth.Token(obj['oauth_token'],
                           obj['oauth_token_secret'])
    except Exception:
        return None


def write_token(path, token):
    obj = {
        'oauth_token': token.key,
        'oauth_token_secret': token.secret
    }
    with open(path, 'wb') as f:
        json.dump(obj, f)


def print_usage(progname):
    print 'usage: %s [-token path] -s_srs SRS -t_srs SRS input georef_vrt warped_vrt' % (progname,)


if __name__ == "__main__":
    import sys
    main(len(sys.argv), sys.argv)


__author__ = "Jeremy Nelson"

import re
from . import app, harvest, cache
from flask import url_for
import search


@app.template_filter('footer')
def get_footer(s):
    footer = cache.get('footer')
    if footer:
        return footer
    harvest()
    return cache.get('footer')

@app.template_filter('format_icon')
def get_format_icon(term):
    return ''

@app.template_filter('header')
def get_header(s):
    header = cache.get('header')
    if header:
        return header
    harvest()
    return cache.get('header')


@app.template_filter('icon')
def get_icon(datastream):
    """Filter returns the glyphicon CSS class for a datastream

    Args:
	    datastream -- Datastream dict
    """
    mime_type = datastream.get('mimeType')
    if mime_type.endswith("pdf"):
        return "glyphicon-file"
    if mime_type.endswith("mp4") or\
       mime_type.endswith("quicktime"):
        return "glyphicon-facetime-video"
    if mime_type.endswith("mp3") or\
       mime_type.endswith("wav") or\
       mime_type.endswith("wave") or\
       mime_type.endswith("mpeg") or\
       mime_type.startswith("audio/x-m4a"):
        return "glyphicon-headphones"
    if mime_type.endswith("jpg") or\
       mime_type.endswith("jpeg") or\
       mime_type.endswith("jp2"):
        return "glyphicon-picture"
    if mime_type.endswith("octet-stream"):
        return "glyphicon-stats"
    if mime_type.endswith("tif"):
        return "glyphicon-download"

@app.template_filter('scripts')
def get_scripts(s):
    scripts = cache.get('scripts')
    if scripts:
        return scripts
    harvest()
    return cache.get('scripts')

@app.template_filter('slugify')
def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

@app.template_filter('styles')
def get_styles(s):
    styles = cache.get('styles')
    if styles:
        return styles
    harvest()
    return cache.get('styles')

@app.template_filter('tabs')
def get_tabs(s):
    """Filter retrieves or harvests CC Library's homepage tabs
  
    Args:
        s -- Ignored string to call from template
    """
    tabs = cache.get('tabs')
    if tabs:
        return tabs
    harvest()
    return cache.get('tabs')


@app.template_filter('title_principal')
def get_title(pid):
    """Filter takes a pid and attempts to return the titlePrincipal

    Args:
        pid -- Fedora Object PID
    """
    return search.get_title(pid)

AUDIO_TEMPLATE = """<audio src="{0}" controls="controls" id="viewer-{1}">
 <a href="{0}" class="center-block">Download</a>
</audio>"""

DATASET_TEMPLATE = """Download Dataset <em>{1}</em> <a href="{0}" class="btn btn-primary">
<i class="glyphicon-stats glyphicon"></i></a>"""

PDF_TEMPLATE = """<object data="{0}" type="application/pdf" width="100%" height="600px">
        alt : <a href="{0}">{1}</a> 
</object>"""

QT_TEMPLATE = """<embed src="{}" width="640" height="480" class="center-block" 
controller="true" loop="false" pluginspage="http://www.apple.com/quicktime/"></embed>"""

TIFF_TEMPLATE = """<div class="row">
<div class="col-md-4 col-md-offset-4">
<a href="{}" class="btn btn-lg btn-primary">
<i class="glyphicon glyphicon-download"></i> Download</a>
</div>
</div>"""


VIDEO_TEMPLATE = """<video src="{0}" controls="controls" poster="poster.jpg" width="640" height="480" id="viewer-{1}">
<a href="{0}" class="center-block">Download video</a>
</video>"""


@app.template_filter("viewer")
def generate_viewer(datastream, dlg_number):
    """Filter takes a datastream and generates HTML5 player based on mime-type

    Args:
        datastream -- Dictionary with Data stream information
        dlg_number -- Dialog ID Number

    """
    mime_type = datastream.get('mimeType')
    ds_url = url_for(
        'get_datastream', 
        pid=datastream.get('pid'),
        dsid=datastream.get('dsid'))
    if mime_type.endswith('pdf'):
        return PDF_TEMPLATE.format(
             ds_url,
             datastream.get('label'))
    if mime_type.endswith('audio/mpeg') or\
       mime_type.endswith("audio/mp3") or\
       mime_type.endswith("audio/x-m4a") or\
       mime_type.endswith("wav") or\
       mime_type.endswith("wave"):
        return AUDIO_TEMPLATE.format(ds_url, dlg_number)
    if mime_type.endswith("octet-stream"):
        return DATASET_TEMPLATE.format(ds_url, datastream.get('label'))
    if mime_type.endswith('quicktime'):
        return QT_TEMPLATE.format(ds_url)
    if mime_type.endswith('mp4'):
        return VIDEO_TEMPLATE.format(ds_url, dlg_number)
    if mime_type.endswith('jpeg'):
        return """<img src="{}" class="center-block img-thumbnail">""".format(ds_url)
    if mime_type.endswith("tif"):
        return TIFF_TEMPLATE.format(ds_url)        


__author__ = "Jeremy Nelson"

from . import app

@app.template_filter('format_icon')
def get_format_icon(term):
    return ''

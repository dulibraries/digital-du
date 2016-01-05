__author__ = "Jeremy Nelson"

from flask import render_template

from . import app

@app.route("/")
def index():
    """Displays Home-page of Digital Repository"""
    return render_template(
        'discovery/index.html', 
        facets=[
            {"name": "Format"},
            {"name": "People"},
            {"name": "Topics"},
            {"name": "Publication Year"},
            {"name": "Geographic Location"}])

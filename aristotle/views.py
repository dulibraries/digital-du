__author__ = "Jeremy Nelson"

import json
from flask import jsonify, render_template, request

from . import app, REPO_SEARCH
from search import browse

@app.route("/browse", methods=["POST", "GET"])
def browser():
    pid = request.form["pid"]
    return browse(pid)

@app.route("/header")
def header():
    """Returns HTML doc to be included in iframe"""
    return render_template('discovery/snippets/cc-header.html')

@app.route("/search", methods=["POST", "GET"])
def query():
    if request.method.startswith("POST"):
        search_result = REPO_SEARCH.search(q=request.form["q"])
        return jsonify(search_result)

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

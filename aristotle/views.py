__author__ = "Jeremy Nelson"

import json
import requests

from flask import abort, jsonify, render_template, request, Response 

from . import app, cache, REPO_SEARCH
from search import browse, get_pid

@app.route("/browse", methods=["POST"])
def browser():
    if request.method.startswith("POST"):
        pid = request.form["pid"]
        browsed = cache.get(pid)
        if not browsed:
            browsed = browse(pid)
            cache.set(pid, browsed)
        return jsonify(browsed)
    
@app.route("/header")
def header():
    """Returns HTML doc to be included in iframe"""
    return render_template('discovery/snippets/cc-header.html')

@app.route("/image/<uid>")
def image(uid):
    pid = get_pid(uid)
    thumbnail_url = "{}{}/datastreams/TN/content".format(
        app.config.get("REST_URL"),
        pid)
    raw_thumbnail = cache.get(thumbnail_url)
    if not raw_thumbnail:
        result = requests.get(thumbnail_url)
        if result.status_code > 399:
            abort(500)
        #raw_thumbnail = result.text
        return Response(result.text, mimetype="image/jpeg")
    

@app.route("/search", methods=["POST", "GET"])
def query():
    if request.method.startswith("POST"):
        search_result = REPO_SEARCH.search(q=request.form["q"])
        return jsonify(search_result)

@app.route("/<identifier>/<value>")
def fedora_object(identifier, value):
    if identifier.startswith("pid"):
        return render_template(
            'discovery/index.html',
	    pid=value,
            facets=[])
    return "Should return detail for {} {}".format(identifier, value)

@app.route("/")
def index():
    """Displays Home-page of Digital Repository"""
    return render_template(
        'discovery/index.html',
	pid="coccc:root",
        facets=[
            {"name": "Format"},
            {"name": "People"},
            {"name": "Topics"},
            {"name": "Publication Year"},
            {"name": "Geographic Location"}])

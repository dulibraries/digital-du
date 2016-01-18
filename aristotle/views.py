"""This module extends and refactors Aristotle Library Apps projects for 
Flask using Elasticsearch"""
__author__ = "Jeremy Nelson"

import json
import requests

from flask import abort, jsonify, render_template, request, Response 

from . import app, cache, REPO_SEARCH
from search import browse, get_aggregations, get_detail, get_pid

@app.route("/browse", methods=["POST"])
def browser():
    """Browse view for AJAX call from client based on the PID in the 
    Form
    Returns:
        jsonified version of search result
    """
    if request.method.startswith("POST"):
        pid = request.form["pid"]
        browsed = cache.get(pid)
        if not browsed:
            browsed = browse(pid)
            cache.set(pid, browsed)
        return jsonify(browsed)

@app.route("/detail", methods=["POST"])
def detailer():
    """Detail view for AJAX call from client based on the PID in
	the Form.

    Returns:
        jsonified version of the search result
    """
    if request.method.startswith("POST"):
        pid = request.form["pid"]
        detailed_info = get_detail(pid)
        return jsonify(detailed_info)

    
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
        results = browse(value)
        if results['hits']['count'] == 1:
            return render_template(
                'discovery/index.html',
                pid=value,
				info=results['hits']['hits'][0])
        return render_template(
            'discovery/index.html',
	        pid=value,
            facets=get_aggregations(value))
    return "Should return detail for {} {}".format(identifier, value)

@app.route("/")
def index():
    """Displays Home-page of Digital Repository"""
    return render_template(
        'discovery/index.html',
	    pid="coccc:root",
        facets=get_aggregations())

"""This module extends and refactors Aristotle Library Apps projects for
Flask using Elasticsearch"""
__author__ = "Jeremy Nelson"

import requests

from flask import abort, jsonify, render_template, request, Response

from . import app, cache, REPO_SEARCH
from search import browse, filter_query, get_aggregations, get_detail, get_pid

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
    """View extracts the Thumbnail datastream from Fedora based on the
    Elasticsearch ID

    Args:
        uid: Elasticsearch ID
    """
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
    """View returns Elasticsearch query search results

    Returns:
        jsonified version of the search result
    """
    if request.method.startswith("POST"):
        search_result = REPO_SEARCH.search(q=request.form["q"])
        return jsonify(search_result)
    query_str = request.args.get('q', '')
    if len(query_str) < 1:
        query_str = None
    facet = request.args.get('facet')
    val = request.args.get('val')
    return jsonify(filter_query(facet, val, query_str))

@app.route("/<identifier>/<value>")
def fedora_object(identifier, value):
    """View routes to a Fedora Object based on type of identifier and
    a value. Currently only supports routing by PID, should support DOI
    next.

    Args:
        identifier: Identifier type, currently supports pid
        value: Identifier value to search on

    Returns:
        Rendered HTML from template and Elasticsearch
    """
    if identifier.startswith("pid"):
        results = browse(value)
        if results['hits']['total'] < 1:
            detail_result = get_detail(value)
            return render_template(
                'discovery/detail.html',
                pid=value,
                info=detail_result['hits']['hits'][0])
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

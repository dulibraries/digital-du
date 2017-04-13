"""This module extends and refactors Aristotle Library Apps projects for
Flask using Elasticsearch"""
__author__ = "Jeremy Nelson"

import datetime
import os
import requests

HOME = os.path.abspath(os.curdir)
with open(os.path.join(HOME, "VERSION")) as fo:
    VERSION = fo.read()

from flask import abort, jsonify, render_template, redirect, request,\
    Response, url_for
from . import app, cache, REPO_SEARCH
from search import browse, filter_query, get_aggregations, get_detail, get_pid,\
    specific_search

@app.route("/about")
def about_digitalcc():
    """Displays details of current version of Digital CC"""
    index_created_on = REPO_SEARCH.indices.get('repository').get('repository').get('settings').get('index').get('creation_date')
    indexed_on = datetime.datetime.utcfromtimestamp(int(index_created_on[0:10]))
    return render_template("discovery/About.html",
        indexed_on = indexed_on,
        version = VERSION)
    

@app.route("/browse", methods=["POST", "GET"])
def browser():
    """Browse view for AJAX call from client based on the PID in the
    Form
    Returns:
        jsonified version of search result
    """
    if request.method.startswith("POST"):
        pid = request.form["pid"]
        from_ = request.form.get("from", 0)
    else:
        pid = request.args.get('pid')
        from_ = request.args.get('from', 0)
    cache_key = "{}-{}".format(pid, from_)
    browsed = cache.get(cache_key)
    if not browsed:
        browsed = browse(pid, from_)
        cache.set(cache_key, browsed)
    return jsonify(browsed)

@app.route("/contribute")
def view_contribute():
    return render_template("discovery/Contribute.html")
	
@app.route("/takedownpolicy")
def view_takedownpolicy():
    return render_template("discovery/Takedown.html")	

@app.route("/needhelp")
def view_help():
    return render_template("discovery/Help.html")	
	
@app.route("/pid/<pid>/datastream/<dsid>")
@app.route("/pid/<pid>/datastream/<dsid>.<ext>")
def get_datastream(pid, dsid, ext=None):
    """View returns the datastream based on pid and dsid

    Args:
        pid -- Fedora Object's PID
        dsid -- Either datastream ID of PID
    """
    fedora_url = "{}{}/datastreams/{}/content".format(
        app.config.get("REST_URL"),
        pid,
        dsid)
    exists_result = requests.get(fedora_url)
    if exists_result.status_code == 404:
        abort(404)
    return Response(
        exists_result.content, 
        mimetype=exists_result.headers.get('Content-Type'))


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

@app.route("/advanced-search",  methods=["POST", "GET"])
def advanced_search():
    """Preforms and advanced search"""
    if request.method.startswith("POST"):
        return "In search"
    
    return render_template(
        'discovery/index.html',
        pid="coccc:root",
        is_advanced_search=True,
        q=request.args.get('q', None),
        mode=request.args.get('mode', None)
    )

@app.route("/search", methods=["POST", "GET"])
def query():
    """View returns Elasticsearch query search results

    Returns:
        jsonified version of the search result
    """
    if request.method.startswith("POST"):
        mode = request.form.get('mode', 'keyword')
        facet = request.form.get('facet')
        facet_val = request.form.get('val')
        from_ = request.form.get('from', 0)
        size = request.form.get('size', 25)
        query = request.form["q"]
    else:
        mode = request.args.get('mode', 'keyword')
        facet = request.args.get('facet')
        from_ = request.args.get('from', 0)
        size = request.args.get('size', 25)
        facet_val = request.args.get('val')
        query = request.args.get('q', None)
    if mode in ["creator", "title", "subject", "number"]:
        return jsonify(
            specific_search(
                query,
                mode,
                size,
                from_))
    if mode.startswith("facet"):
        return jsonify(
            filter_query(
            facet, 
            facet_val, 
            query,
            size,
		    from_
            ))
    return jsonify(
       specific_search(
           query,
           "keyword",
           size,
           from_)
    )

@app.route("/pid/<pid>/datastream/<dsid>.<ext>")
def fedora_datastream(pid, dsid, ext):
    """View returns a specific Fedora Datastream including Images, PDFs,
    audio, and video datastreams

    Args:
        pid -- PID
        dsid -- Datastream ID
        ext -- Extension for datastream
    """
    ds_url = "{}{}/datastream/{}".format(
        app.config.get("REST_URL"),
        pid,
        dsid)
    result = requests.get(ds_url)
    if ext.startswith("pdf"):
        mimetype = 'application/pdf'
    if ext.startswith("jpg"):
        mimetype = 'image/jpg'
    if ext.startswith("mp3"):
        mimetype = "audio/mpeg"
    if ext.startswith("wav"):
        mimetype = "audio/wav"
    return Response(result.text, mimetype=mimetype) 

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
            if not 'islandora:collectionCModel' in\
                detail_result['hits']['hits'][0]['_source']['content_models']:
                return render_template(
                    'discovery/detail.html',
                    pid=value,
                    info=detail_result['hits']['hits'][0])
        if value.endswith("root"):
            return redirect(url_for('index'))
        return render_template(
            'discovery/index.html',
            pid=value,
            info=get_detail(value)['hits']['hits'][0]['_source'],
            facets=get_aggregations(value))
    if identifier.startswith("thumbnail"):
        thumbnail_url = "{}{}/datastreams/TN/content".format(
            app.config.get("REST_URL"),
            value)
        tn_result = requests.get(thumbnail_url)
        if tn_result.status_code == 404:
            thumbnail = cache.get('default-thumbnail')
            if not thumbnail:
                with app.open_resource(
                    "static/images/CCSquareLogo100.png") as fo:
                    thumbnail = fo.read()
                    cache.set('default-thumbnail', thumbnail)
            mime_type = "image/png"
        else:
            thumbnail = tn_result.content
            mime_type = "image/jpg"
        return Response(thumbnail, mimetype=mime_type)


    return "Should return detail for {} {}".format(identifier, value)

@app.route("/")
def index():
    """Displays Home-page of Digital Repository"""
    return render_template(
        'discovery/index.html',
        pid="coccc:root",
        q=request.args.get('q', None),
        mode=request.args.get('mode', None)
    )

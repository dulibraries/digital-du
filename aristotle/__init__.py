"""Port of Aristotle for use as a Digital Archives of Colorado College 
front-end"""
__author__ = "Jeremy Nelson"

import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
from flask import Flask, url_for, current_app
from werkzeug.contrib.cache import FileSystemCache
try:
    from .search import REPO_SEARCH
except ImportError or ValueError:
    from search import REPO_SEARCH

cache = FileSystemCache(
    os.path.join(
        os.path.split(
            os.path.abspath(os.path.curdir))[0],
                "cache"))

def harvest():
    """ Harvests Header, Tabs, and Footer from Library Website"""
    def update_links(element, type_="href"):
        existing_href = element.attrs.get(type_)
        if not existing_href:
            return       
        element.attrs[type_] = urllib.parse.urljoin(
            base_url,
            existing_href)
        element.attrs['target'] = '_top'
    base_url = app.config.get("BASE_URL")
    if not base_url:
        url_parse = urllib.parse.urlparse(
            app.config.get("INSTITUTION").get("url"))
        base_url = "{}://{}".format(url_parse.scheme, url_parse.netloc) 
    website_result = requests.get(app.config.get("INSTITUTION").get("url"))
    library_website = BeautifulSoup(website_result.text, "html.parser")
    header = library_website.find(id="header")
    tabs = library_website.find(id="library-tabs")
    tabs.attrs['style'] = """height: 120px;background-image: url('{}');""".format(
      url_for('static', filename='img/busy-library.jpg'))
    footer = library_website.find(id="footer")
    styles = library_website.find_all('link', rel='stylesheet')
    scripts = library_website.find_all('script')
    for row in styles:
        update_links(row)
    for snippet in [header, tabs, footer]:
        anchors = snippet.find_all('a')
        for anchor in anchors:
            update_links(anchor)
        for image in snippet.find_all('img'):
            update_links(image, type_="src")
    for script in scripts:
        src = script.attrs.get('src')
        if not src or src.startswith("//"):
            continue
        script.attrs['src'] = urllib.parse.urljoin(
            base_url,
            src)
    style_string =  '\n'.join([str(s) for s in styles])
    cache.set('styles', str(style_string))
    cache.set("header", str(header))
    cache.set("tabs", str(tabs))
    cache.set("footer", str(footer))
    cache.set("scripts", '\n'.join([str(s) for s in scripts]))


#from .views import *
#from .filters import *

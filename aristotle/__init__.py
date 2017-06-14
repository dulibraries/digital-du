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

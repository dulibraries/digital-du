#!/usr/bin/env python3
"""Module polls repository and indexes any new Fedora objects"""
__author__ = "Jeremy Nelson"

import datetime
import requests
from . import CONF, REPO_SEARCH
from .indexer import Indexer, IndexerError

# SPARQL Constants
NEWEST_100_SPARQL = """SELECT DISTINCT ?s ?date
WHERE { ?s <fedora-model:createdDate> ?date . }
ORDER BY DESC(?date)
LIMIT 100"""

# Functions
def check_index_new():
    """Function retrieves the newest 100 PIDS from Fedora, checks index
	for existence, and indexes PID if not found."""
    result = requests.post(
        CONF.get('RI_URL'),
        data={"type": "tuples",
              "lang": "sparql",
              "format": "json",
              "query": NEWEST_100_SPARQL},
        auth=CONF.get('FEDORA_AUTH'))
	if result.status_code > 399:
        raise IndexerError(
            "check_index_new() HTTP error {}".format(result.status_code),
            "Could not newest PIDS from repository\n{}".format(result.text))
    indexer = Indexer()
    for row in result.json().get('results'):
        pid = row.get('s').split("/")[-1]
        dsl = {
            "query": {
                "term": {"pid": pid}
            }
        }
        exists_result = REPO_SEARCH.search(body=dsl, index='repository')
        if exists_result['hits']['count'] > 0:
            continue
	    # Now run indexer
        indexer.index_pid(pid)

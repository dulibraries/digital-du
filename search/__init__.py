"""Module wraps Elastic Search functionality"""

__author__ = "Jeremy Nelson"

import click
import os
import requests
import sys

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
import xml.etree.ElementTree as etree

etree.register_namespace("mods", "http://www.loc.gov/mods/v3")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_SEARCH = None

try:
    sys.path.append(BASE_DIR)
    from instance import conf as CONF
    if hasattr(CONF, "ELASTICSEARCH"):
        REPO_SEARCH = Elasticsearch([CONF.get("ELASTICSEARCH"),])
except ImportError:
    CONF = dict()
    print("Failed to import config from instance")

if not REPO_SEARCH:
    REPO_SEARCH = Elasticsearch()

def browse(pid):
    """Function takes a pid and runs query to retrieve all of it's children
    pids

    Args:
        pid -- PID of Fedora Object
    """
    search = Search(using=REPO_SEARCH, index="repository") \
             .filter("term", inCollection=pid) \
             .sort("titlePrincipal") 
               
    results = search.execute()
   #return {"hits": results}
    return results.to_dict()

def get_aggregations(pid=None):
    """Function takes an optional pid and returns the aggregations
    scoped by the pid, if pid is None, runs aggregation on full ES
    index.
    
    Args:
        pid -- PID of Fedora Object, default is None
    
    Returns:
        dictionary of the results
    """
    #search = Search(using=REPO_SEARCH, index="repository) \
    aggs_dsl = {
	    "size": 0,
	    "aggs": {
		    "Format": {
			    "terms": {
				    "field": "typeOfResource"
			    }
		    },
		    "Genres": {
			    "terms": {
				    "field": "genre"
			    }
		    },
		    "Languages": {
			    "terms": {
				    "field": "language"
			    }
		    },
		    "Publication Year": {
			    "terms": {
				    "field": "dateCreated"
			    }
		    }
	    }
    }
    if pid is not None:
        aggs_dsl["query"] = {"match": { "inCollection": pid }}
    return REPO_SEARCH.search(index="repository", body=aggs_dsl)['aggregations']
        

def get_pid(es_id):
    """Function takes Elastic search id and returns the object's
    pid.

    Args:
        pid -- PID of Fedora Object
    """
    es_doc = REPO_SEARCH.get_source(id=es_id, index="repository")
    return es_doc.get("pid")

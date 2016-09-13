"""Module wraps Elastic Search functionality"""

__author__ = "Jeremy Nelson, Sarah Bogard"

import click
import os
import requests
import sys

from collections import OrderedDict
from copy import deepcopy
from flask import abort
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, A
import xml.etree.ElementTree as etree

etree.register_namespace("mods", "http://www.loc.gov/mods/v3")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_SEARCH = None
AGGS_DSL = {
    "sort": ["titlePrincipal"],
    "size": 0,
    "aggs": {
        "Format": {
             "terms": {
                 "field": "typeOfResource"
            }
        },
        "Geographic": {
            "terms": {
                "field": "subject.geographic"
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
                "field": "publicationYear"
			}
        },
        "Temporal (Time)": {
            "terms": {
                "field": "subject.temporal"
            }
        },
        "Topic": {
            "terms": {
                "field": "subject.topic"
            }
        }
    }
}

try:
    sys.path.append(BASE_DIR)
    from instance import conf as CONF
    if hasattr(CONF, "ELASTIC_SEARCH"):
        REPO_SEARCH = Elasticsearch([CONF.ELASTIC_SEARCH])
except ImportError:
    CONF = dict()
    print("Failed to import config from instance")

if not REPO_SEARCH:
    # Sets default using Elasticsearch defaults of localhost and ports
    # 9200 and 9300
    REPO_SEARCH = Elasticsearch()

def browse(pid, from_=0):
    """Function takes a pid and runs query to retrieve all of it's children
    pids

    Args:
		pid: PID of Fedora Object
    """
    search = Search(using=REPO_SEARCH, index="repository") \
             .filter("term", parent=pid) \
             .params(size=50, from_=from_) \
             .sort("titlePrincipal")
    results = search.execute()
    output = results.to_dict()
    search = Search(using=REPO_SEARCH, index="repository") \
             .filter("term", inCollections=pid) \
             .params(size=0)
    search.aggs.bucket("Format", A("terms", field="typeOfResource"))
    search.aggs.bucket("Geographic", A("terms", field="subject.geographic"))
    search.aggs.bucket("Genres", A("terms", field="genre"))
    search.aggs.bucket("Languages", A("terms", field="language"))
    search.aggs.bucket("Publication Year", A("terms", field="publicationYear"))
    search.aggs.bucket("Temporal (Time)", A("terms", field="subject.temporal"))
    search.aggs.bucket("Topic", A("terms", field="subject.topic"))
    facets = search.execute()
    output['aggregations'] = facets.to_dict()["aggregations"]
    return output

def filter_query(facet, facet_value, query=None, size=25, from_=0):
    """Function takes a facet, facet_value, and query string, and constructs
    filter for Elastic search.

    Args:
		facet: Facet name
		facet_value: Facet value
		query: Query, if blank searches entire index
		size: size of result set, defaults to 25
		from_: From location, used for infinite browse
    """
    dsl = {
        "size": size,
		"from": from_,
        "query": {
            "filtered":  {
                "filter": {
                    "term": {
							AGGS_DSL["aggs"][facet]["terms"]["field"]: facet_value
                    }
                }
            }
         },
		"aggs": AGGS_DSL['aggs']
    }
    if query is not None:
        dsl["query"]["match"] = {"_all": query}
    results = REPO_SEARCH.search(body=dsl, index="repository")
    return results


def specific_search(query, type_of, size=25, from_=0):
    """Function takes a query and fields list and runs a search on those
    specific fields.

    Args:
        query: query terms to search on
        type_of: Type of query, choices should be creator, title, subject,
                 and number

    Returns:
	    A dict of the search results
    """
    search = Search(using=REPO_SEARCH, index="repository")
    if type_of.startswith("creator"):
        search = search.query("match_phrase", creator=query)
    elif type_of.startswith("number"):
        search = search.query(
            Q("match_phrase", pid=query) | Q("match_phrase", doi=query))
    elif type_of.startswith("title"):
        search = search.query("match_phrase", titlePrincipal=query)
    elif type_of.startswith("subject"):
        search = search.query(Q("match_phrase", **{"subject.topic": query}) |\
                     Q("match_phrase", **{"subject.geographic": query}) |\
                     Q("match_phrase", **{"subject.temporal": query}))
    elif query is None:
        search = search.filter("term", parent=pid) \
                 .params(size=50, from_=from_) \
                 .sort("titlePrincipal")
    else:
        search = search.query(Q("query_string", query=query))
    search.params(size=size, from_=from_)
    search.aggs.bucket("Format", A("terms", field="typeOfResource"))
    search.aggs.bucket("Geographic", A("terms", field="subject.geographic"))
    search.aggs.bucket("Genres", A("terms", field="genre"))
    search.aggs.bucket("Languages", A("terms", field="language"))
    search.aggs.bucket("Publication Year", A("terms", field="dateCreated"))
    search.aggs.bucket("Temporal (Time)", A("terms", field="subject.temporal"))
    search.aggs.bucket("Topic", A("terms", field="subject.topic"))
    results = search.execute()
    return results.to_dict()

def get_aggregations(pid=None):
    """Function takes an optional pid and returns the aggregations
    scoped by the pid, if pid is None, runs aggregation on full ES
    index.

    Args:
        pid -- PID of Fedora Object, default is NoneBASE_DIR = os.path.dirname(os.path.dirname(__file__))

    Returns:
        dictionary of the results
    """
    #search = Search(using=REPO_SEARCH, index="repository) \
    dsl = deepcopy(AGGS_DSL)
    if pid is not None:
        dsl["query"] = {"term": { "inCollections": pid } }
    results = REPO_SEARCH.search(index="repository", body=dsl)['aggregations']
    output = OrderedDict()
    for key in sorted(results):
        aggregation = results[key]
        if len(aggregation.get('buckets')) > 0:
            output[key] = aggregation
    return output
        
def get_detail(pid):
    """Function takes a pid and returns the detailed dictionary from 
    the search results.

    Args:
        pid -- PID of Fedora Object
    """
    search = Search(using=REPO_SEARCH, index="repository") \
             .filter("term", pid=pid)
    result = search.execute()
    if len(result) < 1:
        # Raise 404 error because PID not found
        abort(404)
    return result.to_dict()
 

def get_pid(es_id):
    """Function takes Elastic search id and returns the object's
    pid.

    Args:
        pid -- PID of Fedora Object
    """
    es_doc = REPO_SEARCH.get_source(id=es_id, index="repository")
    return es_doc.get("pid")

def get_title(pid):
    """Function takes a pid and returns the titlePrincipal as a string

    Args:
        pid -- PID of Fedora Object
    """
    result = REPO_SEARCH.search(body={"query": {"term": {"pid": pid }},
			                          "fields": ["titlePrincipal"]},
                                index='repository')
    if result.get('hits').get('total') == 1:
        return result['hits']['hits'][0]['fields']['titlePrincipal'][0]
    return "Home"

if __name__ == "__main__":
    print()

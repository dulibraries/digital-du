"""indexer contains the Indexer class for indexing Fedora 3.x Objects into
an ElasticSearch instance either by PID or by Collection.

>>> import indexer
>>> test_indexer = indexer.Indexer() # Uses defaults from configuration file
>>> test_indexer.index_pid("abc:1234") # Indexes a single object by PID
>>> test_indexer.index_collection("cba:23") # Indexes all objects in a parent
                                            # collection
"""
__author__ = "Jeremy Nelson"

import datetime
import requests
import xml.etree.ElementTree as etree
from search.mods2json import mods2rdf

from . import CONF, REPO_SEARCH

class Indexer(object):
    """Elasticsearch MODS and PDF full-text indexer for Fedora Repository 3.8"""

    def __init__(self, **kwargs):
        """Initializes an instance of the IndexerClass

		Keyword args:
		    auth -- Tuple of username and password to authenticate to Fedora,
			        defaults to Fedora's standard login credentials

			elasticsearch -- Instance of Elasticsearch Python Client, defaults
			                 to REPO_SEARCH from indexer

            rest_url -- REST URL for Fedora 3.x, defaults to Fedora's stanard
			ri_url -- SPARQL Endpoint, defaults to Fedora's standard search URL

		"""
        self.auth = kwargs.get("auth", CONF.FEDORA_AUTH)
        self.elastic = kwargs.get("elasticsearch", REPO_SEARCH)
        self.rest_url = kwargs.get("rest_url", CONF.REST_URL)
        self.ri_search = kwargs.get("ri_url", CONF.RI_URL)
        # Set defaults if don't exist
        if not self.auth:
            self.auth = ("fedoraAdmin", "fedoraAdmin")
        if not self.rest_url:
            self.rest_url = "http://localhost:8080/fedora/objects/"
        if not self.ri_search:
            self.ri_search = "http://localhost:8080/fedora/risearch"

    def __reindex_pid__(self, pid, body):
        """Internal method checks and if pid already exists"""
        if self.elastic.count().get('count') < 1:
            return False
        dsl = {
            "query": {
                "term": {"pid": pid}
            }
        }
        result = self.elastic.search(body=dsl, index='repository', doc_type='mods')
        if  result.get('hits').get('total') > 0:
            mods_id = result.get('hits')[0].get('_id')
            self.elastic.index(
                id=mods_id,
                index="repository",
                doc_type="mods",
                body=body)
            return True


    def index_pid(self, pid, parent=None):
        """Method retrieves MODS and any PDF datastreams and indexes
        into repository's Elasticsearch instance

        Args:
            pid: PID to index
	    parent: PID of parent collection, default is None

        Returns:
            boolean: True if indexed, False otherwise
        """
        # Extract MODS XML Datastream
        mods_url = "{}{}/datastreams/MODS/content".format(
            self.rest_url,
            pid)
        mods_result = requests.get(
            mods_url,
            auth=self.auth)
        if mods_result.status_code > 399:
            raise IndexerError(
                "Failed to index PID {}, error={} url={}".format(
                    pid,
                    mods_result.status_code,
                    mods_url),
                mods_result.text)
        mods_xml = etree.XML(mods_result.text)
        mods_body = mods2rdf(mods_xml)
        mods_body['pid'] = pid
        if self.__reindex_pid__(pid, mods_body):
            return True
        if parent:
            mods_body['inCollection'] = [parent,]
        if not self.__reindex_pid__(pid, mods_body):
            mods_index_result = self.elastic.index(
                index="repository",
                doc_type="mods",
                body=mods_body)
            mods_id = mods_index_result
            if mods_id is not None:
                return True
        return False

    def index_collection(self, pid):
        """Method takes a parent collection PID, retrieves all children, and
        iterates through and indexes all pids

        Args:
            pid -- Collection PID
        """
        sparql = """SELECT DISTINCT ?s
WHERE {{
  ?s <fedora-rels-ext:isMemberOfCollection> <info:fedora/{}> .
}}""".format(pid)
        started = datetime.datetime.utcnow()
        print("Started indexing collection {} at {}".format(
            self.ri_search,
            started.isoformat()))
        children_response = requests.post(
            self.ri_search,
            data={"type": "tuples",
                  "lang": "sparql",
                  "format": "json",
                  "query": sparql},
            auth=self.auth)
        if children_response.status_code < 400:
            children = children_response.json().get('results')
            for row in children:
                iri = row.get('s')
                child_pid = iri.split("/")[-1]
                self.index_pid(child_pid, parent=pid)
                is_collection_sparql = """SELECT DISTINCT ?o
WHERE {{
  <info:fedora/{0}> <fedora-model:hasModel> <info:fedora/islandora:collectionCModel> .
  <info:fedora/{0}> <fedora-model:hasModel> ?o
}}""".format(child_pid)
                is_collection_result = requests.post(
                    self.ri_search,
                    data={"type": "tuples",
                          "lang": "sparql",
                          "format": "json",
                          "query": is_collection_sparql},
                    auth=self.auth)
                if len(is_collection_result.json().get('results')) > 0:
                    self.index_collection(child_pid)
            

        else:
            raise IndexerError(
                "Failed to index collection PID {}, error {}".format(
                    pid,
                    children_response.status_code),
                children_response.text)
        end = datetime.datetime.utcnow()
        print("Finished indexing {} at {}, total object {} total time {}".format(
            pid,
            end.isoformat(),
			len(children),
            (end-started).seconds / 60.0))


class IndexerError(Exception):
    """Base for any errors indexing Fedora 3.x objects into Elasticsearch"""

    def __init__(self, title, description):
        """Initializes an instance of IndexerError

	    Args:
	       title -- Title for Error
		   description -- More detailed information about the exception
        """
        super(IndexerError, self).__init__()
        self.title = title
        self.description = description

    def __str__(self):
        """Returns string representation of the object using the instance's
		title"""
        return repr(self.title)

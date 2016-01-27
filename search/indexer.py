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
import logging
import os
import requests
import sys
import xml.etree.ElementTree as etree
from rdflib import Namespace
from search.mods2json import mods2rdf
from search.mapping import MAP

from . import BASE_DIR, CONF, REPO_SEARCH

FEDORA_ACCESS = Namespace("http://www.fedora.info/definitions/1/0/access/")

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "index.log"),
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

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
        if not self.elastic.indices.exists('repository'):
            # Load mapping
            self.elastic.indices.create(index='repository', body=MAP)

    def __add_datastreams__(self, pid):
        """Internal method takes a PID and queries Fedora to extract 
        datastreams and return a list of datastreams names to be indexed
        into Elasticsearch.

		Args:
		   pid -- PID
        """
        ds_pid_url = "{}{}/datastreams?format=xml".format(
            self.rest_url,
            pid)
        result = requests.get(ds_pid_url)
        output = []
        if result.status_code > 399:
            raise IndexerError(
                "Failed to retrieve datastreams for {}".format(pid),
                "Code {} for url {} \nError {}".format(
						result.status_code,
                        ds_pid_url,
                        result.text))
        result_xml = etree.XML(result.text)
        datastreams = result_xml.findall(
            "{{{}}}datastream".format(FEDORA_ACCESS))
        for row in datastreams:
            add_ds = False
            mime_type = row.attrib.get('mimeType')
            if mime_type.startswith("application/pdf") or\
			   mime_type.startswith("audio/mpeg") or\
			   mime_type.startswith("video/quicktime") :
                add_ds = True
            if add_ds:
                output.append({
                    "label": row.attrib.get('label'),
					"dsid": row.attrib.get('dsid'),
                    "mimeType": mime_type})

        return output



    def __reindex_pid__(self, pid, body):
        """Internal method checks and if pid already exists"""
        if self.elastic.count().get('count') < 1:
            return False
        dsl = {
            "query": {
                "term": {"pid": pid}
            }
        }
        result = self.elastic.search(
            body=dsl,
            index='repository',
            doc_type='mods')
        if  result.get('hits').get('total') > 0:
            mods_id = result.get('hits')[0].get('_id')
            self.elastic.index(
                id=mods_id,
                index="repository",
                doc_type="mods",
                body=body)
            logging.info("Re-indexed PID=%s, ES-id=%s", pid, mods_id.get('_id'))
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
            err_title = "Failed to index PID {}, error={} url={}".format(
                pid,
                mods_result.status_code,
                mods_url)
            logging.error(err_title)
            # 404 error assume that MODS datastream doesn't exist for this
			# pid, return False instead of raising IndexerError exception
            if mods_result.status_code == 404:
                return False
            raise IndexerError(
                err_title,
                mods_result.text)
        mods_xml = etree.XML(mods_result.text)
        mods_body = mods2rdf(mods_xml)
        mods_body['pid'] = pid
        if parent:
            mods_body['inCollection'] = [parent,]
       
        
        if not self.__reindex_pid__(pid, mods_body):
            # Extract Islandora Content Models from REL-EXT 
            # Add Datasteams to Index
            mods_body["datastreams"] = self.__add_datastreams__(pid)
            #try:
            mods_index_result = self.elastic.index(
                index="repository",
                doc_type="mods",
                body=mods_body)
            #except:
            #    err_title = "Error indexing {},\nError {}".format(pid,
			#        sys.exc_info()[0])
            #    logging.error(err_title)
            #    print(err_title)
            #    return False
            mods_id = mods_index_result
            if mods_id is not None:
                logging.info(
                    "Indexed PID=%s, ES-id=%s",
                    pid,
                    mods_id.get('_id'))
                return True
        return False

    def index_collection(self, pid):
        """Method takes a parent collection PID, retrieves all children, and
        iterates through and indexes all pids

        Args:
            pid -- Collection PID
			children -- List of all children Fedora Object PIDs
        """
        sparql = """SELECT DISTINCT ?s
WHERE {{
  ?s <fedora-rels-ext:isMemberOfCollection> <info:fedora/{}> .
}}""".format(pid)
        started = datetime.datetime.utcnow()
        print("Started indexing collection {} at {}".format(
            pid,
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
            err_title = "Failed to index collection PID {}, error {}".format(
                pid,
                children_response.status_code)
            logging.error(err_title)
            raise IndexerError(
                err_title,
                children_response.text)
        end = datetime.datetime.utcnow()
        print("Indexing done {} at {}, total object {} total time {}".format(
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

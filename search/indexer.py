__author__ = "Jeremy Nelson"

import requests
import xml.etree.ElementTree as etree
from search.mods2json import mods2rdf

from . import conf, REPO_SEARCH

class Indexer(object):
    """Elasticsearch MODS and PDF full-text indexer for Fedora Repository 3.8"""

    def __init__(self, **kwargs):
        self.auth = kwargs.get("auth", conf.FEDORA_AUTH)
        self.es = kwargs.get("elasticsearch", REPO_SEARCH)
        self.rest_url = kwargs.get("rest_url", conf.REST_URL)
        self.ri_search = kwargs.get("ri_url", conf.RI_URL)
        # Set defaults if don't exist  
        if not self.auth:
            self.auth = ("fedoraAdmin", "fedoraAdmin")
        if not self.rest_url:
            self.rest_url = "http://localhost:8080/fedora/objects/"
        if not self.ri_search:
            self.ri_search = "http://localhost:8080/fedora/risearch"

    def __reindex_pid__(self, pid, body):
        """Internal method checks and if pid already exists"""
        if self.es.count().get('count') < 1:
            return False
        query = pid.replace(":", "\:")
        result = self.es.search(q=query, index='repository', doc_type='mods')
        if result.get('total') > 0:
            mods_id = result.get('hits')[0].get('_id')
            self.es.index(
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
            return
        if parent:
            mods_body['inCollection'] = [parent,]
        if not self.__reindex_pid__(pid, mods_body):
            mods_index_result = self.es.index(
                index="repository", 
                doc_type="mods", 
                body=mods_body)
            mods_id = mods_index_result  

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
        print("RI search URI {}".format(self.ri_search))
        children_response = requests.post(
            self.ri_search,
            data={"type": "tuples",
                  "lang": "sparql",
                  "format": "json",
                  "query": sparql},
            auth=self.auth)
        if children_response.status_code < 400:
            for row in children_response.json().get('results'):
                iri = row.get('s')
                child_pid = iri.split("/")[-1]
                self.index_pid(child_pid, parent=pid)
        else:
            raise IndexerError(
                "Failed to index collection PID {}, error {}".format(
                    pid,
                    children_response.status_code),
                children_response.text)

        
        
            
         
class IndexerError(Exception):

    def __init__(self, title, description):
        self.title = title
        self.description = description

    def __str__(self):
        return repr(self.title)

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
from copy import deepcopy
from rdflib import Namespace, RDF
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
from search.mods2json import mods2rdf
from search.mapping import MAP
from . import BASE_DIR, CONF, REPO_SEARCH

DC = Namespace("http://purl.org/dc/elements/1.1/")
FEDORA_ACCESS = Namespace("http://www.fedora.info/definitions/1/0/access/")
FEDORA = Namespace("info:fedora/fedora-system:def/relations-external#")
FEDORA_MODEL = Namespace("info:fedora/fedora-system:def/model#")
ISLANDORA = Namespace("http://islandora.ca/ontology/relsext#")
etree.register_namespace("fedora", str(FEDORA))
etree.register_namespace("fedora-model", str(FEDORA_MODEL))
etree.register_namespace("islandora", str(ISLANDORA))

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "index.log"),
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

logging.getLogger("requests").setLevel(logging.WARNING)

class Indexer(object):
    """Elasticsearch MODS and PDF full-text indexer for Fedora Repository 3.8"""

    def __init__(self, **kwargs):
        """Initializes an instance of the IndexerClass

		Keyword args:
		    auth -- Tuple of username and password to authenticate to Fedora,
			        defaults to Fedora's standard login credentials

			elasticsearch -- Instance of Elasticsearch Python Client, defaults
			                 to REPO_SEARCH from indexer

            rest_url -- REST URL for Fedora 3.x, defaults to Fedora's El contrabando de El Pasostanard
			ri_url -- SPARQL Endpoint, defaults to Fedora's standard search URL

		"""
        self.auth = kwargs.get("auth", CONF.FEDORA_AUTH)
        self.elastic = kwargs.get("elasticsearch", REPO_SEARCH)
        self.rest_url = kwargs.get("rest_url", CONF.REST_URL)
        self.ri_search = kwargs.get("ri_url", CONF.RI_URL)
        self.skip_pids = []
        # Set defaults if don't exist
        if not self.auth:
            self.auth = ("fedoraAdmin", "fedoraAdmin")
        if not self.rest_url:
            self.rest_url = "http://localhost:8080/fedora/objects/"
        if not self.ri_search:
            self.ri_search = "http://localhost:8080/fedora/risearch"
        print("Elastic search repository index exists {}".format(self.elastic.indices.exists('repository')))
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
            if mime_type.startswith("image/tif"):
                output = self.__process_tiff__(pid, datastreams)
                break
            if mime_type.startswith("application/pdf") or\
               mime_type.startswith("audio/mpeg") or\
               mime_type.startswith("video/quicktime") or\
               mime_type.startswith("video/mp4") or\
               mime_type.startswith("image/jpeg") or\
               mime_type.startswith("image/jp2") or\
               mime_type.startswith("audio/x-wav") or\
               mime_type.startswith("application/octet-stream"):
                add_ds = True
            if add_ds:
                output.append({
                    "pid": pid,
                    "label": row.attrib.get('label'),
                    "dsid": row.attrib.get('dsid'),
                    "mimeType": mime_type})
        return output


    def __index_compound__(self, pid):
        """Internal method takes a parent PID in a Compound Object and indexes
        all children.

        Args:
            pid -- PID of parent Fedora object
        """
        output = []
        sparql = """SELECT DISTINCT ?s
WHERE {{
   ?s <fedora-rels-ext:isConstituentOf> <info:fedora/{0}> .
}}""".format(pid)
        result = requests.post(
            self.ri_search,
            data={"type": "tuples",
                  "lang": "sparql",
                  "format": "json",
                  "query": sparql},
            auth=self.auth)
        if result.status_code > 399:
            raise IndexerError(
                "Could not retrieve {} constituent PIDS".format(pid),
                "Error code {} for pid {}\n{}".format(
                    result.status_code,
                    pid,
                    result.text))
        for row in result.json().get('results'):
            constituent_pid = row.get('s').split("/")[-1]
            self.skip_pids.append(constituent_pid)
            pid_as_ds = self.__process_constituent__(constituent_pid)
            if pid_as_ds is not None:
                output.extend(pid_as_ds)
        return output

    def __process_constituent__(self, pid, rels_ext=None):
        """Returns constituent PID and returns dictionary compatible with datastream

		Args:
		    pid -- PID
        """
        if not rels_ext:
            rels_ext = self.__get_rels_ext__(pid)
        xpath = "{{{0}}}Description/{{{1}}}isConstituentOf".format(
            RDF,
            FEDORA)
        isConstituentOf = rels_ext.find(xpath)
        parent_pid = isConstituentOf.attrib.get(
            "{{{0}}}resource".format(RDF)).split("/")[-1]
        xpath = "{{{0}}}Description/{{{1}}}isSequenceNumberOf{2}".format(
            RDF,
            ISLANDORA,
			parent_pid.replace(":","_"))
        sequence_number = rels_ext.find(xpath)
        order = sequence_number.text
        datastreams = self.__add_datastreams__(pid)
        for datastream in datastreams:
            datastream['order'] = order
        return datastreams
       
    def  __process_tiff__(self, pid, datastreams):
        """Takes a list of datastreams for an object that contains TIFF
        and attempts to retrieve jpeg derivatives.

        Args:
            pid: PID of Fedora Object with TIFF datastreams
            datastreams: List of datastreams

        Returns: 
            List of datastreams
        """
        output = []
        for row in datastreams:
            mime_type = row.attrib.get('mimeType')
            dsid = row.attrib.get('dsid')
            if mime_type.startswith("image/tif") or \
               dsid.startswith("JPG"):
                output.append(    {"pid": pid,
                    "label": row.attrib.get('label'),
                    "dsid": dsid,
                    "mimeType": mime_type
                    })
        return output
        
        
    def __get_rels_ext__(self, pid):
        """Extracts and returns RELS-EXT base on PID

        Args:
            pid -- PID
        """
        rels_ext_url = "{}{}/datastreams/RELS-EXT/content".format(
            self.rest_url,
            pid)

        rels_ext_result = requests.get(rels_ext_url)
        if rels_ext_result.status_code > 399:
            raise IndexerError("Cannot get RELS-EXT for {}".format(pid),
                "Tried URL {} status code {}\n{}".format(
                    rels_ext_url,
                    rels_ext_result.status_code,
                    rels_ext_result.text))
        return etree.XML(rels_ext_result.text)

    def __get_content_models__(self, pid, rels_ext=None):
        """Extracts and adds content models
        
		Args:
		    pid -- PID
            rels_ext -- XML of RELS-EXT, defaults to None
        """
        if not rels_ext:
            rels_ext = self.__get_rels_ext__(pid)
        output = []
        content_models = rels_ext.findall(
            "{{{0}}}Description/{{{1}}}hasModel".format(
                RDF,
                FEDORA_MODEL))
        if len(content_models) > 0:
            for model in content_models:
                content_model = model.attrib.get("{{{0}}}resource".format(RDF))
                # Remove and save to content_models
                output.append(content_model.split("/")[-1])
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


    def index_pid(self, pid, parent=None, inCollections=[]):
        """Method retrieves MODS and any PDF datastreams and indexes
        into repository's Elasticsearch instance

        Args:
            pid: PID to index
	        parent: PID of parent collection, default is None
			inCollections: List of pids that this object belongs int, used for
			    aggregations.

        Returns:
            boolean: True if indexed, False otherwise
        """
        rels_ext = self.__get_rels_ext__(pid)
        xpath = "{{{0}}}Description/{{{1}}}isConstituentOf".format(
            RDF,
            FEDORA)
        is_constituent = rels_ext.find(xpath)
        # Skip and don't index if pid is a constituent of another compound 
		# object
        if is_constituent is not None:
            return False
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
        try:
            mods_xml = etree.XML(mods_result.text)
        except etree.ParseError:
            msg = "Could not parse pid {}".format(pid)
            return False
        mods_body = mods2rdf(mods_xml)
        # Extract and process based on content model
        mods_body["content_models"] = self.__get_content_models__(pid, rels_ext)
        mods_body['pid'] = pid
        # Used for scoping aggregations
        if len(inCollections) > 0:
            mods_body['inCollections'] = inCollections
        # Used for browsing
        if parent:
            mods_body['parent'] = parent
        if not self.__reindex_pid__(pid, mods_body):
            # Add Datasteams to Index
            # Extract Islandora Content Models from REL-EXT 
            if "islandora:compoundCModel" in mods_body["content_models"]:
                mods_body["datastreams"] = self.__index_compound__(pid)
            else: 
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

    def index_collection(self, pid, parents=[]):
        """Method takes a parent collection PID, retrieves all children, and
        iterates through and indexes all pids

        Args:
            pid -- Collection PID
			parents -- List of all Fedora Object PIDs that pid is in the 
			            collection

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
                child_parents = deepcopy(parents)
                child_parents.append(pid)
                self.index_pid(child_pid, pid, child_parents)
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
                    self.index_collection(child_pid, child_parents)
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


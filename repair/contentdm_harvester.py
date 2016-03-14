__author__ = "Jeremy Nelson, Sarah Bogard"

import csv
import datetime
import mimetypes
import os
import requests
import sys
import urllib.parse

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from jinja2 import Template

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
from instance import conf as CONF

if hasattr(CONF, "ELASTIC_SEARCH"):
    REPO_SEARCH = Elasticsearch([CONF.ELASTIC_SEARCH])
else:
    REPO_SEARCH = Elasticsearch() # Use defaults

with open(os.path.join(BASE_DIR, "repair", "mods.xml")) as fo:
    MODS_TEMPLATE = Template(fo.read())

with open(os.path.join(BASE_DIR, "repair", "rels-ext.xml")) as fo:
    RELS_EXT_TEMPLATE = Template(fo.read())

GET_FILE_URL = "http://cdm16304.contentdm.oclc.org/utils/getfile/collection/"

EXISTING_SPARQL = """SELECT DISTINCT ?s
WHERE {{
  ?s <dc:title> "{0}" 
}}
"""

def _add_datastream(pid, raw_datastream, ident, label, mime_type):
    add_file_url = "{}{}/datastreams/{}?{}".format(
        CONF.REST_URL,
        pid,
        ident,
        urllib.parse.urlencode({"controlGroup": "M",
               "dsLabel": label,
               "mimeType": mime_type}))
    repo_add_result = requests.post(
         add_file_url,
         files={"content": raw_datastream},
         auth=CONF.FEDORA_AUTH)
    if repo_add_result.status_code > 399:
        print("Error {} with {}".format(
            repo_add_result.status_code, add_file_url))
        return False
    return True

def _add_rels_ext(pid, collection_pid, content_model):
     rels_ext = RELS_EXT_TEMPLATE.render(
         object_pid = pid,
         collection_pid = collection_pid,
         content_model = content_model)
     return _add_datastream(
         pid, 
         rels_ext, 
         "RELS-EXT", 
         "RDF Statements about this Object",
         "application/rdf+xml")
     
    
def _check_existing(title, creator):
    """Internal function takes a title and creator and searches Repository 
    for exact match on title and creator

    Args:
        title: Title string
        creator: Creator string
    Returns:
        PID of exact match 
    """
    sparql = EXISTING_SPARQL.format(title)
    existing_response = requests.post(
        CONF.RI_URL,
        data={"type": "tuples",
              "lang": "sparql",
               "format": "json",
               "query": sparql},
            auth=CONF.FEDORA_AUTH)
    if existing_response.status_code > 399:
        return
        print("Error with {}\nSPARQL\n{}".format(title, sparql))
        raise ValueError(existing_response.status_code,
                         existing_response.text)
    existing_pids = existing_response.json().get('results')
    if len(existing_pids) == 1:
        return existing_pids[0].get('s').split("/")[-1]
    

def _convert_date(date_str):
    if len(date_str) > 8:
        return datetime.datetime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    

def geology_thin_sections():
    pass

def gypsy_ames(filepath, gypsy_ames_pid="coccc:17501"):
    start = datetime.datetime.utcnow()
    reader = csv.DictReader(
	open(filepath),
	dialect='excel-tab')
    recs = [r for r in reader]
    existing_pids =[]
    print("Started Gypsy Ames Collection at {}".format(start))
    for i, row in enumerate(recs):
        title = row.get('Title')
        creator=row.get("Creator")
        ref_url = row.get('Reference URL')
        existing_ = _check_existing(title, creator)
        if existing_ is not None:
            existing_pids.append({"ref-url": ref_url,
                                  "pid": existing_})
            continue
        new_pid_result = requests.post(
            "{}new?namespace={}".format(
                CONF.REST_URL,
                "coccc"),
            auth=CONF.FEDORA_AUTH) 
        if new_pid_result.status_code > 399:
            continue
        new_pid = new_pid_result.text
        collection_frag = ref_url.split("collection/")[-1]
        filename = row.get('CONTENTdm file name')
        modify_obj_url = "{}{}?{}".format(
            CONF.REST_URL,
            new_pid,
            urllib.parse.urlencode(
                {"label": title,
                 "ownerID": CONF.FEDORA_AUTH[0],
                 "state": 'A'}))
        repo_modify_obj_result = requests.put(
            modify_obj_url,
            auth=CONF.FEDORA_AUTH)
        mods_xml = MODS_TEMPLATE.render(
            creator=creator,
            date_captured=row.get('Date Digital'),
            date_created=row.get('Date Original'),
            department="Theatre and Dance Department",
            title=title,
            type_of_resource=row.get('Type'))

        _add_datastream(
            new_pid,
            mods_xml,
            "MODS",
            "Metadata Object Description Schema",
            "text/xml")
        file_url = "{}{}/filename/{}".format(GET_FILE_URL, 
            collection_frag,
            filename)
        raw_file = requests.get(file_url).content
         
        _add_datastream(
            new_pid, 
            raw_file, 
            "OBJ",
            "{}{}".format(row.get('Local Identifier'),
                          filename), 
            mimetypes.guess_type(file_url)[0])
        _add_rels_ext(
            new_pid,  
            gypsy_ames_pid,
            "islandora:sp_large_image_cmodel")
        if not i%10 and i > 0:
            print(".", end="")
        if not i%100:
            print(" {} ".format(i), end="")
    end = datetime.datetime.utcnow()
    print("Total {} finished at {} total = {}".format(
        i, 
        end, 
        (end-start).seconds))
    return existing_pids
        
    
	
def ideas_merged(filepath, collection_pid="coccc:17501"):
    start = datetime.datetime.utcnow()
    reader = csv.DictReader(
	open(filepath. errors='ignore'),
	dialect='excel-tab')
    recs = [r for r in reader]
    print("Starting IDEAS (merged) at {}".format(start))
    for i, row in enumerate(recs):
        title = row.get('Title')
        creator = row.get('Artist/Creator')
        photographer = row.get('Photographer/Recorder')
        if len(creator) < 1:
            creator = photographer
        ref_url = row.get('Reference URL')
        topics = [r.strip() for r in rows.get('IDEAS Topic').split(";")]
        mods = MODS_TEMPLATE.render(
            abstract=row.get('Description'),
            creator=creator,
            photographer=photographer,
            topics=topics,
            title=title)

        
     

def harvest():
    gypsy_ames()
    #ideas_merged()
    #geology_thin_sections()
    

if __name__ == "__main__":
    harvest()

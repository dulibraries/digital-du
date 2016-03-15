__author__ = "Jeremy Nelson, Sarah Bogard"

import csv
import datetime
import mimetypes
import os
import requests
import rdflib
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

GEOSCIML_BASIC = rdflib.Namespace("")
GEOSCIML_EXT = rdflib.Namespace("http://xmlns.geosciml.org/GeoSciML-Extension/4.0")
GEOSCIML_PORTRAYAL = rdflib.Namespace("http://xmlns.geosciml.org/geosciml-portrayal/4.0")
GEOCONTAT_TYPE = rdflib.Namespace("http://resource.geosciml.org/classifierscheme/cgi/201211/contacttype/")
GEOSTR_RANK = rdflib.Namespace("http://resource.geosciml.org/classifier/cgi/stratigraphicrank/")
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
    

class Harvester(object):

    def __init__(self, filepath, collection_pid, conf=CONF):
        reader = csv.DictReader(
	    open(filepath, errors='ignore'),
	    dialect='excel-tab')
        self.collection_pid = collection_pid
        self.records = [r for r in reader]
        self.existing_pids = []
        self.conf = conf 

    def __new_fedora_object__(self, label):
        new_pid_result = requests.post(
            "{}new?namespace={}".format(
                self.conf.REST_URL,
                "coccc"),
            auth=self.conf.FEDORA_AUTH) 
        if new_pid_result.status_code > 399:
            return
        new_pid = new_pid_result.text
        modify_obj_url = "{}{}?{}".format(
            self.conf.REST_URL,
            new_pid,
            urllib.parse.urlencode(
                {"label": label,
                 "ownerID": CONF.FEDORA_AUTH[0],
                 "state": 'A'}))
        repo_modify_obj_result = requests.put(
            modify_obj_url,
            auth=self.conf.FEDORA_AUTH)
        return new_pid
       

    def harvest(self):
        start = datetime.datetime.utcnow()
        print("Starting {} Harvester at {} for {} records".format(
            Harvester.__name__,
            start,
            len(self.records)))  
        for i, row in enumerate(self.records):
            self.__process_record__(row)
            if not i%10 and i > 0:
                print(".", end="")
            if not i%100:
                print(" {} ".format(i), end="")
        end = datetime.datetime.utcnow()
        print("Total {} finished at {} total = {} seconds".format(
            i, 
            end, 
            (end-start).seconds))     


class GeologyThinSlices(Harvester):

    def __geo_linked_data__(self, pid, row):
        geo_subject = rdflib.URIRef(
            "https://digitalcc.coloradocollege.edu/pid/{}".format(pid))
        geo_graph = rdflib.Graph()
        topics = []
        locations = []
        notes = []
        names = []
        if len(row['Collector Name']) > 0:
            names.append({"role": "Collector",
                           "type": "personal",
                           "name": row['Collector Name']})
        if len(row['Collection Company']) > 0:
            names.append({"role": "Collector",
                           "type": "corporate",
                          "name": row['Collector Company']})
        if len(row['Course ID and Name']) > 0:
            parts = row['Course ID and Name'].split(";")
            for course in parts:
                notes.append({"displayLabel": "Course ID and Name",
                              "text": course.strip()})        
        if len(row['Exact Sample Location']) > 0:
            notes.append({"displayLabel": 'Exact Sample Location',
                          "text": row['Exact Sample Location']})
        if len(row['Geographic Sample Location']) > 0:
            locations.append(row['Geographic Sample Location'])
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.siteName,
                           rdflib.Literal(row['Geographic Sample Location'])))    

        if len(row['Formation Name']) > 0:
            topics.append(row['Formation Name'])
            geo_graph.add((geo_subject,
                           GEOSTR_RANK.formation,
                           rdflib.Literal(row['Formation Name'])))
        if len(row['Instructor Name']) > 0:
            instructors = row['Instructor Name'].split(";")
            for teacher in instructors:
                names.append({"role": "Teacher",
                              "type": "personal",
                              "name": teacher})
        if len(row['Literature Citation']) > 0:
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.source,
                           rdflib.Literal(row['Literature Citation'])))
        if len(row['Microscopic Description']) > 0:
            notes.append({"displayLabel": "Microscopic Description",
                          "text": row['Microscopic Description']})
        if len(row['Mineral Assemblage']) > 0:
            parts = row['Mineral Assemblage'].split(";")
            for name in parts:
                topics.append(name.strip())
                geo_graph.add(
                    (geo_subject,
                     GEOCONTAT_TYPE.mineralisation_assemblage_contact,
                     rdflib.Literal(name.strip())))
        if len(row['Microstructures']) > 0:
            parts = row['Microstructures'].split(";")
            for struct in parts:
                topics.append(struct.strip())
                geo_graph.add(
                    (geo_subject,
                     GEOSCIML_EXT.CompoundMaterialDescriptionType,
                     rdflib.Literal(struct.strip())))
        if len(row["Rock Name"]) > 0 and \
            not row["Rock Name"] in ["na", "???"]:
            topics.append(row["Rock Name"])
            geo_graph.add(
                (geo_subject,
                 GEOSCIML_PORTRAYAL.label,
                 rdflib.Literal(row["Rock Name"])))
        if len(row['Rock Class']) > 0:
            topics.append(row['Rock Class'])
            geo_graph.add((geo_subject,
                           GEOSCIML_BASIC.RockMaterialType,
                           rdflib.Literal(row['Rock Class'])))
        if len(row['Storage Location']) > 0:
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.currentLocation,
                           rdflib.Literal(row['Storage Location'])))
        


    def __process_record__(self, row):
        title = row.get("Thin Section ID")
        ref_url = row.get('Reference URL')
        filename = row.get('CONTENTdm file name')
        new_pid = self.__new_fedora_object__(title)

          
class GypsyAmes(Harvester):

    def __process_record__(self, row):
        title = row.get('Title')
        creator=row.get("Creator")
        ref_url = row.get('Reference URL')
        existing_ = _check_existing(title, creator)
        if existing_ is not None:
            self.existing_pids.append(
                {"ref-url": ref_url,
                 "pid": existing_})
            return
        new_pid = self.__new_fedora_object__(title)
        collection_frag = ref_url.split("collection/")[-1]
        filename = row.get('CONTENTdm file name')
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
            self.collection_pid,
            "islandora:sp_large_image_cmodel")

    
class IDEASMerged(Harvester):

    def __process_record__(self, row):
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

       

if __name__ == "__main__":
    harvest()

__author__ = "Jeremy Nelson, Sarah Bogard"

import csv
import datetime
import logging
import mimetypes
import os
import re
import requests
import rdflib
import sys
import urllib.parse
import warnings
import xml.etree.ElementTree as etree

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from jinja2 import Template


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
from instance import conf as CONF

logging.getLogger("requests").setLevel(logging.WARNING)

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

GEOSCIML_BASIC = rdflib.Namespace("http://xmlns.geosciml.org/GeoSciML-Basic/4.0/")
GEOSCIML_EXT = rdflib.Namespace("http://xmlns.geosciml.org/GeoSciML-Extension/4.0/")
GEOSCIML_PORTRAYAL = rdflib.Namespace("http://xmlns.geosciml.org/geosciml-portrayal/4.0/")
GEOCONTAT_TYPE = rdflib.Namespace("http://resource.geosciml.org/classifierscheme/cgi/201211/contacttype/")
GEOSTR_RANK = rdflib.Namespace("http://resource.geosciml.org/classifier/cgi/stratigraphicrank/")
SCHEMA_ORG = rdflib.Namespace("https://schema.org/")

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
                "codu"),
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
        warnings.filterwarnings("ignore")
        print("Starting {} Harvester at {} for {} records".format(
            Harvester.__name__,
            start,
            len(self.records)))  
        for i, row in enumerate(self.records):
            try:
                self.__process_record__(row)
            except:
                print("Error {} with {}".format(sys.exc_info()[0], i))
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
        geo_graph.namespace_manager.bind("gsmlb", GEOSCIML_BASIC)
        geo_graph.namespace_manager.bind("gsmle", GEOSCIML_EXT)
        geo_graph.namespace_manager.bind("gsmlp", GEOSCIML_PORTRAYAL)
        geo_graph.namespace_manager.bind("gsmct", GEOCONTAT_TYPE)
        geo_graph.namespace_manager.bind("gsmsr", GEOSTR_RANK)
        geo_graph.namespace_manager.bind("schema", SCHEMA_ORG)
        output = {
            "topics": [],
            "locations": [],
            "notes": [],
            "names":  []
        }
        if len(row['Collector Name']) > 0:
            collectors = row['Collector Name'].split(";")
            for collector in collectors:
                output['names'].append(
                    {"role": "Collector",
                     "type": "personal",
                     "name": collector.strip()})
        if len(row['Collection Company']) > 0:
            output['names'].append(
                {"role": "Collector",
                 "type": "corporate",
                 "name": row['Collection Company']})
        if len(row['Course ID and Name']) > 0:
            parts = row['Course ID and Name'].split(";")
            for course in parts:
                output['notes'].append(
                    {"displayLabel": "Course ID and Name",
                      "text": course.strip()})        
        if len(row['Exact Sample Location']) > 0:
            output['notes'].append(
                {"displayLabel": 'Exact Sample Location',
                 "text": row['Exact Sample Location']})
        if len(row['Geographic Sample Location']) > 0:
            output['locations'].append(row['Geographic Sample Location'])
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.siteName,
                           rdflib.Literal(row['Geographic Sample Location'])))    

        if len(row['Formation Name']) > 0:
            output['topics'].append(row['Formation Name'])
            geo_graph.add((geo_subject,
                           GEOSTR_RANK.formation,
                           rdflib.Literal(row['Formation Name'])))
        if len(row['Instructor Name']) > 0:
            instructors = row['Instructor Name'].split(";")
            for teacher in instructors:
                output['names'].append(
                    {"role": "Teacher",
                     "type": "personal",
                      "name": teacher})
        if len(row['Literature Citation']) > 0:
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.source,
                           rdflib.Literal(row['Literature Citation'])))
        if len(row['Microscopic Description']) > 0:
            output['abstract'] = row['Microscopic Description']
            geo_graph.add((geo_subject,
                           SCHEMA_ORG.description,
                           rdflib.Literal("{}\n{}".format(
                               'Microscopic Description',
                               row['Microscopic Description']))))
        if len(row['Mineral Assemblage']) > 0:
            parts = row['Mineral Assemblage'].split(";")
            for name in parts:
                output['topics'].append(name.strip())
                geo_graph.add(
                    (geo_subject,
                     GEOCONTAT_TYPE.mineralisation_assemblage_contact,
                     rdflib.Literal(name.strip())))
        if len(row['Microstructures']) > 0:
            parts = row['Microstructures'].split(";")
            for struct in parts:
                output['topics'].append(struct.strip())
                geo_graph.add(
                    (geo_subject,
                     GEOSCIML_EXT.CompoundMaterialDescriptionType,
                     rdflib.Literal(struct.strip())))
        if len(row["Rock Name"]) > 0 and \
            not row["Rock Name"] in ["na", "???"]:
            output['topics'].append(row["Rock Name"])
            geo_graph.add(
                (geo_subject,
                 GEOSCIML_PORTRAYAL.label,
                 rdflib.Literal(row["Rock Name"])))
        if len(row['Rock Class']) > 0:
            output['topics'].append(row['Rock Class'])
            geo_graph.add((geo_subject,
                           GEOSCIML_BASIC.RockMaterialType,
                           rdflib.Literal(row['Rock Class'])))
        if len(row["Reason For Use"]) > 0:
            output["notes"].append({"displayLabel": "Reason For Use",
                                    "text": row["Reason For Use"]})
        if len(row['Storage Location']) > 0:
            geo_graph.add((geo_subject,
                           GEOSCIML_PORTRAYAL.currentLocation,
                           rdflib.Literal(row['Storage Location'])))
        if len(row["Quantity"]) > 0:
            geo_graph.add((geo_subject,
                           SCHEMA_ORG.quantity,
                           rdflib.Literal(row["Quantity"])))
        output["graph-rdf"] = geo_graph.serialize(format='xml')
        return output 


    def __process_record__(self, row):
        title = row.get("Thin Section ID")
        existing_ = _check_existing(title, None)
        if existing_ is not None:
            self.existing_pids.append(existing_)
        ref_url = row.get('Reference URL')
        filename = row.get('CONTENTdm file name')
        if filename.endswith('jpg'):
            # Skip processing record should card
            return
        new_pid = self.__new_fedora_object__(title)
        _add_rels_ext(
            new_pid,  
            self.collection_pid,
            "islandora:sp_large_image_cmodel")
        ld_result = self.__geo_linked_data__(new_pid, row)
        _add_datastream(
            new_pid,
            ld_result.get('graph-rdf'),
            "GEO_LD",
            "Geology Linked Data",
            "application/rdf+xml")
        mods_xml = MODS_TEMPLATE.render(
            abstract=ld_result.get('abstract', None),
            names=ld_result.get('names', []),
            department="Geology Department",
            locations=ld_result.get('locations', []),
            notes=ld_result.get('notes', []),
            topics=ld_result.get('topics', []),
            date_captured=row.get('Year Collected', None),
            date_created=row.get('Date created'),
            title=title)
        _add_datastream(
            new_pid,
            mods_xml,
            "MODS",
            "Metadata Object Description Schema",
            "text/xml")
        collection_frag = ref_url.split("collection/")[-1]
        page_collection = collection_frag.split("id/")[0]
        postcard_url = "{}{}/filename/{}".format(GET_FILE_URL, 
            collection_frag,
            filename)
        postcard_result = requests.get(postcard_url)
        raw_postcard = postcard_result.content
        postcard = etree.XML(raw_postcard)
        pages = postcard.findall("page")
        for i, page in enumerate(pages):
            obj_id = "OBJ"
            if i > 0:
                obj_id = "{}{}".format(obj_id, i)
            pagefile = page.find('pagefile')
            page_img = pagefile.text
            title = page.find('pagetitle')
            page_id = page_img.split(".")[0]
            file_url = "{}{}id/{}/filename/{}".format(
                GET_FILE_URL,
                page_collection,
                page_id,
                page_img)
            raw_request = requests.get(file_url)
            if raw_request.status_code > 399:
                print("Failed to get {}".format(file_url))
                continue
            raw_file = raw_request.content
            _add_datastream(
                new_pid, 
                raw_file, 
                obj_id,
                "{}-{}".format(title.text,
                              page_img), 
                mimetypes.guess_type(page_img)[0])
 
              

          
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
    AUDIO_RE = re.compile(r"audio", re.IGNORECASE)
    CREATOR_DL_RE = re.compile(r"[^\d*];")
    PDF_RE = re.compile(r"pdf", re.IGNORECASE)
    VIDEO_RE = re.compile(r"video", re.IGNORECASE)

    def __guess_format__(self, row):
        format_raw = row.get('Format')
        format_val = 'still image'
        if IDEASMerged.PDF_RE.search(format_raw):
            format_val = 'text'
        if IDEASMerged.AUDIO_RE.search(format_raw):
            format_val = 'sound recording'
        if IDEASMerged.VIDEO_RE.search(format_raw):
            format_val = 'moving image'
        return format_val
 
    def __handle_creator__(self, row):
        raw_creator = row.get('Artist/Creator')
        names, notes = [], []
        if IDEASMerged.CREATOR_DL_RE.search(raw_creator):
            creator_list = raw_creator.split(";")
            for creator in creator_list:
                 # Any row length > 30, assume to be a note
                 if len(creator) >= 30:
                     notes.append(
                         {"type": "biographical/historical",
                          "text": creator})
                 elif len(creator) > 0:
                     names.append(
                         {"role": "creator",
                          "type": "personal",
                           "name": creator})
        elif raw_creator and len(raw_creator) > 0:
            names.append(
                {"role": "creator",
                 "type": "personal",
                 "name": raw_creator})
        return names, notes

    def __handle_collection_editor__(self, row, names, topics):
        editors = row['Collection Editor']
        for row1 in editors.split(";"):
            if "," in row1: # Assumes people in last name, first name
                names.append({"role": "Editor",
                              "type": "personal",
                              "name": row1})
            else:
                topics.append(row1)

    def __handle_dates__(self, row):
        dates, temporal = [], []
        if row['Accession Date'] and len(row['Accession Date']) > 0:
            dates.append({"tag": "dateOther",
                          "value":  row['Accession Date']})
        if row['Date Digital'] and len(row['Date Digital']) > 0:
            dates.append({"tag": "dateOther",
                          "value": row["Date Digital"]})
        if row['Date Photographed/Recorded'] and \
           len(row['Date Photographed/Recorded']) > 0:
            dates.append({"tag": "dateCaptured",
                          "value": row['Date Photographed/Recorded']})
            temporal.append(row['Date Photographed/Recorded'])
        if row['Date created'] and len(row['Date created']) > 0:
            dates.append({"tag": "dateCreated",
                          "keyDate": "yes",
                          "value": row['Date created']})
            temporal.append(row['Date created'])
        if row["Date modified"] and len(row["Date modified"]) > 0:
            dates.append({"tag": "dateModified",
                          "value": row["Date modified"]})
        if row['Date of Content'] and len(row['Date of Content']) > 0:
            dates.append({"tag": "dateValid",
                          "value": row['Date of Content']})
            temporal.append(row['Date of Content'])
        if row['Historical Period'] and len(row['Historical Period']) > 0:
            temporal.append(row['Historical Period'])
        return dates, temporal
        
    def __handle_identifiers__(self, row):
        identifiers = []
        if row["Getty Geographic ID"] and len(row["Getty Geographic ID"]) > 0:
            identifiers.append(
                {"type": "getty-geographic",
                 "displayLabel": "Getty Geographic ID",
                 "value": row["Getty Geographic ID"]})
        if row["IDEAS Identifier"] and len(row["IDEAS Identifier"]) > 0:
            identifiers.append(
                {"type": "ideas-local",
                 "displayLabel": "IDEAS Identifier",
                 "value": row["IDEAS Identifier"] })
        if row["OCLC number"] and len(row["OCLC number"]) > 0: 
            identifiers.append(
                {"type": "oclc",
                 "displayLabel": "OCLC number",
                 "value": row["OCLC number"]})
        return identifiers
              

    def __handle_languages__(self, row):
        raw_language = row.get('Language')
        languages = []
        if "ara" in raw_language:
            languages.append("Arabic")
        if "chn" in raw_language or \
           "Chinese" in raw_language:
           languages.append("Chinese")
        if "Dutch" in raw_language:
            languages.append("Dutch")
        if "eng" in raw_language or \
           "English" in raw_language:
            languages.append("English")
        if "hin" in raw_language:
            languages.append("Hindi")
        if "jpn" in raw_language or \
           "Japanese" in raw_language:
            languages.append("Japanese")
        if "kor" in raw_language or\
           "Korean" in raw_language:
            languages.append("Korean")
        if "Latin" in raw_language:
            languages.append("Latin")
        if "Mandarin" in raw_language or\
           "Manchu" in raw_language:
            languages.append("Chinese")
            languages.append("Mandarin")
        if "mar" in raw_language:
            languages.append("Marathi")
        if "Nepalese" in raw_language:
            languages.append("Nepalese")
        if "Pali" in raw_language:
            languages.append("Pali")
        if "san" in raw_language or\
           "Sanskrit" in raw_language:
            languages.append("Sanskrit")
        if "Tibetan" in raw_language:
            languages.append("Tibetan")
        if "tsubo" in raw_language:
            languages.append("Tsubo")
        return list(set(languages))

    def __handle_locations__(self, row):
        def __test_add__(name):
            if row[name] and len(row[name]) > 0:
                locations.append(row[name])
        locations = []
        __test_add__('Associated Places')
        __test_add__('Country')
        __test_add__('Work of Art, Original Location')
        __test_add__('Work of Art, Present Location') 
        if row['Latitude'] and len(row['Latitude']) > 0 and\
           row['Longitude'] and len(row['Longitude']) > 0:
           locations.append("Latitude {}, Longitude {}".format(
               row['Latitude'],
               row['Longitude']))
        return locations 

    def __handle_notes__(self, row, notes):
        if row['Notes'] and len(row['Notes']) > 0:
            notes.append({"type": "admin",
                          "text": row['Notes']})
        if row['Pedagogical Note'] and \
           len(row['Pedagogical Note']) > 0:
            notes.append({"displayLabel": "Pedagogical Note",
                          "text": row['Pedagogical Note']})
        if row['Source'] and len(row['Source']) > 0:
            notes.append({"type": "source note",
                          "text": row['Source']})
        if row['Work of Art, Original Location'] and \
           len(row['Work of Art, Original Location']) > 0:
            notes.append({"type": "original location",
                          "text": row['Work of Art, Original Location']})
        

    def __handle_topics__(self, row):
        topics = []
        for field_name in ['IDEAS Topic', 'Subject']:
            raw_field = row[field_name]
            if raw_field and len(raw_field) > 0:
                topics.extend([s.strip() for s in raw_field.split(";")])
        return topics
        

    def __process_record__(self, row):
        abstract = None
        title = row.get('Title')
        names, notes = self.__handle_creator__(row)
        locations = self.__handle_locations__(row)
        topics = self.__handle_topics__(row)
        dates, temporal = self.__handle_dates__(row)
        self.__handle_collection_editor__(row, names, topics)
        if row.get("Description") and len(row.get("Description")) > 0:
            abstract = row.get("Description")
        photographer = row.get('Photographer/Recorder')
        if photographer is not None and len(photographer) > 0: 
            names.append({"role": "photographer",
                          "type": "personal",
                          "name": photographer})
        dates, temporal = self.__handle_dates__(row)
        rights = row.get("Permissions")
        if rights and len(rights) < 1:
            rights = None
        if row.get('Institution Name') and \
           len(row.get('Institution Name')) > 0:
               institution = {"name": row.get('Institution Name')}
        else:
               institution = None
        ref_url = row.get('Reference URL')
        type_of_resource = self.__guess_format__(row)
        mods_xml = MODS_TEMPLATE.render(
            abstract=abstract,
            dates=dates,
            department="Asian Studies Program",
            extent=row.get('Extent'),
            identifiers=self.__handle_identifiers__(row),
            institution=institution,
            languages=self.__handle_languages__(row),
            locations=locations,
            names=names,
            notes=notes,
            rights=rights,
            temporal=temporal,
            topics=topics,
            title=title,
            type_of_resource=type_of_resource)
        etree.XML(mods_xml) # Parse to insure valid MODS
        # First create new fedora obj
        new_pid = self.__new_fedora_object__(title)
        # Add MODS
        _add_datastream(
            new_pid,
            mods_xml,
            "MODS",
            "Metadata Object Description Schema",
            "text/xml")
        content_model = "islandora:sp_large_image_cmodel"
        if type_of_resource.startswith('sound recording'):
            content_model = "islandora:sp-audioCModel"
        if type_of_resource.startswith('moving image'):
            content_model = "islandora:sp_videoCModel"
        if type_of_resource.startswith("text"):
            content_model = "islandora:sp_document"
        # Add RELS-EXT datastream
        _add_rels_ext(
            new_pid,  
            self.collection_pid,
            "islandora:sp_large_image_cmodel")
        filename = row.get("CONTENTdm file name")
        collection_frag = ref_url.split("collection/")[-1]
        file_url = "{}{}/filename/{}".format(GET_FILE_URL, 
            collection_frag,
            filename)
        file_result = requests.get(file_url)
        raw_file = file_result.content
        # Add Object
        _add_datastream(
            new_pid, 
            raw_file, 
            "OBJ",
            filename,               
            mimetypes.guess_type(file_url)[0])

if __name__ == "__main__":
    harvest()

__author__ "Jeremy Nelson, Sarah Bogard"

import csv
import datetime
import os
import requests
import sys

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

with open(os.path.join(BASE_DIR, "repair", "mods.xml") as fo:
    MODS_TEMPLATE = Template(fo.read())

GET_FILE_URL = "http://cdm16304.contentdm.oclc.org/utils/getfile/collection/"

def _convert_date(date_str):
    if len(date_str) > 8:
        return datetime.datetime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    

def geology_thin_sections():
    pass

def gypsy_ames(filepath):
    reader = csv.DictReader(
	open(filepath),
	dialect='excel-tab')
    recs = [r for r in reader]
    for row in recs:
        title = row.get('Title')
        creator=row.get("Creator")
        mods_xml = MODS_TEMPLATE.render(
            creator=creator,
            date_captured=row.get('Date Digital'),
            date_created=row.get('Date Original'),
            department="",
            title=title,
            type_of_resource=row.get('Type') 
    
	
    pass

def ideas_merged():
    pass

def harvest():
    gypsy_ames()
    ideas_merged()
    geology_thin_sections()
    

def __name__ == "__main__":
    harvest()

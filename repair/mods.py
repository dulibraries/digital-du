"""Module repairs errors with MODS metadata"""
__author__ = "Jeremy Nelson, Sarah Bogard"


import os
import requests
import sys

import xml.etree.ElementTree as etree
import rdflib
MODS = rdflib.Namespace("http://www.loc.gov/mods/v3")
etree.register_namespace("mods", str(MODS))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
from instance import conf as CONF

def update_mods(pid, field_xpath, old_value, new_value):
    """Function takes pid, field, and old_value, replaces with
	a new_value.

    Args:
        pid -- 
		field_xpath -- 
		old_value -- 
		new_value --
    """
    mods_url = "{}{}/datastreams/MODS/content".format(
        CONF.REST_URL,
        pid)
    mods_result = requests.get(
        mods_url,
        auth=CONF.FEDORA_AUTH)
    if mods_result.status_code > 399:
        err_title = """"Failed to replace {} with {} for PID {}, 
error={} url={}""".format(
            old_value, 
            new_value, 
            pid,
            mods_result.status_code,
            mods_url)
    mods_xml = etree.XML(mods_result.text)
    old_value_elements = mods_xml.findall(field_xpath)
    for element in old_value_elements:
        if element.text == old_value:
            element.text = new_value
    print(etree.tostring(mods_xml).decode())

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

class RepairMODSError(Exception):

    def __init__(self, pid, message):
        self.pid = pid
        self.message = message

    def __str__(self):
        return "Error with {}'s MODS\n{}".format(self.pid, self.message)

def update_mods(pid, field_xpath, old_value, new_value):
    """Function takes pid, field, and old_value, replaces with
	a new_value.

    Args:
        pid -- 
		field_xpath -- 
		old_value -- 
		new_value --
    """
    mods_base_url = "{}{}/datastreams/MODS/".format(
        CONF.REST_URL,
        pid)
    get_mods_url = "{}content".format(mods_base_url)
    mods_result = requests.get(
        get_mods_url,
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
    put_result = requests.put(
        mods_base_url,
        files={"file": ('MODS', etree.tostring(mods_xml))},
        auth=CONF.FEDORA_AUTH)
    if put_result.status_code < 300:
        return True
    else:
        raise RepairMODSError(
            pid, 
            "Failed to update MODS with PUT\nStatus code {}\n{}".format(
                put_result.status_code,
                put_result.text))

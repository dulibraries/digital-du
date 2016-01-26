"""Module repairs errors with MODS metadata"""
__author__ = "Jeremy Nelson, Sarah Bogard"

import datetime
import os
import requests
import sys

import xml.etree.ElementTree as etree
import rdflib
import urllib.parse

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
    start = datetime.datetime.utcnow()
    mods_base_url = "{}{}/datastreams/MODS".format(
        CONF.REST_URL,
        pid)
    get_mods_url = "{}/content".format(mods_base_url)
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
    # Create backup of MODS
    backup_mods_filename = os.path.join(
        BASE_DIR, 
        "repair",
        "backups",
        "{}-mods-{}.xml".format(pid, start.strftime("%Y-%m-%d")))
    print(backup_mods_filename, os.path.exists(backup_mods_filename))
    return
    if not os.path.exists(backup_mods_filename):
        with open(backup_mods_filename, "wb+") as mods_file:
            mods_file.write(mods_result.text.encode())
    old_value_elements = mods_xml.findall(field_xpath)
    for element in old_value_elements:
        if element.text == old_value:
            element.text = new_value
    mods_update_url = "{}?{}".format(
        mods_base_url,
        urllib.parse.urlencode({"controlGroup": "M",
            "dsLabel": "MODS",
            "mimeType": "text/xml"}))
    raw_xml = etree.tostring(mods_xml)
    put_result = requests.post(
        mods_update_url,
		files={"content":  raw_xml},
        auth=CONF.FEDORA_AUTH)
    print(put_result.status_code)
    if put_result.status_code < 300:
        return True
    else:
        raise RepairMODSError(
            pid, 
            "Failed to update MODS with PUT\nStatus code {}\n{}".format(
                put_result.status_code,
                put_result.text))

def update_multiple(
    pid_list,
    field_xpath,
    old_value,
    new_value):
    """Function takes a list of PIDs, the MODS field xpath, the old value to be 
    replaced by the new value.

    Args:
        pid_list -- Listing of PIDs
        field_xpath -- Field XPath
        old_value -- Old string value to be replaced
        new_value -- New string value
    """
    start = datetime.datetime.utcnow()
    print("Starting MODS update for {} PIDS at {}".format(
        len(pid_list), 
        start.isoformat()))
    errors = []
    for i, pid in enumerate(pid_list):
        if not update_mods(pid, field_xpath, old_value, new_value):
            print("Could update MODS for PID {}".format(pid))
            errors.append(pid)
        if not i%25:
            print(i, end="")
        elif not i%10:
            print(".", end="")
    end = datetime.datetime.utcnow()
    print("Finished updating MODS for {}, errors {} at {}, total {}".format(
        len(pid_list),
        len(errors),
        end.isoformat()
        (end-start).seconds / 60.0))

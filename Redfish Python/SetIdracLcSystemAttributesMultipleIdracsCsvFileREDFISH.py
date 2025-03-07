#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2025, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
#
# Edited CSV file example:
#
#iDRAC IP	iDRAC Username	iDRAC Password	ServerPwr.1.PSRapidOn   IPMILan.1.AlertEnable   IPMILan.1.Enable

#10.10.1.10	root	        calvin	        Enabled	                Enabled                 Enabled          
#11.11.1.11	root	        calvin	        Enabled	                Disabled                Disabled
#
# Note: The first 3 columns do not change the name, they need to be iDRAC IP, iDRAC Username and iDRAC Password.
# For the other columns pass in attribute names you want to configure. In the CSV file example i pass in these attributes
# to set but you can pass in as many attributes as you want in the CSV file,
# just make sure the value you want to apply is listed under that attribute.
#
# Script pseudo code workflow:
#
# 1. Read the CSV file and get attribute names and values or each iDRAC listed.
# 2. Script will loop through each iDRAC setting the attribute values as stated in the CSV file. 



import argparse
import csv
import getpass
import json
import logging
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to set multiple iDRAC, LC or System attributes for multiple iDRACs using a CSV file.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--csv-filename', help='Pass in CSV filename', dest="csv_filename", required=False)
parser.add_argument('-ip',help='iDRAC IP address, this is only supported to get attributes for one iDRAC.', required=False)
parser.add_argument('-u', help='iDRAC username, this is only supported to get attributes for one iDRAC.', required=False)
parser.add_argument('-p', help='iDRAC password, this is only supported to get attributes for one iDRAC.', required=False)
parser.add_argument('--get-idrac-attributes', help='Get all supported iDRAC attributes', action="store_true", dest="get_idrac_attributes", required=False)
parser.add_argument('--get-system-attributes', help='Get all supported system attributes', action="store_true", dest="get_system_attributes", required=False)
parser.add_argument('--get-lc-attributes', help='Get all supported lifecycle controller (LC) attributes', dest="get_lc_attributes", action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SetIdracLcSystemAttributesMultipleIdracsCsvFileREDFISH.py --csv-filename idrac_details.csv, this example will configure multiple attributes for multiple iDRACs using CSV file.
    \n- python SetIdracLcSystemAttributesMultipleIdracsCsvFileREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-idrac-attributes, this example will return iDRAC attributes for one iDRAC.""")
    return

def get_idrac_attributes():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1?$select=Attributes' % args["ip"], verify=verify_cert,auth=(args["u"], args["p"]))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get iDRAC attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    pprint(data)

def get_system_attributes():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/System.Embedded.1?$select=Attributes' % args["ip"], verify=verify_cert,auth=(args["u"], args["p"]))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get System attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    pprint(data)

def get_lc_attributes():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/LifecycleController.Embedded.1?$select=Attributes' % args["ip"], verify=verify_cert,auth=(args["u"], args["p"]))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get LC attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    pprint(data)


def set_attributes():
    global idrac_ip
    global idrac_username
    global idrac_password 
    attributes_dict = {}
    set_idrac_attributes = {"Attributes":{}}
    set_system_attributes = {"Attributes":{}}
    set_lc_attributes = {"Attributes":{}}
    for i in attribute_dict.items():
        if "idrac ip" in i[0].lower():
            idrac_ip = i[1]
        elif "idrac username" in i[0].lower():
            idrac_username = i[1]
        elif "idrac password" in i[0].lower():
            idrac_password = i[1]
        else:
            attributes_dict[i[0]] = i[1]
            
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1?$select=Attributes' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get iDRAC attributes to build dict, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in attributes_dict.items():
        if i[0] in data["Attributes"].keys():
            set_idrac_attributes["Attributes"][i[0]] = i[1]

    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/System.Embedded.1?$select=Attributes' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get System attributes to build dict, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in attributes_dict.items():
        if i[0] in data["Attributes"].keys():
            set_system_attributes["Attributes"][i[0]] = i[1]
    
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/LifecycleController.Embedded.1?$select=Attributes' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get LC attributes to build dict, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in attributes_dict.items():
        if i[0] in data["Attributes"].keys():
            set_lc_attributes["Attributes"][i[0]] = i[1]
    # Set iDRAC attributes
    if set_idrac_attributes["Attributes"] != {}:
        logging.info("- INFO, setting iDRAC attributes for iDRAC %s: %s" % (idrac_ip, set_idrac_attributes["Attributes"]))
        for i in set_idrac_attributes["Attributes"].items():
            response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    for iii in ii.items():
                        if iii[0] == "Type":
                            if iii[1] == "Integer":
                                set_idrac_attributes["Attributes"][i[0]] = int(i[1])
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1' % idrac_ip
        payload = set_idrac_attributes
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully set iDRAC attributes for iDRAC %s" % idrac_ip)
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            logging.error("\n- FAIL, PATCH command failed to set iDRAC attributes(s) for iDRAC %s, status code %s returned" % (idrac_ip, response.status_code))
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
    else:
        logging.info("- WARNING, no iDRAC attributes detected in CSV file, PATCH command will skip setting iDRAC attributes")
    # Set System attributes
    if set_system_attributes["Attributes"] != {}:
        logging.info("- INFO, setting System attributes for iDRAC %s: %s" % (idrac_ip, set_system_attributes["Attributes"]))
        for i in set_system_attributes["Attributes"].items():
            response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    for iii in ii.items():
                        if iii[0] == "Type":
                            if iii[1] == "Integer":
                                set_system_attributes["Attributes"][i[0]] = int(i[1])
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/System.Embedded.1' % idrac_ip
        payload = set_system_attributes
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully set System attributes for iDRAC %s" % idrac_ip)
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            logging.error("\n- FAIL, PATCH command failed to set System attributes(s) for iDRAC %s, status code %s returned" % (idrac_ip, response.status_code))
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
    else:
        logging.info("- WARNING, no System attributes detected in CSV file, PATCH command will skip setting System attributes")
    # Set LC attributes
    if set_lc_attributes["Attributes"] != {}:
        logging.info("- INFO, setting LC attributes for iDRAC %s: %s" % (idrac_ip, set_lc_attributes["Attributes"]))
        for i in set_lc_attributes["Attributes"].items():
            response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    for iii in ii.items():
                        if iii[0] == "Type":
                            if iii[1] == "Integer":
                                set_lc_attributes["Attributes"][i[0]] = int(i[1])
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/LifecycleController.Embedded.1' % idrac_ip
        payload = set_lc_attributes
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully set LC attributes for iDRAC %s" % idrac_ip)
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            logging.error("\n- FAIL, PATCH command failed to set LC attributes(s) for iDRAC %s, status code %s returned" % (idrac_ip, response.status_code))
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
                                
    else:
        logging.info("- WARNING, no LC attributes detected in CSV file, PATCH command will skip setting LC attributes")
    


            
if __name__ == "__main__":
    verify_cert = False
    if args["script_examples"]:
        script_examples()
    elif args["get_idrac_attributes"]:
        get_idrac_attributes()
    elif args["get_system_attributes"]:
        get_system_attributes()
    elif args["get_lc_attributes"]:
        get_lc_attributes()
    elif args["csv_filename"]:
        file_path = args["csv_filename"]
        count = 1
        idrac_config_jobs = {}
        # Get contents from CSV file 
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            idrac_dict = {}
            for line_number, line_data in enumerate(csv_reader, start=1):
                try:
                    if "idrac ip" in line_data[0].lower():
                        csv_row_names = line_data
                        csv_row_names[0] = "iDRAC IP"
                        continue
                    else:
                        idrac_details_attribute_values = line_data
                except:
                    break
                attribute_dict = {}
                for i,ii in zip(csv_row_names, idrac_details_attribute_values):
                    attribute_dict[i] = ii
                idrac_name ="idrac%s" % count
                idrac_dict[idrac_name]= {"iDRAC IP": attribute_dict["iDRAC IP"], "iDRAC Username": attribute_dict["iDRAC Username"], "iDRAC Password": attribute_dict["iDRAC Password"]}
                set_attributes()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

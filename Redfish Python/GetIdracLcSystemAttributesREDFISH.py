#!/usr/bin/python3
#
# GetIdracLcSystemAttributesREDFISH. Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run this script first to get attributes with current values before you execute SetIdracLcSystemAttributesREDFISH script.
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
#
# Copyright (c) 2017, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import getpass
import json
import logging
import os
import re
import requests
import sys
import time
import warnings

from pprint import pprint
from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--group-name', help='Get attributes pass in the group name. Supported values are \"idrac\", \"lc\" and \"system\"', dest="group_name", required=False)
parser.add_argument('--attribute-name', help='Get specific attribute value, pass in the attribute name. Make sure to also pass in --group-name argument.', dest="attribute_name", required=False)
parser.add_argument('--get-registry', help='Get the attribute registry for all iDRAC, System and LC attributes. This option is helpful for viewing attributes to see if they are read only or read write, supported possible values.', dest="get_registry", action="store_true", required=False)
parser.add_argument('--registry-attribute', help='Get attribute registry information for a specific attribute, pass in the attribute name', dest="registry_attribute", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --group-name idrac, this example wil get all iDRAC attributes and echo them to the screen along with copy output to a file.
    \n- GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --group-name idrac --attribute-name LDAPRoleGroup.1.Privilege, this example will only return current value for attribute LDAPRoleGroup.1.Privilege.
    \n- GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-registry, this example will return the attribute registry for iDRAC, LC and System attributes.
    \n- GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -x b21af7b065989c576f4011ac554b2b61 --registry-attribute SNMPAlert.7.State, this example using iDRAC x-auth token session will return registry information for only attribute SNMPAlert.7.State.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_attribute_registry():
    try:
        os.remove("idrac_attribute_registry.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step" % "idrac_attribute_registry.txt")
    open_file = open("idrac_attribute_registry.txt","w")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['RegistryEntries']['Attributes']:
        for ii in i.items():
            message = "%s: %s" % (ii[0], ii[1])
            open_file.writelines(message)
            print(message)
            message = "\n"
            open_file.writelines(message)
        message = "\n"
        print(message)
        open_file.writelines(message)
    logging.info("\n- Attribute registry is also captured in \"idrac_attribute_registry.txt\" file")
    open_file.close()

def attribute_registry_get_specific_attribute():
    logging.info("\n- INFO, searching attribute registry for attribute \"%s\"" % args["registry_attribute"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['RegistryEntries']['Attributes']:
        if args["registry_attribute"] in i.values():
            logging.info("\n- Attribute Registry information for attribute \"%s\" -\n" % args["registry_attribute"])
            for ii in i.items():
                print("%s: %s" % (ii[0],ii[1]))
            sys.exit(0)
    logging.error("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % args["registry_attribute"])
        
def get_attribute_group():
    global current_value
    if args["group_name"] == "idrac":
        fqdd = "iDRAC.Embedded.1"
    elif args["group_name"] == "lc":
        fqdd = "LifecycleController.Embedded.1"
    elif args["group_name"] == "system":
        fqdd = "System.Embedded.1"
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/%s/Attributes' % (idrac_ip, fqdd), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/%s/Attributes' % (idrac_ip, fqdd), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict = data['Attributes']
    logging.info("\n- %s Attribute Names and Values:\n" % args["group_name"].upper())
    sorted_dict = {}
    open_file = open("attributes.txt","w")
    for i in attributes_dict.items():
        if 'odata' not in i[0]:
            sorted_dict[i[0]] = i[1]
    try:
        for i in sorted(sorted_dict.iterkeys()):
            message = "Name: %s, Value: %s" % (i, sorted_dict[i])
            print(message)
            open_file.writelines("%s\n" % message)
    except:
        for i in attributes_dict:
            message = "Name: %s, Value: %s" % (i, attributes_dict[i])
            print(message)
            open_file.writelines("%s\n" % message)
    open_file.close()
    logging.info("\n- INFO, attribute enumeration also copied to \"attributes.txt\" file")
    
def get_specific_attribute():
    global current_value
    if args["group_name"] == "idrac":
        fqdd = "iDRAC.Embedded.1"
    elif args["group_name"] == "lc":
        fqdd = "LifecycleController.Embedded.1"
    elif args["group_name"] == "system":
        fqdd = "System.Embedded.1"
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/%s/Attributes' % (idrac_ip, fqdd), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/%s/Attributes' % (idrac_ip, fqdd), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict = data['Attributes']
    for i in attributes_dict:
        if i == args["attribute_name"]:
            logging.info("\nAttribute Name: %s, Current Value: %s" % (i, attributes_dict[i]))
            sys.exit(0)
    logging.error("\n- FAIL, unable to locate attribute \"%s\". Either current iDRAC version installed doesn\'t support this attribute or iDRAC missing required license" % args["attribute_name"])
  
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip=args["ip"]
        idrac_username=args["u"]
        if args["p"]:
            idrac_password=args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- Argument -p not detected, pass in iDRAC user %s password: " % args["u"])
        if args["ssl"]:
            if args["ssl"].lower() == "true":
                verify_cert = True
            elif args["ssl"].lower() == "false":
                verify_cert = False
            else:
                verify_cert = False
        else:
            verify_cert = False
        check_supported_idrac_version()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get_registry"]:
        get_attribute_registry()
    elif args["registry_attribute"]:
        attribute_registry_get_specific_attribute()
    elif args["group_name"] and args["attribute_name"]:
        get_specific_attribute()
    elif args["group_name"]:
        get_attribute_group()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

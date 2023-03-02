#!/usr/bin/python3
#
# SetIdracLcSystemAttributesREDFISH. Python script using Redfish API to set either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run script GetIdracLcSystemAttributesREDFISH first to return attributes with current values. 
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 14.0
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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to set either iDRAC, lifecycle controller or system attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--set', help='Set attributes, pass in the group name of the attributes you want to configure. Supported values are \"idrac\", \"lc\" and \"system\"', required=False)
parser.add_argument('--attribute-names', help='Pass in the attribute name you want to configure. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: Make sure you are passing in the correct attributes which match the value you are passing in for argument -s. Note: Attribute names are case sensitive, make sure to pass in the exact syntax of the attribute name', dest="attribute_names", required=False)
parser.add_argument('--attribute-values', help='Pass in the attribute value you want to set the attribute to. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value. Note: Attribute values are case sensitive, make sure to pass in the exact syntax of the attribute value', dest="attribute_values", required=False)
parser.add_argument('--get-registry', help='Get the attribute registry for all iDRAC, System and LC attributes. This option is helpful for viewing attributes to see if they are read only or read write, supported possible values.', dest="get_registry", action="store_true", required=False)
parser.add_argument('--registry-attribute', help='Get attribute registry information for a specific attribute, pass in the attribute name', dest="registry_attribute", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-registry, this example will return complete attribute registry and redirect output to a text file.
    \n- SetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --registry-attribute SNMPAlert.8.SNMPv3UserID, this example will return registry details for only this attribute.
    \n- SetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set idrac --attribute-names EmailAlert.4.Enable --attribute-values Disabled, this example shows setting one iDRAC attribute.
    \n- SetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set idrac --attribute-names Time.1.Timezone,Telnet.1.Enable,RemoteHosts.1.SMTPServerIPAddress --attribute-values CST6CDT,enabled,test.labs.net, this example shows setting multiple iDRAC attributes.""")
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

def set_attributes():
    global url
    global payload
    global static_ip_set
    global static_ip_value
    global attribute_names
    static_ip_value = ""
    static_ip_set = "no"
    if args["set"] == "idrac":
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    elif args["set"] == "lc":
        url = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip
    elif args["set"] == "system":
        url = 'https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip
    else:
        print("\n- FAIL, invalid value entered for -s argument")
        sys.exit(0)
    if args["x"]:
        response = requests.get('%s' % (url), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('%s' % (url), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    payload = {"Attributes":{}}
    attribute_names = args["attribute_names"].split(",")
    attribute_values = args["attribute_values"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        payload["Attributes"][i] = ii
    logging.info("\n- INFO, configuring \"%s\" attributes\n" % args["set"].upper())
    for i in payload["Attributes"].items():
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                for iii in ii.items():
                    if iii[0] == "Type":
                        if iii[1] == "Integer":
                            payload["Attributes"][i[0]] = int(i[1])
    for i in payload["Attributes"].items():
        logging.info(" Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
        if i[0].lower() == "IPv4Static.1.Address".lower():
            static_ip_set = "yes"
            static_ip_value = i[1]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, PATCH command passed to successfully set \"%s\" attribute(s), status code %s returned\n" % (args["set"].upper(), response.status_code))
        if "error" in data.keys():
            logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
            logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
    else:
        logging.error("\n- FAIL, Command failed to set %s attributes(s), status code is: %s\n" % (args["set"].upper(),response.status_code))
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)

def get_new_attribute_values():
    logging.info("- INFO, getting new attribute current values")
    time.sleep(30)
    if "IPv4.1.Address" in attribute_names:
        logging.info("- INFO, static IP address change detected, script will validate changes using new IP address\n")
        url_new = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % payload["Attributes"]["IPv4.1.Address"]
        if args["x"]:
            response = requests.get('%s' % (url_new), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('%s' % (url_new), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        attributes_dict = data['Attributes']
        for i in payload["Attributes"].items():
            if i[1] == attributes_dict[i[0]]:
                logging.info("- Attribute Name: %s, Attribute Value: %s" % (i[0], attributes_dict[i[0]]))
            else:
                logging.info("- INFO, attribute %s current value is not set to %s, current value: %s" % (i[0], i[1], attributes_dict[i[0]]))
    elif static_ip_set == "no":
        response = requests.get('%s' % (url),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        attributes_dict = data['Attributes']
        for i in payload["Attributes"].items():
            if i[1] == attributes_dict[i[0]]:
                logging.info("- Attribute Name: %s, Attribute Value: %s" % (i[0], attributes_dict[i[0]]))
            else:
                logging.info("- INFO, attribute %s current value is not set to %s, current value: %s" % (i[0], i[1], attributes_dict[i[0]]))
    elif static_ip_set == "yes":
        logging.info("- INFO, DHCP to static IP change detected, will use new IP to validate attribute changes\n")
        url_new = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % static_ip_value
        if args["x"]:
            response = requests.get('%s' % (url_new), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('%s' % (url_new), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        attributes_dict = data['Attributes']
        for i in payload["Attributes"].items():
            if i[1] == attributes_dict[i[0]]:
                 logging.info("- Attribute Name: %s, Attribute Value: %s" % (i[0], attributes_dict[i[0]]))
            else:
                logging.info("- INFO, attribute %s current value is not set to %s, current value: %s" % (i[0], i[1], attributes_dict[i[0]]))
        
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
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
    elif args["set"] and args["attribute_names"] and args["attribute_values"]:
        set_attributes()
        if "Pass" in args["attribute_names"]:
            logging.info("- PASS, attribute \"%s\" successfully changed" % args["attribute_names"])
        else:
            get_new_attribute_values()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

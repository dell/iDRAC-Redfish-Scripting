#!/usr/bin/python3
#
# GetEthernetInterfacesREDFISH. Python script using Redfish API to get ethernet interface information.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
#
# Copyright (c) 2018, Dell, Inc.
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

from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to get ethernet interface information')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-fqdds', help='Get ethernet interface fqdds', action="store_true", dest="get_fqdds", required=False)
parser.add_argument('--get-all', help='Get all details for all ethernet devices in the server', action="store_true", dest="get_all", required=False)
parser.add_argument('--get', help='Get ethernet FQDD detailed information for a specific FQDD, pass in ethernet FQDD. Example, pass in NIC.Integrated.1-1-1', required=False)
parser.add_argument('--get-properties', help='Get specific FQDD properties for all ethernet devices, pass in property name. To get the list of property names, first execute --get-all to get detailed information which will return the property values. Make sure to pass in the exact string as this value is case sensitive. Note: Multiple properties can be passed in by using a comma separator', dest="get_properties", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get NIC.Integrated.1-1-1, this example will return detailed information for NIC.Integrated.1-1-1 only.
    \n- GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-fqdds, this example will return only ethernet FQDDs detected for the server.
    \n- GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all, this example will returned detailed information for all ethernet devices detected in the server. 
    \n- GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-properties LinkStatus,PermanentMACAddress,IPv4Addresses, this example will only return these specific properties for all NIC interfaces detected.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_ethernet_fqdds():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get ethernet interface details, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    logging.info("\n- Ethernet interface FQDDs for iDRAC %s -\n" % idrac_ip)
    for i in data['Members']:
        for ii in i.items():
            print(ii[1].split("/")[-1])

def get_ethernet_interfaces():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get ethernet interface details, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit()
    logging.info("\n- Ethernet interface details for iDRAC %s -\n" % idrac_ip)
    for i in data['Members']:
        pprint(i)
        print("\n")

def get_specific_ethernet_interface():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, args["get"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, args["get"]), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get ethernet interface details, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit()
    logging.info("\n- Ethernet interface details for %s -\n" % args["get"])
    for i in data.items():
        pprint(i)

def get_specific_ethernet_property():
    ethernet_fqdds = []
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get ethernet interface details, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data['Members']:
        for ii in i.items():
            ethernet_fqdds.append(ii[1].split("/")[-1])
    data = response.json()
    if "," in args["get_properties"]:
        argument_properties = args["get_properties"].split(",")
    else:
        argument_properties = [args["get_properties"]]   
    for i in ethernet_fqdds:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in argument_properties:
            if i not in data.keys():
                logging.warning("\n- WARNING, property %s not detected, check to make sure spelling and case is correct" % i)
                argument_properties.remove(i)
        if argument_properties == []:
            logging.error("- ERROR, no valid properties passed in to get details, check to make sure spelling and case is correct")
            sys.exit(0)
        logging.info("\n- Specific property details for %s -\n" % i)
        for i in data.items():
            if i[0] in argument_properties:
                print(i)
               
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
    if args["get_all"]:
        get_ethernet_interfaces()
    elif args["get_fqdds"]:
        get_ethernet_fqdds()
    elif args["get"]:
        get_specific_ethernet_interface()
    elif args["get_properties"]:
        get_specific_ethernet_property()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

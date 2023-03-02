#!/usr/bin/python3
#
# GetAssemblyInventoryREDFISH. Python script using Redfish API DMTF to get system assembly or hardware inventory
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2019, Dell, Inc.
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
import pickle
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to get system assembly (hardware) inventory(output will be printed to the screen and also copied to a text file). This includes information for storage controllers, memory, network devices, motherboard(planar), power supplies, backplanes")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-details-all', help='Get detailed information for all chassis assembly URIs', action="store_true", dest="get_details_all", required=False)
parser.add_argument('--get-details-uri', help='Get detailed information for only a specific chassis assembly URI, pass in the URI', dest="get_details_uri", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetAssemblyInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-details-all, this example will get detailed information for all chassis assembly URIs.
    \n- GetAssemblyInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-details-uri /redfish/v1/Chassis/System.Embedded.1/Assembly/DIMM.Socket.A2, this example will only return data for this URI""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def get_details_all():
    logging.info("\n- INFO, chassis assembly details for iDRAC %s - \n" % idrac_ip)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    for i in data.items():
        pprint(i)

def get_specific_uri_info():
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_details_uri"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_details_uri"]), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit(0)
    logging.info("\n- Detailed information for URI %s -\n" % args["get_details_uri"])
    for i in data.items():
        pprint(i)
       
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
    if args["get_details_all"]:
          get_details_all()
    elif args["get_details_uri"]:
        get_specific_uri_info()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

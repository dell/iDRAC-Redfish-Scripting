#!/usr/bin/python3
#
# GetIdracMessageRegistryREDFISH. Python script using Redfish API with OEM extension to get iDRAC message registry.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
#
# Copyright (c) 2020, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API with OEM extension to get iDRAC message registry. This is helpful for finding out details on a message ID or error message returned from executing any Redfish command against iDRAC.')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get', help='Get message registry details', action="store_true", required=False)
parser.add_argument('--message-id', help='Get information for only a specific message id, pass in the message ID string', dest="message_id", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracMessageRegistryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get the complete message registry, print to the screen and also capture in a text file.
    \n- GetIdracMessageRegistryREDFISH.py -ip 192.168.0.120 -u root -p calvin --message-id SYS409, this example will return information for only message ID SYS409.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_message_registry():
    try:
        os.remove("message_registry.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step" % "message_registry.txt")
    open_file = open("message_registry.txt","w")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Messages'].items():
        pprint(i), print("\n")
        message = "Message ID: %s" % i[0]
        open_file.writelines("\n%s"% message)
        for ii in i[1].items():
            message = "%s: %s" % (ii[0], ii[1])
            open_file.writelines("\n%s"% message)
        message = "\n"
        open_file.writelines("%s"% message)
    open_file.close()
    logging.info("\n- INFO, output also captured in \"message_registry.txt\" file")

def get_specific_message_id():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Messages'].items():
        if i[0].lower() == args["message_id"].lower():
            logging.info("\nMessage ID: %s" % i[0])
            for ii in i[1].items():
                print("%s: %s" % (ii[0], ii[1]))
            print("\n")
            sys.exit(0)
    logging.error("\n - FAIL, either invalid message ID was passed in or message ID does not exist on this iDRAC version")
    
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
    if args["get"]:
        get_message_registry()
    elif args["message_id"]:
        get_specific_message_id()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

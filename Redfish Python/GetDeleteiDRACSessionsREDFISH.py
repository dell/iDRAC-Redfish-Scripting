#!/usr/bin/python3
#
# GetDeleteiDRACSessionsREDFISH. Python script using Redfish API to either get current iDRAC sessions or delete iDRAC session
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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
import re
import requests
import sys
import time
import warnings

from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC sessions or delete an iDRAC session. NOTE: current DMTF doesn't support Type property which this information is needed to know which session you want to delete. As a workaround, you can get this information using remote RACADM command which support has been added in this script.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get', help='Get current iDRAC sessions running and details', action="store_true", required=False)
parser.add_argument('--delete', help='Delete an iDRAC session, pass in the session ID', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetDeleteiDRACSessionsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return current iDRAC active sessions.
    \n- GetDeleteiDRACSessionsREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete 2, this example will delete iDRAC session 2 and validate it has been deleted.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Sessions' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Sessions' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    
def get_current_iDRAC_sessions():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Sessions?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Sessions?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to get iDRAC session details, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    logging.info("\n- Current running session(s) detected for iDRAC %s -\n" % idrac_ip) 
    for i in data['Members']:
        pprint(i), print("\n")

def delete_session():
    url = 'https://%s/redfish/v1/Sessions/%s' % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: DELETE command passed to delete session id \"%s\", status code %s returned" % (args["delete"], response.status_code))
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Sessions/%s' % (idrac_ip, args["delete"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Sessions/%s' % (idrac_ip, args["delete"]), verify=verify_cert, auth=(idrac_username, idrac_password))
        if response.status_code == 404:
            logging.info("- PASS, validation passed to confirm session %s has been deleted" % args["delete"])
        else:
            logging.info("- FAIL, validation failed to confirm session %s has been deleted and still exists" % args["delete"])
            sys.exit(0)
    else:
        logging.error("\n- FAIL, DELETE command failed, status code returned %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- DELETE command failure:\n %s" % data)
        sys.exit(0)
   
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
        get_current_iDRAC_sessions()
    elif args["delete"]:
        delete_session()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

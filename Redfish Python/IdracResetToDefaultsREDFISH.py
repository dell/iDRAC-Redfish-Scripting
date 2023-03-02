#!/usr/bin/python3
#
# IdracResetToDefaultsREDFISH. Python script using Redfish API to reset iDRAC to default settings.
#
# NOTE: Once the script is complete, iDRAC will reset to complete the process and you will lose network connection. iDRAC should be back up within a few minutes.
# 
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to reset the iDRAC to default settings')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--reset-type', help='Pass in the iDRAC reset type. Supported values are 1, 2 and 3. 1 for All(All configuration is set to default), 2 for ResetAllWithRootDefaults(All configuration including network is set to default. Exception root user password set to calvin) or 3 for Default(All configuration is set to default except users and network settings are preserved)', dest="reset_type", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- IdracResetToDefaultsREDFISH.py -ip 192.168.0.120 -u root -p calvin --reset-type 2, this example will reset iDRAC to default settings, user ID 2 account will be set to root/calvin.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- FAIL, status code %s detected, incorrect iDRAC credentials detected" % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- FAIL, GET request failed to validate JobService is supported, status code %s returned. Error:\n%s" % (response.status_code, data))
        sys.exit(0)

def reset_idrac_to_default_settings():
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults" % idrac_ip
    if args["reset_type"] == "1":
        payload = {"ResetType":"All"}
        reset_type = "All"
    elif args["reset_type"] == "2":
        payload = {"ResetType":"ResetAllWithRootDefaults"}
        reset_type = "ResetAllWithRootDefaults"
    elif args["reset_type"] == "3":
        payload = {"ResetType":"Default"}
        reset_type = "Default"
    else:
        logging.error("\n- FAIL, invalid value passed in for --reset-type. Execute script with -h to see supported values for --reset-type argument.")
        sys.exit(0)
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC to \"%s\" setting\n" % (response.status_code, reset_type))
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, error is: \n%s" % (response.status_code, data))
        sys.exit(0)
    time.sleep(15)
    logging.info("- INFO, iDRAC will now reset and be back online within a few minutes.")
    
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    reset_idrac_to_default_settings()

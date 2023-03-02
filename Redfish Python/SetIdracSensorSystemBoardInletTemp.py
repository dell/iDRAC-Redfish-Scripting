#!/usr/bin/python3
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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to either get or set min/max system board inlet temps")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current system board inlet temp readings', action="store_true", required=False)
parser.add_argument('--min', help='Pass in value to set min warning threshold (lower caution) for system board inlet temp', required=False)
parser.add_argument('--max', help='Pass in value to set max warning threshold (upper caution) for system board inlet temp', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SetIdracSensorSystemBoardInletTemp.py -ip 192.168.0.120 -u root -p calvin --get, this example will get the current system board inlet temp readings.
    \n- SetIdracSensorSystemBoardInletTemp.py -ip 192.168.0.120 -u root -p calvin --min 4 --max 46, this example will set both min and max inlet temp readings. """)
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_current_system_board_temps():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET request failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    else:
        logging.info("\n- INFO, current system board inlet temp readings \n")
    for i in data["Thresholds"].items():
        pprint(i)

def set_inlet_temp():
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp" % idrac_ip
    if args["min"]:
        logging.info("\n- INFO, setting LowerCaution property to %s reading" % args["min"])
        payload = {"Thresholds":{"LowerCaution":{"Reading":int(args["min"])}}}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("- PASS, PATCH operation passed to set LowerCaution property")
        else:
            logging.error("- FAIL, PATCH command failed to set LowerCaution property, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
            sys.exit(0)
    if args["max"]:
        logging.info("\n- INFO, setting UpperCaution property to %s reading" % args["max"])
        payload = {"Thresholds":{"UpperCaution":{"Reading":int(args["max"])}}}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("- PASS, PATCH operation passed to set UpperCaution property")
        else:
            logging.error("- FAIL, PATCH command failed to set UpperCaution property, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
            sys.exit(0)
            
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
    if args["get"]:
        get_current_system_board_temps()
    elif args["min"] or args["max"]:
        set_inlet_temp()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

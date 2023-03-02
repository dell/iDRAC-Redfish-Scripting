#!/usr/bin/python3
#
# SupportAssistCollectionLocalREDFISH. Python script using Redfish API with OEM extension to perform scheduled auto SupportAssist collection.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2022, Dell, Inc.
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

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform scheduled auto SupportAssist collections.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current auto SupportAssist collection schedule details.',action="store_true", required=False)
parser.add_argument('--clear', help='Clear auto SupportAssist collection schedule details.',action="store_true", required=False)
parser.add_argument('--set', help='Set auto SupportAssist collection schedule.',action="store_true", required=False)
parser.add_argument('--recurrence', help='Set auto SupportAssist collection schedule, pass in recurrence value. Supported values: Weekly, Monthly and Quarterly',required=False)
parser.add_argument('--time', help='Set auto SupportAssist collection schedule, pass in time value. Value format: HH:MMAM/PM, example: \"06:00PM\"',required=False)
parser.add_argument('--dayofweek', help='Set auto SupportAssist collection schedule, pass in day of week. Supported values: Mon, Tue, Wed, Thu, Fri, Sat, Sun or * for all days of the week',required=False)
parser.add_argument('--dayofmonth', help='Set auto SupportAssist collection schedule, pass in day of month. Supported values: 1 through 32 or L for last day or * for all days of the month',required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current SupportAssist auto schedule details.
    \n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --set --recurrence Monthly --time "06:00PM" --dayofweek Sat --dayofmonth L, this example shows setting SupportAssist auto collection schedule which will run monthly at 6PM on the last Saturday of the month.
    \n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear, this example shows clearing SupportAssist auto schedule details.""")
    sys.exit(0)

def check_supported_idrac_version():
    supported = ""
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.error("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "SupportAssistCollection" in i:
            supported = "yes"
    if supported == "no":
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_support_assist_auto_collection_details():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetAutoCollectSchedule' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to get SupportAssist auto collection details\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
    for i in data.items():
        if "ExtendedInfo" not in i[0]:
            print("%s: %s" % (i[0], i[1]))

def clear_support_assist_auto_collection_details():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistClearAutoCollectSchedule' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to clear SupportAssist auto collection details\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)

def set_support_assist_auto_collection():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistSetAutoCollectSchedule' % (idrac_ip)
    payload = {}
    if args["recurrence"]:
        payload["Recurrence"] = args["recurrence"]
    if args["time"]:
        payload["Time"] = args["time"]
    if args["dayofweek"]:
        payload["DayOfWeek"] = args["dayofweek"]
    if args["dayofmonth"]:
        payload["DayOfMonth"] = args["dayofmonth"]       
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to set SupportAssist auto collection details\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
            
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
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
        get_support_assist_auto_collection_details()
    elif args["clear"]:
        clear_support_assist_auto_collection_details()
    elif args["set"] and args["recurrence"] and args["time"] and args["dayofweek"] and args["dayofmonth"]:
        set_support_assist_auto_collection()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

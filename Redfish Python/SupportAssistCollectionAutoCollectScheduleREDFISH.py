#
# SupportAssistCollectionLocalREDFISH. Python script using Redfish API with OEM extension to perform scheduled auto SupportAssist collection.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('--script-examples', help='Get examples of executing script.', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current auto SupportAssist collection schedule details.',action="store_true", required=False)
parser.add_argument('--clear', help='Clear auto SupportAssist collection schedule details.',action="store_true", required=False)
parser.add_argument('--set', help='Set auto SupportAssist collection schedule.',action="store_true", required=False)
parser.add_argument('--recurrence', help='Set auto SupportAssist collection schedule, pass in recurrence value. Supported values: Weekly, Monthly and Quarterly',required=False)
parser.add_argument('--time', help='Set auto SupportAssist collection schedule, pass in time value. Value format: HH:MMAM/PM, example: \"06:00PM\"',required=False)
parser.add_argument('--dayofweek', help='Set auto SupportAssist collection schedule, pass in day of week. Supported values: Mon, Tue, Wed, Thu, Fri, Sat, Sun or * for all days of the week',required=False)
parser.add_argument('--dayofmonth', help='Set auto SupportAssist collection schedule, pass in day of month. Supported values: 1 through 32 or L for last day or * for all days of the month',required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current SupportAssist auto schedule details.
    \n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --set --recurrence Monthly --time "06:00PM" --dayofweek Sat --dayofmonth L, this example shows setting SupportAssist auto collection schedule which will run monthly at 6PM on the last Saturday of the month.
    \n- SupportAssistCollectionAutoCollectScheduleREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear, this example shows clearing SupportAssist auto schedule details.""")

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.warning("\n- WARNING, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to validate DellLCService URI is supported")
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
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
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
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
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
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to set SupportAssist auto collection details\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
            

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    else:
        check_supported_idrac_version()
    if args["get"]:
        get_support_assist_auto_collection_details()
    elif args["clear"]:
        clear_support_assist_auto_collection_details()
    elif args["set"] and args["recurrence"] and args["time"] and args["dayofweek"] and args["dayofmonth"]:
        set_support_assist_auto_collection()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")

    
    
        
            
        
        

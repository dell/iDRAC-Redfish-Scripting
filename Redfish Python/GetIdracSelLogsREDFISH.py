#!/usr/bin/python3
#
# GetIdracSelLogsREDFISH. Python script using Redfish API to get iDRAC System Event Logs (SEL) logs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

parser = argparse.ArgumentParser(description="Python script using Redfish API to get iDRAC System Event Logs (SEL) logs.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current iDRAC SEL log', action="store_true", required=False)
parser.add_argument('--clear', help='Clear iDRAC SEL log', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracSelLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get the complete iDRAC system event log.
    \n- GetIdracSelLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear, this example will clear iDRAC system event log.""")
    sys.exit(0)

def get_iDRAC_version():
    global iDRAC_version
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        return
    elif response.status_code != 200:
        print("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    server_generation = int(data["Model"].split(" ")[0].replace("G",""))
    if server_generation <= 13:
        iDRAC_version = "old"
    else:
        iDRAC_version = "new"

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_SEL_logs():
    try:
        os.remove("iDRAC_SEL_logs.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step" % "iDRAC_SEL_logs.txt")
    open_file = open("iDRAC_SEL_logs.txt","w")
    date_timestamp = datetime.now()
    logging.info("\n- INFO, getting iDRAC SEL details, this may take 15-30 seconds to complete depending on log size")
    current_date_time = "- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (date_timestamp.month, date_timestamp.day, date_timestamp.year, date_timestamp.hour, date_timestamp.minute, date_timestamp.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if iDRAC_version == "old":
        uri = "/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Sel"
    elif iDRAC_version == "new":
        uri = "/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries"
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get iDRAC SEL entries, status code %s returned" % response.status_code)
        sys.exit(0)
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            SEL_log_entry = ("%s: %s" % (ii[0],ii[1]))
            print(SEL_log_entry)
            open_file.writelines("%s\n" % SEL_log_entry)
        print("\n")
        open_file.writelines("\n")
    if iDRAC_version == "old":
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Sel?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Sel?$skip=%s' % (idrac_ip, seq), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data or data["Members"] == [] or response.status_code == 400:
                break
            for i in data['Members']:
                for ii in i.items():
                    SEL_log_entry = ("%s: %s" % (ii[0], ii[1]))
                    print(SEL_log_entry)
                    open_file.writelines("%s\n" % SEL_log_entry)
                print("\n")
                open_file.writelines("\n")
    logging.info("\n- INFO, system event logs also captured in \"iDRAC_SEL_logs.txt\" file")
    open_file.close()
    sys.exit(0)

def clear_SEL():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Actions/LogService.ClearLog' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS: POST command passed to clear iDRAC SEL, status code %s returned" % response.status_code)
        sys.exit(0)
    else:
        logging.error("\n- FAIL, POST command failed to clear iDRAC SEL, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
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
        get_iDRAC_version()
    if args["clear"]:
        clear_SEL()
    elif args["get"]:
        get_SEL_logs()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    get_SEL_logs()

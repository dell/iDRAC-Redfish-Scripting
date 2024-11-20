#!/usr/bin/python3
#
# ResetIdracREDFISH. Python script using Redfish API to reset iDRAC.
#
# NOTE: Once the script is complete, iDRAC will reset to complete the process and you will lose network connection. iDRAC should be back up within a few minutes.
# 
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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
import platform
import re
import requests
import subprocess
import sys
import time
import warnings

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to reset(reboot) iDRAC')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--check', help='Pass in this argument to check iDRAC is fully back up after iDRAC reset. Script will loop until success ping request is returned, then check API status to confirm iDRAC is ready', action="store_true", required=False) 
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ResetIdracREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will reset iDRAC and be back online after a few minutes, same behavior as \"racadm racreset\" command""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def reset_idrac():
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % idrac_ip
    payload={"ResetType":"GracefulRestart"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC\n" % response.status_code)
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, detailed error results \n%s" % (response.status_code, data))
        sys.exit(0)
    logging.info("- INFO, iDRAC will now reset and be back online within a few minutes.")

def check_idrac_connection():
    logging.info("- INFO, argument --check detected, script will start ping requests in 3 minutes")
    time.sleep(180)
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        logging.error("- FAIL, unable to determine OS type, check iDRAC connection function will not execute")
        sys.exit(0)
    while True:
        execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE)
        if execute_command != 0:
            logging.info("- INFO, unable to ping iDRAC IP, script will wait 30 seconds and try again")
            time.sleep(30)
            continue
        else:
            logging.info("- PASS, ping command successful to iDRAC IP, script will now check to validate iDRAC is fully up and ready")
            time.sleep(15)
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
            method = "GetRemoteServicesAPIStatus"
            payload = {}
            if args["x"]:
                headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
            data=response.json()
            if response.status_code == 200:
                logging.debug("\n- PASS: POST command passed for %s method, status code 200 returned\n" % method)
            else:
                logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                sys.exit(0)
            if data["Status"] == "Ready":
                logging.info("- PASS, iDRAC is fully up and in ready state")
                return
            else:
                logging.info("- INFO, iDRAC not fully up and ready, script will wait 30 seconds and try again")
                time.sleep(30)

           
    
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
    reset_idrac()
    if args["check"]:
        check_idrac_connection()
        

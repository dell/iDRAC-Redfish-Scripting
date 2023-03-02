#!/usr/bin/python3
#
# ChangeIdracUserPasswordREDFISH. Python script using Redfish API with OEM extension to change iDRAC username password. Once the password is changed, the script will also execute a GET command to verify the password change was successful.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to change iDRAC username password. Once the password is changed, the script will execute GET command to verify the password change was successful.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get iDRAC user account information. This will return detailed information for each iDRAC user account.', action="store_true", required=False)
parser.add_argument('--user-id', help='Pass in the iDRAC user account ID you want to change the password for. If needed, use argument -g to get the iDRAC user account ID.', dest="user_id", required=False)
parser.add_argument('--new-pwd', help='Pass in the new password you want to set for the iDRAC user ID. If you do not pass in this argument, script will prompt to enter new password and will not be echoed to the screen.', dest="new_pwd", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ChangeIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get user account information for all iDRAC users.
    \n- ChangeIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u user -p calvin --user-id 3 --new-pwd pAssw0rd, this example shows changing iDRAC user ID 3 password.
    \n- ChangeIdracUserPasswordREDFISH.py -ip 192.168.0.120 -x 983d154b4a125c7ae3838b8e32256b78 --user-id 8, this example using iDRAC X-auth token session will first prompt to enter new password, then change the password for user ID 8.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_iDRAC_user_account_info():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts?$expand=*($levels=1)' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
        sys.exit(0)
    logging.info("\n- iDRAC User Account Information -")
    for i in data["Members"]:
        pprint(i)
        print("\n")
                
def change_idrac_user_password():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["user_id"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["user_id"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code 401 detected, check iDRAC username / password credentials and privilege level")
        sys.exit(0)
    data = response.json()
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["user_id"])
    if not args["new_pwd"]:
        args["new_pwd"] = getpass.getpass("\n- Argument --new-pwd not detected, pass in new user password: ")
    payload = {'Password': args["new_pwd"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS, status code %s returned for PATCH command to change iDRAC user password for user ID %s" % (response.status_code, args["user_id"]))
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, password was not changed. Detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    if args["x"]:
        logging.info("\n- INFO, X-auth token session detected. If you changed the user password for the user account that created the token, this token is no longer valid and needs to be recreated") 
    
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
        get_iDRAC_user_account_info()
    elif args["user_id"] or args["new_pwd"]:
        idrac_account_id = args["user_id"]
        idrac_new_password = args["new_pwd"]
        change_idrac_user_password()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

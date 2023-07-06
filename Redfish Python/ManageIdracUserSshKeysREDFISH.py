#!/usr/bin/python3
#
# ManageIdracUserSshKeysREDFISH.py Python script using Redfish API to manage iDRAC user account SSH keys. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2023, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to manage iDRAC user account SSH keys.')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-user-ids', help='Get iDRAC user account ID for all enabled iDRAC users', action="store_true", required=False)
parser.add_argument('--get-user-keys', help='Get current iDRAC user account installed SSH keys, pass in the user account ID', dest="get_user_keys", required=False)
parser.add_argument('--install-key', help='Install iDRAC user SSH key pass in user account ID', dest="install_key", required=False)
parser.add_argument('--key-string', help='Install iDRAC user SSH key pass in SSH key string', dest="key_string", required=False)
parser.add_argument('--delete-key-user-id', help='Delete iDRAC user SSH key pass in user account ID', dest="delete_key_user_id", required=False)
parser.add_argument('--delete-key-id', help='Delete iDRAC user SSH key pass in the key ID you want to delete', dest="delete_key_id", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ManageIdracUserSshKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-user-keys 2, this example will current installed keys for iDRAC user ID 2.
    \n- ManageIdracUserSshKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin --install-key 2 --key-string "ssh-rsa AAAAB3NzaC1yc2EDAQAgQDnzUYFHz+mYB6dCjKtqoMw9+udigTWRPpY60X8wOE1BevTxdRM+foB19wewW2V4AGcznbKrUU3Vd66Mm4X23U4Zj7lxyfSiqOfx9C5eIGVqWfHtuW9MhDXIomLnuP9DMaOypOBWExwkNPSa9q/SAQLiBglX3FLLWQtOwTwGA0sXhIz+DDn0s9fMsOYY24nsGYOwfzaDcVPaQks2N8hSHVUu+0N52S+awCDLJ6p1GqAweFmYlL3QZ9ei+IYaV+W9K9ciVLLcyE7yYNdVamzckTfSxt+tRDc7wXHGtiVKLufVEhIIW+tXAe/qk/aCb+noUwFABwOXvfVl8BPE8Da7ayOaz4hSDkmv2BuQP1+VinCE/9/sn4pNI9g0pF31CMWz+UePbdsCt+D8HdV9YhQRTU6yMc+L10IEQD5uY4j3G/k9g8o8NvEm9xb3YuSq3uYZYBlJooXonWPfoq6PX5OpwsITBmCEiIoAMXU42uKlWLCd5GdW/1xwNFB833yarBDpXs= root@good.example.com, this example shows installing SSH key for iDRAC user ID 2."
    \n- ManageIdracUserSshKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete-key-user-id 2 --delete-key-id 1, this example shows deleting key 1 for iDRAC user ID 2.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts/2/Keys' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts/2/Keys' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_idrac_user_ids():
    logging.info("\n- INFO, current enabled iDRAC user ID(s)\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get iDRAC user account IDs, status code %s returned" % response.status_code)
        sys.exit(0)
    for i in data["Members"]:
        for ii in i.items():
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logging.warning("\n- WARNING, GET command failed to get iDRAC user account IDs, status code %s returned" % response.status_code)
                sys.exit(0)
            if data["Id"] != "1" and data["Enabled"] != False:
                print("Username: %s, ID: %s" % (data["UserName"], data["Id"]))
            
def get_idrac_user_SSH_keys():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts/%s/Keys?$expand=*($levels=1)' % (idrac_ip, args["get_user_keys"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/AccountService/Accounts/%s/Keys?$expand=*($levels=1)' % (idrac_ip, args["get_user_keys"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    if data["Members"] == []:
        logging.info("\n- WARNING, no SSH keys installed for user ID %s" % args["get_user_keys"])
        sys.exit(0)
    print("\n")
    for i in data["Members"]:
        pprint(i)
                            
def install_user_SSH_key():    
    url = 'https://%s/redfish/v1/AccountService/Accounts/%s/Keys' % (idrac_ip, args["install_key"])
    payload = {"KeyType":"SSH", "KeyString":args["key_string"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 201:
        logging.info("\n- PASS, status code %s returned for POST command to install iDRAC user SSH key" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed, status code %s returned" % response.status_code)
        sys.exit(0)

def delete_user_SSH_key():
    url = 'https://%s/redfish/v1/AccountService/Accounts/%s/Keys/%s' % (idrac_ip, args["delete_key_user_id"], args["delete_key_id"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, status code %s returned for DELETE command to remove iDRAC user SSH key" % response.status_code)
    else:
        logging.error("\n- FAIL, DELETE command failed, status code %s returned" % response.status_code)
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
    if args["get_user_ids"]:
        get_idrac_user_ids()
    elif args["get_user_keys"]:
        get_idrac_user_SSH_keys()
    elif args["install_key"] and args["key_string"]:
        install_user_SSH_key()
    elif args["delete_key_user_id"] and args["delete_key_id"]:
        delete_user_SSH_key()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

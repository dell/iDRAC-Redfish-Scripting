#!/usr/bin/python3
#
# CreateXAuthTokenSessionREDFISH. Python script using Redfish API to create X-AUTH token session for iDRAC user.
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
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
import requests
import sys
import time
import warnings

from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to create or delete X-AUTH token session for iDRAC user.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--create', help='Create X-auth token session', action="store_true", required=False)
parser.add_argument('--get-sessions', help='Get iDRAC sessions information. You must also use argument -u and -p', dest="get_sessions", action="store_true", required=False)
parser.add_argument('--delete', help='Delete X-auth-token session or any iDRAC session, pass in the session ID.', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current iDRAC sessions information.
    \n- CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -u root --create, this example will first prompt to enter user password, then create X auth token session for iDRAC.
    \n- CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete 28, this example will delete iDRAC session ID 28.""")
    sys.exit(0)
    
def get_redfish_version():
    global session_uri
    response = requests.get('https://%s/redfish/v1' % idrac_ip,verify=False, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        try:
            response = requests.get('https://%s/redfish/v1' % (idrac_ip),verify=False, headers={'X-Auth-Token': args["t"]})
            if response.status_code == 401:
                logging.info("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
                sys.exit(0)
            else:
                data = response.json()
        except:
            logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
            sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get Redfish version, status code %s returned" % response.status_code)
        sys.exit(0)
    redfish_version = int(data["RedfishVersion"].replace(".",""))
    if redfish_version >= 160:
        session_uri = "redfish/v1/SessionService/Sessions"
    elif redfish_version < 160:
        session_uri = "redfish/v1/Sessions"
    else:
        logging.error("- ERROR, unable to select URI based off Redfish version")
        sys.exit(0)

def get_session_info_using_username_password():
    response = requests.get('https://%s/%s' % (idrac_ip, session_uri), auth=(idrac_username, idrac_password), verify=False)
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
        sys.exit(0)
    elif response.status_code != 200:
        logging.error("- FAIL, GET request failed, status code %s returned. Detailed error results:\n %s" % (response.status_code, data))
        sys.exit(0)
    if data["Members"] == []:
        logging.warning("\n- WARNING, no sessions detected for iDRAC %s" % idrac_ip)
        sys.exit(0)
    else:
        sessions_list = []
        for i in data["Members"]:
            for ii in i.items():
                sessions_list.append(ii[1])
    logging.info("\n- Sessions detected for iDRAC %s\n" % idrac_ip)
    for i in sessions_list:
        print(i)
    for i in sessions_list:
        logging.info("\n- Detailed information for sessions URI \"%s\" -\n" % i)
        response = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        data = response.json()
        for i in data.items():
            pprint(i)

def create_x_auth_session():
    url = 'https://%s/%s' % (idrac_ip, session_uri)
    payload = {"UserName":idrac_username,"Password":idrac_password}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
    data = response.json()
    if response.status_code == 201:
        logging.info("\n- PASS, successfully created X auth session")
    else:
        try:
            logging.error("\n- FAIL, unable to create X-auth_token session, status code %s returned, detailed error results:\n %s" % (response.status_code, data))
        except:
            logging.error("\n- FAIL, unable to create X-auth_token session, status code %s returned" % (response.status_code))
        sys.exit(0)
    logging.info("\n- INFO, created session details -\n")
    for i in response.headers.items():
        print("%s: %s" % (i[0],i[1]))

def delete_x_auth_session():
    url = 'https://%s/%s/%s' % (idrac_ip, session_uri, args["delete"])
    try:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    except requests.ConnectionError as error_message:
        logging.error("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
        sys.exit(0)
    if response.status_code == 200:
        logging.info("\n- PASS, successfully deleted iDRAC session ID %s" % args["delete"])
    else:
        data = response.json()
        logging.info("\n- FAIL, unable to delete iDRAC session, status code %s returned, detailed error results:\n %s" % (response.status_code, data))
        sys.exit(0)

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
        if not args["p"] and args["u"]:
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
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    get_redfish_version()
    if args["create"]:
        create_x_auth_session()
    elif args["get_sessions"]:
        get_session_info_using_username_password()
    elif args["delete"]:
        delete_x_auth_session()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

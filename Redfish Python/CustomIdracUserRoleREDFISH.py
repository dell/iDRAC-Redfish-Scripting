#!/usr/bin/python3
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2024, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to either create, edit or delete custom iDRAC user role. ')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-custom-roles', help='Get current custom roles created', action="store_true", dest="get_custom_roles", required=False)
parser.add_argument('--create', help='Create custom iDRAC user role, pass in unique string name of the custom role. Note no whitespace is allowed and only dash and underscore special characters are allowed', required=False)
parser.add_argument('--privilege-types', help='Pass in privilege type(s) for create or edit custom user role, supported case sensitive values are: Login, ConfigureComponents, ConfigureManager, ConfigureSelf, ConfigureUsers, AccessVirtualConsole, AccessVirtualMedia, ClearLogs, ExecuteDebugCommands, TestAlerts. Note if passing in multiple values using a comma separator. Note if editing a custom user role make sure to also pass in existing privilege(s) if you do not want those settings to get removed', dest="privilege_types", required=False)
parser.add_argument('--edit', help='Edit current custom user role pass in custom role absolute URI path, example: /redfish/v1/AccountService/Roles/custom-role', required=False)
parser.add_argument('--delete', help='Delete custom role pass in custom role absolute URI path, example: /redfish/v1/AccountService/Roles/custom-role', required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- CustomIdracUserRoleREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-custom-roles, this example will get current custom user roles.
    \n- CustomIdracUserRoleREDFISH.py -ip 192.168.0.120 -u root -p calvin --create test2 --privilege-types "Login, AccessVirtualMedia", this example will create custom user role.
    \n- CustomIdracUserRoleREDFISH.py -ip 192.168.0.120 -u root -p calvin --edit /redfish/v1/AccountService/Roles/test3 --privilege-types ConfigureUsers, this example will edit test3 custom user role.
    \n- CustomIdracUserRoleREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/AccountService/Roles/test, this example will delete custom user role named test.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if "12" in data["Model"] or "13" in data["Model"] or "14" in data["Model"] or "15" in data["Model"] or "16" in data["Model"]:
        logging.warning("\n- WARNING, iDRAC version detectec does not support this feature")
        sys.exit(0)


def create_custom_role():
    dmtf_privileges = ["Login", "ConfigureComponents", "ConfigureManager", "ConfigureSelf", "ConfigureUsers"]
    oem_privileges = ["AccessVirtualConsole", "AccessVirtualMedia", "ClearLogs", "ExecuteDebugCommands", "TestAlerts"]
    url = "https://%s/redfish/v1/AccountService/Roles" % idrac_ip
    payload = {"RoleId":args["create"], "AssignedPrivileges":[], "OemPrivileges":[]}
    if "," in args["privilege_types"]:
        privilege_type_values = args["privilege_types"].split(",")
    else:
        privilege_type_values = [args["privilege_types"]]
    for i in privilege_type_values:
        if i in dmtf_privileges:
            payload["AssignedPrivileges"].append(i)
        if i in oem_privileges:
            payload["OemPrivileges"].append(i)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 201:
        logging.info("\n- PASS, POST command passed to create custom role, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed to create custom role, status code %s returned" % response.status_code)
        print(response.json())
        sys.exit(0)

def edit_custom_role():
    dmtf_privileges = ["Login", "ConfigureComponents", "ConfigureManager", "ConfigureSelf", "ConfigureUsers"]
    oem_privileges = ["AccessVirtualConsole", "AccessVirtualMedia", "ClearLogs", "ExecuteDebugCommands", "TestAlerts"]
    url = "https://%s%s" % (idrac_ip, args["edit"])
    payload = {"AssignedPrivileges":[], "OemPrivileges":[]}
    if "," in args["privilege_types"]:
        privilege_type_values = args["privilege_types"].split(",")
    else:
        privilege_type_values = [args["privilege_types"]]
    for i in privilege_type_values:
        if i in dmtf_privileges:
            payload["AssignedPrivileges"].append(i)
        if i in oem_privileges:
            payload["OemPrivileges"].append(i)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS, PATCH command passed to edit custom role, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to edit custom role, status code %s returned" % response.status_code)
        print(response.json())
        sys.exit(0)   
    
def delete_custom_role():
    url = "https://%s%s" % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS: DELETE command passed to delete custom role, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, DELETE command failed to delete custom role, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- DELETE command failure:\n %s" % data)
        sys.exit(0)

def get_current_custom_roles():
    uri = "redfish/v1/AccountService/Roles"
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
        sys.exit(0)
    custom_role_uris = []
    for i in data["Members"]:
        for ii in i.items():
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
                sys.exit(0)
            if data["Description"] == "Custom User Role":
                custom_role_uris.append(ii[1])
    if custom_role_uris == []:
        logging.warning("\n- WARNING, no custom roles detected")
    else:
        logging.info("\n- INFO custom iDRAC user role(s) detected\n")
        for i in custom_role_uris:
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
                sys.exit(0)
            pprint(data)
            print("\n")
                
            

        
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
    if args["get_custom_roles"]:
        get_current_custom_roles()
    elif args["delete"]:
        delete_custom_role()
    elif args["create"] and args["privilege_types"]:
        create_custom_role()
    elif args["edit"] and args["privilege_types"]:
        edit_custom_role()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

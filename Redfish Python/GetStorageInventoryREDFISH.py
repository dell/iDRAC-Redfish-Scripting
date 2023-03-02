#!/usr/bin/python3
#
# GetStorageInventoryREDFISH. Python script using Redfish API DMTF to get storage inventory: controllers, disks and backplanes.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
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
import os
import platform
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API DMTF to get server storage inventory (disks, controllers and backplanes)')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-controllers', help='Get server storage controller information.', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-disks', help='Get server storage disks information', action="store_true", dest="get_disks", required=False)
parser.add_argument('--get-virtualdisks', help='Get server storage virtual disk information', action="store_true", dest="get_virtualdisks", required=False)
parser.add_argument('--get-backplanes', help='Get server storage backplane information', action="store_true", dest="get_backplanes", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-controllers, this example will get details for all controllers detected.
    \n- GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-disks, this example will get details for all disks detected for all controllers.
    \n- GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-virtualdisks, this example will get details for all virtualdisks detected for all controllers.
    \n- GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-backplanes, this example will get details for all backplanes(enclosures) detected.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    
def get_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed, detailed error information: %s" % data)
        sys.exit(0)
    logging.info("\n- Storage controller information for iDRAC %s -\n" % idrac_ip)
    for i in data.items():
        pprint(i)
        print("\n")
    
def get_disks():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    controller_list = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
    for i in controller_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s?$select=Drives' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s?$select=Drives' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if data["Drives"] == []:
            logging.warning("\n- WARNING, no drives detected for controller %s\n" % i)
        else:
            logging.info("\n- INFO, drives detected for controller %s -\n" % i)
            for i in data["Drives"]:
                for ii in i.items():
                    if args["x"]:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
                pprint(response.json())

def get_backplanes():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis?$select=Members' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Chassis?$select=Members' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data["Members"]:
        for ii in i.items():
            if "enclosure" in ii[1].lower():
                logging.info("\n- INFO, detailed information for %s -\n" % ii[1].split("/")[-1])
                if args["x"]:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
                pprint(response.json())

def get_virtualdisks():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    controller_list = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
    for i in controller_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, i),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, i),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        vd_list = []
        if data['Members'] == []:
            logging.error("\n- WARNING, no volume(s) detected for controller %s\n" % i)
        else:
            logging.info("\n- Volume(s) detected for %s controller -\n" % i)
            for i in data['Members']:
                vd_list.append(i['@odata.id'].split("/")[-1])
        for ii in vd_list:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            for i in data.items():
                pprint(i)
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
    if args["get_controllers"]:
        get_controllers()
    elif args["get_disks"]:
        get_disks()
    elif args["get_backplanes"]:
        get_backplanes()
    elif args["get_virtualdisks"]:
        get_virtualdisks()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

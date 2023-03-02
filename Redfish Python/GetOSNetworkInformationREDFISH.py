#!/usr/bin/python3
#
# GetOSNetworkInformationREDFISH. Python script using Redfish API to get host operating system (OS) network information.
#
# NOTE: iSM (iDRAC Service Module) must be installed and running in the OS for Redfish to be able to get this data. iSM is available on Dell support site under Drivers / Downloads, System Management section for your server model.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
#
# Copyright (c) 2018, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to get operating system network information. iDRAC Service Module (iSM) must be installed in the OS and services is running for iDRAC to get this data.')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-ism-status', help='Get iSM service status, confirm iSM is running in the OS', dest="get_ism_status", action="store_true", required=False)
parser.add_argument('--get-network-details', help='Get OS network details for each network device configured in the OS.', dest="get_network_details", action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetOSNetworkInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-ism-status, this example will return current iDRAC iSM service status.
    \n- GetOSNetworkInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-network-details, this example will return detailed information for all OS network devices configured.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_iSM_status():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes?$select=Attributes/ServiceModule.1.ServiceModuleState' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes?$select=Attributes/ServiceModule.1.ServiceModuleState' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to get iDRAC iSM service status, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    logging.info("\n- INFO, current iDRAC iSM service status: %s" % data["Attributes"]["ServiceModule.1.ServiceModuleState"])
        
def get_OS_network_devices():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to get OS network device interfaces, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    supported_os_uris = []
    for i in data["Members"]:
        for ii in i.items():
            if "OS" in ii[1]:
                supported_os_uris.append(ii[1])
    if supported_os_uris == []:
        logging.warning("\n- WARNING, no OS network uris detected. Check to make sure iSM is running and network devices are configured in the OS.")
        sys.exit(0)
    for i in supported_os_uris:
        logging.info("\n- Detailed information for %s -\n" % i)
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        pprint(response.json())
                   
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
    if args["get_ism_status"]:
        get_iSM_status()
    elif args["get_network_details"]:
        get_OS_network_devices()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

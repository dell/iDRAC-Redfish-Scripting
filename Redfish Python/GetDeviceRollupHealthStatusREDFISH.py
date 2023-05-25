#!/usr/bin/python3
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get health rollup status for server devices. If you see status other than Ok for a device, recommended to get event log information about the error.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--rollup-status-device', help='Pass in device(s) to get current health rollup status. Supported values: voltage, intrusion, processor, memory, fan, powersupply, temperature, battery, storage or all. If passing in multiple values use a comma separator.', dest="rollup_status_device", required=False)
parser.add_argument('--get-fault-details', help='get fault details for a device reporting non healthy rollup status.', action="store_true", dest="get_fault_details", required=False)
parser.add_argument('--memory-health', help='Get health status per dimm installed', action="store_true", dest="memory_health", required=False)
parser.add_argument('--processor-health', help='Get health status per processor installed', action="store_true", dest="processor_health", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO) 


def script_examples():
    print("""\n- GetDeviceRollupHealthStatusREDFISH.py -ip 192.168.0.120 -u root -p calvin --rollup-status-device powersupply, this example will return health rollupstatus for power supplies only.
    \n- GetDeviceRollupHealthStatusREDFISH.py -ip 192.168.0.120 -u root -p calvin --rollup-status-device all, this example will return health rollup status for all supported devices.
    \n- GetDeviceRollupHealthStatusREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-fault-details, this example will return any server fault details detected.
    \n- GetDeviceRollupHealthStatusREDFISH.py -ip 192.168.0.120 -u root -p calvin --memory-health, this example will return memory health status for each dimm detected.
    \n- GetDeviceRollupHealthStatusREDFISH.py -ip 192.168.0.120 -u root -p calvin --processor-health, this example will return processor health status for each cpu installed.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRollupStatus' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRollupStatus' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_device_rollup_health_status():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRollupStatus' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRollupStatus' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed to get rollup status, status code %s returned, error: \n\n%s" % (response.status_code, data))
        sys.exit(0)
    supported_device_detected = []
    if args["rollup_status_device"].lower() == "all":
        print("\n")
        for i in data["Members"]:
            pprint(i)
            print("\n")
        sys.exit(0)
    for i in data["Members"]:
        if i["SubSystem"].lower() in args["rollup_status_device"]:
            supported_device_detected.append(i)
    if supported_device_detected == [] and args["rollup_status_device"].lower() != "all":
        logging.warning("\n- WARNING, no supported device(s) detected for argument value %s" % args["rollup_status_device"])
    else:
        logging.info("\n- INFO, rollup health status information for devices(s): %s\n" % args["rollup_status_device"])
        for i in supported_device_detected:
            pprint(i)
            print("\n")

def get_device_fault_details():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/FaultList/Entries' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/FaultList/Entries' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed to get fault list details, status code %s returned, error: \n\n%s" % (response.status_code, data))
        sys.exit(0)
    if data["Members"] == []:
        logging.warning("\n- WARNING, no fault events detected")
    else:
        print("\n")
        for i in data["Members"]:
            pprint(i)
            print("\n")    

def get_memory_processor_health_information(device_name):
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/%s' % (idrac_ip, device_name), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/%s' % (idrac_ip, device_name), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    for i in data["Members"]:
        for ii in i.items():
            if args["x"]:
                response = requests.get('https://%s%s?$select=Status/Health' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s?$select=Status/Health' % (idrac_ip, ii[1]), verify=verify_cert, auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logging.error("\n- FAIL, get command failed, error: %s" % data)
                sys.exit(0)
            data = response.json()
            logging.info("\n- %s: Health: %s" % (ii[1].split("/")[-1], data["Status"]["Health"]))

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
    if args["rollup_status_device"]:
        get_device_rollup_health_status()
    if args["get_fault_details"]:
        get_device_fault_details()
    if args["memory_health"]:
        get_memory_processor_health_information("Memory")
    if args["processor_health"]:
        get_memory_processor_health_information("Processors")

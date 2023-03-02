#!/usr/bin/python3
#
# BiosDeviceRecoveryREDFISH. Python script using Redfish API with OEM extension to recover the BIOS
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to recover the server BIOS. This script should be executed when the server BIOS gets corrupted causing POST to not complete.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- BiosDeviceRecoveryREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will recover the server BIOS. NOTE: During this process, server will power OFF, power ON, recover the BIOS firmware, reboot and process will be complete.""")
    sys.exit(0)
    
def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "DeviceRecovery" in i:
            supported = "yes"
    if supported == "no":
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def bios_device_recovery():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService/Actions/DellBIOSService.DeviceRecovery' % (idrac_ip)
    method = "DeviceRecovery"
    payload = {"Device":"BIOS"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    
def get_idrac_time():
    global current_idrac_time
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    payload={"GetRequest":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    for i in data.items():
        if i[0] !="@Message.ExtendedInfo":
            current_idrac_time = i[1]
    strip_timezone=current_idrac_time.find("-")
    strip_timezone=current_idrac_time.find("-", strip_timezone+1)
    strip_timezone=current_idrac_time.find("-", strip_timezone+1)
    current_idrac_time = current_idrac_time[:strip_timezone]
    time.sleep(10)

def validate_process_started():
    global start_time
    global t1
    start_time = datetime.now()
    count = 0
    while True:
        if count == 10:
            logging.error("- FAIL, unable to validate the recovery operation has initiated. Check server status, iDRAC Lifecycle logs for more details")
            sys.exit(0)
        else:
            try:
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            except requests.ConnectionError as error_message:
                logging.error("- FAIL, GET requests failed to check LC logs for validating recovery process started, detailed error information: \n%s" % error_message)
                sys.exit(0)
            data = response.json()
            for i in data['Members']:
                for ii in i.items():
                    if ii[1] == "UEFI0298":
                        message_id_timestamp = i['Created']
                        strip_timezone = message_id_timestamp.find("-")
                        strip_timezone = message_id_timestamp.find("-", strip_timezone+1)
                        strip_timezone = message_id_timestamp.find("-", strip_timezone+1)
                        message_id_timestamp_start = message_id_timestamp[:strip_timezone]
                        t1 = datetime.strptime(current_idrac_time, "%Y-%m-%dT%H:%M:%S")
                        t2 = datetime.strptime(message_id_timestamp_start, "%Y-%m-%dT%H:%M:%S")
                        if t2 > t1:
                            logging.info("\n- PASS, recovery operation initiated successfully. The system will automatically turn OFF, turn ON to recovery the BIOS. Do not reboot server or remove power during this time.")
                            time.sleep(10)
                            return
            count += 1
            time.sleep(10)
    
def validate_process_completed():
    count = 0
    while True:
        if count == 100:
            print("- FAIL, unable to validate the recovery operation has completed. Check server status, iDRAC Lifecycle logs for more details")
            sys.exit()
        else:
            try:
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            except requests.ConnectionError as error_message:
                if "Max retries exceeded with url" in str(error_message):
                    logging.warning("- WARNING, max retries exceeded with URL error, retry GET command")
                    time.sleep(10)
                    continue
                else:
                    logging.error("- FAIL, GET command failed to query LC Logs, validate recovery process completed. Detail error results: %s" % error_message)
                    sys.exit(0)   
            data = response.json()
            for i in data['Members']:
                for ii in i.items():
                    if ii[1] == "UEFI0299":
                        message_id_timestamp = i['Created']
                        strip_timezone=message_id_timestamp.find("-")
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        message_id_timestamp_start = message_id_timestamp[:strip_timezone]
                        t2 = datetime.strptime(message_id_timestamp_start, "%Y-%m-%dT%H:%M:%S")
                        if t2 > t1:
                            logging.info("\n- PASS, recovery operation completed successfully")
                            sys.exit(0)
            logging.info("- INFO, recovery operation is still executing, current execution process time: %s" % str(datetime.now()-start_time)[0:7]) 
            count += 1
            time.sleep(30)
    
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
    get_idrac_time()
    bios_device_recovery()
    validate_process_started()
    validate_process_completed()

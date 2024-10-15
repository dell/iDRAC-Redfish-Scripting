#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
# Example of change_boot_order.txt file contents:
#
# {"@odata.context": "/redfish/v1/$metadata#DellBootSources.DellBootSources", "@odata.id": "/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources",
# "@odata.type": "#DellBootSources.v1_1_0.DellBootSources", "Attributes": {"UefiBootSeq": [{"Enabled": true, "Id": "BIOS.Setup.1-1#UefiBootSeq#NIC.PxeDevice.1-1#709c0888d3f7fb4aa12e13c31f22ef1b", "Index": 1,
# "Name": "NIC.PxeDevice.1-1"}, {"Enabled": true, "Id": "BIOS.Setup.1-1#UefiBootSeq#AHCI.SL.6-2#5cf8b4f3d15f5690499ec8b96a91f7ac", "Index": 0, "Name": "AHCI.SL.6-2"}]}}
#
# Make sure to only modify the file contents, do not delete/change the JSON format.
#
# To change the boot order change the index number for the devices listed. In the example above if I want to make NIC.PxeDevice.1-1 first device in the boot order I would set
# Index to 0 and AHCI.SL.6-2 Index to 1.
#
# To disable a boot order device change Enabled property to false.
#
# Note you can enable/disable boot order devices and change the boot order at the same time if needed. 

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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to ether get current BIOS boot order, change boot order or enable/disable boot order devices.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value true or false. By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current boot order', action="store_true", required=False)
parser.add_argument('--create', help='Create config file that will be used to make BIOS boot order changes. See script comments for file example contents along with information about how to edit the file correctly', action="store_true", required=False)
parser.add_argument('--change', help='Change boot order or boot order device state, pass in filename value "change_boot_order.txt". If file is in another directory pass in the directory path also.', required=False)
parser.add_argument('--reboot', help='Pass in this argument to reboot the server now to change BIOS boot order. If argument is not passed in BIOS config job will still get scheduled and run on next server reboot.', action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ChangeBiosBootOrderSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current BIOS boot order and enable/disable state.
    \n- ChangeBiosBootOrderSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --create, this example will create the config file which is needed to modify the boot order.
    \n- ChangeBiosBootOrderSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --change change_boot_order.txt --reboot, this example will create BIOS config job and reboot the server now to apply boot order changes.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(1)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(1)

def get_current_boot_order():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to get BIOS details, status code %s returned" % response.status_code)
        sys.exit(1)
    else:
        data = response.json()
        try:
            current_boot_mode = data['Attributes']['BootMode']
        except:
            logging.error("- FAIL, unable to locate BootMode attribute in JSON output")
            sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources?$select=Attributes' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources?$select=Attributes' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to Get BIOS boot source details, status code %s returned" % response.status_code)
        sys.exit(1)
    data = response.json()
    logging.info("\n- INFO, current boot order/device state for %s boot order devices -\n" % current_boot_mode)
    pprint(data)

def create_config_file():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources?$select=Attributes' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources?$select=Attributes' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("- FAIL, GET command failed to get BIOS boot source details, status code %s returned" % response.status_code)
        sys.exit(1)
    data = response.json()
    with open("change_boot_order.txt", "w") as create_file:
        json.dump(data, create_file)
    logging.info("\n- Config file \"change_boot_order.txt\" created. This file can be used to either change the boot order or enable/disable boot order devices")
                
def change_boot_source_state():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources/Settings' % idrac_ip
    try:
        with open(args["change"], "r") as file:
            json_data = file.read()
            payload = json.loads(json_data)
    except:
        logging.warning("\n- WARNING, unable to locate file \"%s\"" % args["change"])
        sys.exit(1)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to change boot order settings")
    else:
        logging.error("\n- FAIL, PATCH command failed to change boot order settings, status code %s returned" % response.status_code)
        detail_message = str(response.__dict__)
        logging.error(detail_message)
        sys.exit(1)

def create_bios_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs' % idrac_ip
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.debug("- PASS, POST command passed to create BIOS config job")
    else:
        logging.error("\n- FAIL, POST command failed to create BIOS config job, status code %s returned\n" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers PATCH response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("- PASS, job ID \"%s\" successfully created" % job_id)
    
def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(5)
            count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- PASS, BIOS config job successfully marked as scheduled")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            if "powercyclerequest" in args["attribute_names"].lower():
                logging.info("- INFO, PowerCycleRequest attribute detected, virtual a/c cycle is running. Script will sleep for 180 seconds, retry")
                time.sleep(180)
            else:
                time.sleep(60)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'])
            time.sleep(10)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to gracefully power OFF server")
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(60)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        while True:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                if args["x"]:
                    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("- PASS, POST command passed to perform forced shutdown")
                    time.sleep(60)
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        logging.info("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        logging.error("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit(0)
            else:
                continue
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to power ON server")
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, Command passed to power ON server, code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
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
    if args["get"]:
        get_current_boot_order()
    elif args["create"]:
        create_config_file()
    elif args["change"]:
        change_boot_source_state()
        create_bios_config_job()
        get_job_status_scheduled()
        if not args["reboot"]:
            logging.info("- INFO, --reboot argument not detected, BIOS config job is still scheduled and will run on next server manual reboot")
        else:
            logging.info("- INFO, rebooting server to run BIOS config job for changing BIOS boot order settings")
            reboot_server()
            loop_job_status_final()
            get_current_boot_order()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

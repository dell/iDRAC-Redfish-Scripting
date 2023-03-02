#!/usr/bin/python3
#
# DeviceFirmwareRollbackREDFISH. Python script using Redfish API with OEM extension to rollback firmware for a device iDRAC supports. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 6.0
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
import os
import platform
import re
import requests
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to rollback firmware for a device iDRAC supports")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-firmware', help='Get current supported devices for firmware updates and their current firmware versions', action="store_true", dest="get_firmware", required=False)
parser.add_argument('--get-rollback', help='Get current PREVIOUS URI entries for rollback support', action="store_true", dest="get_rollback", required=False)
parser.add_argument('--rollback', help='Pass in the PREVIOUS URI entry you want to rollback the firmware', required=False)
parser.add_argument('--reboot', help='Pass in this argument to reboot the server now to perform the update. If you do not pass in this argument, update job is still scheduled and will get applied on next server manual reboot. Note: For devices that do not need a reboot to apply the firmware update (Examples: iDRAC, DIAGS, Driver Pack), you don\'t need to pass in this agrument(update will happen immediately). See Lifecycle Controller User Guide firmware update section for more details on which devices get applied immediately or need a reboot to get updated', action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DeviceFirmwareRollbackREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-rollback, this example will return devices which support rollback.
    \n- DeviceFirmwareRollbackREDFISH.py -ip 192.168.0.120 -u root -p calvin --rollback /redfish/v1/UpdateService/FirmwareInventory/Previous-159-2.7.7 --reboot, this example will reboot server now to rollback BIOS to version 2.7.7.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to validate supported iDRAC version, status code %s returned, error: \n%s" % (response.status_code, data))
        sys.exit(0)  

def get_rollback_entries():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    previous_devices = []
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get rollback entries, error: \n%s" % data)
        sys.exit(0)
    for i in data["Members"]:
        for ii in i.items():
            if "Previous" in ii[1]:
                previous_devices.append(ii[1])
    if previous_devices == []:
        logging.warning("- WARNING, no PREVIOUS firmware images detected for rollback support")
        sys.exit(0)
    logging.info("\n- Device URI(s) detected for rollback support -\n")
    for i in previous_devices:
        print(i)

def get_FW_inventory():
    logging.info("\n- INFO, getting current firmware inventory for iDRAC %s -\n" % idrac_ip)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get firmware inventory, error: \n%s" % data)
        sys.exit(0)
    installed_devices = []
    for i in data['Members']:
        pprint(i)
        print("\n")

def rollback_fw():
    global job_id
    global start_time
    start_time = datetime.now()
    url = 'https://%s/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate' % (idrac_ip)
    payload = {"ImageURI":args["rollback"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        data = response.json()
        logging.info("\n- FAIL, POST command failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    try:
        job_id = response.headers["Location"].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in headers output")
        sys.exit(0)
    logging.info("\n- PASS, rollback job ID \"%s\" successfully created" % job_id)
    if "idrac" in args["rollback"].lower():
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        logging.info("\n- Final detailed job results -\n")
        for i in data['Oem']['Dell'].items():
            pprint(i)
        sys.exit(0)

def check_job_status():
    retry_count = 1
    while True:
        check_idrac_connection()
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(10)
            retry_count += 1
            continue
        data = response.json()
        current_time = str(datetime.now()-start_time)[0:7]   
        message_string = data["Messages"]
        if response.status_code == 200 or response.status_code == 202:
            time.sleep(1)
        else:
            logging.error("\n- ERROR, GET request failed to get job ID details, status code %s returned, error: \n%s" % (response.status_code, data))
            sys.exit(0)
        if data["TaskState"] == "Completed" and data["Oem"]["Dell"]["JobState"]:
            logging.info("\n- INFO, job completed, detailed final job status results\n")
            for i in data['Oem']['Dell'].items():
                pprint(i)
            logging.info("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit(0)
        if data["TaskState"] == "Completed":
            logging.info("\n- PASS, job ID successfuly marked completed, detailed final job status results\n")
            for i in data['Oem']['Dell'].items():
                pprint(i)
            logging.info("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit(0)
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit(0)
        elif "failed" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Failed" in data['Oem']['Dell']['Message']:
            logging.error("- FAIL: Job failed, current message: %s" % data["Messages"])
            sys.exit(0)
        elif "scheduled" in data['Oem']['Dell']['Message']:
            print("- PASS, job ID %s successfully marked as scheduled" % data["Id"])
            if not args["reboot"]:
                logging.warning("- WARNING, missing argument --reboot for rebooting the server. Job is still scheduled and will be applied on next manual server reboot")
                sys.exit(0)
            elif args["reboot"]:
                break
        elif "completed successfully" in data['Oem']['Dell']['Message']:
            logging.info("\n- PASS, job ID %s successfully marked completed, detailed final job status results\n")
            for i in data['Oem']['Dell'].items():
                pprint(i)
            logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            break
        else:
            logging.info("- INFO: %s, execution time: %s" % (message_string[0]["Message"].rstrip("."), current_time))
            time.sleep(1)
            continue

def loop_check_final_job_status():
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        check_idrac_connection()
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(10)
            retry_count += 1
            continue 
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            logging.error("- FAIL: job ID %s failed" % job_id)
            sys.exit(0)
        elif "completed successfully" in data['Message']:
            logging.info("\n- PASS, job ID %s successfully marked completed" % job_id)
            logging.info("\n- Final detailed job results -\n")
            for i in data.items():
                pprint(i)
            logging.info("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit(0)
        else:
            logging.info("- INFO, JobStatus not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'].rstrip("."), current_time))
            time.sleep(1)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- INFO, Current server power state is: %s" % data['PowerState'])
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
            time.sleep(15)
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
            elif current_time >= "0:05:00":
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
                    time.sleep(15)
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

def check_idrac_connection():
    run_network_connection_function = ""
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        logging.error("- FAIL, unable to determine OS type, check iDRAC connection function will not execute")
        run_network_connection_function = "fail"
    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
    if execute_command != 0:
        ping_status = "lost"
    else:
        ping_status = "good"
        pass
    if ping_status == "lost":
            logging.info("- INFO, iDRAC network connection lost due to slow network response, waiting 30 seconds to access iDRAC again")
            time.sleep(30)
            while True:
                if run_network_connection_function == "fail":
                    break
                execute_command=subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
                if execute_command != 0:
                    ping_status = "lost"
                else:
                    ping_status = "good"
                if ping_status == "lost":
                    logging.info("- INFO, unable to ping iDRAC IP, script will wait 30 seconds and try again")
                    time.sleep(30)
                    continue
                else:
                    break
            while True:
                try:
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                    else:
                        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
                except requests.ConnectionError as error_message:
                    logging.info("- INFO, GET request failed due to connection error, retry")
                    time.sleep(10)
                    continue
                break

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
    if args["get_firmware"]:
        get_FW_inventory()
    elif args["get_rollback"]:
        get_rollback_entries()
    elif args["rollback"]:
        rollback_fw()
        check_job_status()
        if args["reboot"]:
            logging.info("- INFO, powering on or rebooting server to apply the firmware")
            reboot_server()
            loop_check_final_job_status()
        else:
            logging.info("- INFO, argument --reboot not detected. Update job is marked as scheduled and will be applied on next server reboot")
            sys.exit(0)
    else:
        logging.info("- INFO, argument --reboot not detected. Update job is marked as scheduled and will be applied on next server reboot")

#!/usr/bin/python3
#
# _author_ = Texas Roemer <administrator@Dell.com>
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
import glob
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to update multiple devices using a local directory which contains all Dell Update packages only. Script will first update all devices except for iDRAC that do not require a reboot (examples: DIAGs or DriverPack). Next will download and create update jobs for all devices that need a reboot to apply (examples: BIOS, RAID, NIC). Once all jobs created, server will reboot to execute all of them. Last script will run iDRAC update if detected. iDRAC update will run last since the iDRAC reboots after the update is complete.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get', help='Get current supported devices for firmware updates and their current firmware versions', action="store_true", required=False)
parser.add_argument('--location', help='Pass in the full directory path location of the directory which contains all Dell update packages (DUP). Note: only Windows DUPs are supported by iDRAC interfaces to perform updates. Note: make sure only DUPs are in this directory and no other files, directories. Note: If planning to update iDRAC, make sure the DUP name package contains the word idrac (default DUP name does contain wording iDRAC, recommended not to change it)', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- FirmwareUpdateLocalRepoREDFISH.py -ip 192.168.0.120 -u root -p calvin --location C:\\Users\\administrator\\Downloads\\R740xd_repo, this example will apply updates for all DUP packages detected in this directory path.""")
    sys.exit(0)

# Example of local directory contents containing Dell DUPs:
#>>> glob.glob("C://Users//administrator//Downloads//R740xd_repo/*")
#['C://Users//administrator//Downloads//R740xd_repo\\BIOS_W77H1_WN64_2.16.1.EXE',
#'C://Users//administrator//Downloads//R740xd_repo\\Diagnostics_Application_R30YT_WN64_4301A73_4301.74_01.EXE',
#'C://Users//administrator//Downloads//R740xd_repo\\Firmware_60K1J_WN32_2.52_A00.EXE',
#'C://Users//administrator//Downloads//R740xd_repo\\iDRAC-with-Lifecycle-Controller_Firmware_KMYV9_WN64_6.10.00.00_A00.EXE',
#'C://Users//administrator//Downloads//R740xd_repo\\Network_Firmware_T3KH2_WN64_15.05.12_A00-00_02.EXE',
#'C://Users//administrator//Downloads//R740xd_repo\\SAS-RAID_Firmware_NYKX7_WN32_25.5.9.0001_A15.EXE']

    
def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if 'MultipartHttpPushUri' not in data.keys():
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)   
    
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

def download_image_create_update_job(firmware_image_device):
    global job_id
    global idrac_dup_package
    global idrac_update_flag
    if "idrac" in firmware_image_device.lower():
        logging.info("- INFO, iDRAC firmware package detected, this update will get applied at the end due to iDRAC reboot")
        idrac_update_flag = True
        idrac_dup_package = firmware_image_device
    else:
        logging.info("- INFO, uploading update package \"%s\" to create update job, this may take a few minutes depending on firmware image size" % firmware_image_device.split("\\")[-1])                                                                                                                                                                           
        url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
        payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
        files = {
             'UpdateParameters': (None, json.dumps(payload), 'application/json'),
             'UpdateFile': (os.path.basename(firmware_image_device), open(firmware_image_device, 'rb'), 'application/octet-stream')
        }
        if args["x"]:
            headers = {'X-Auth-Token': args["x"]}
            response = requests.post(url, files=files, headers=headers, verify=verify_cert)
        else:
            response = requests.post(url, files=files, verify=verify_cert,auth=(idrac_username,idrac_password))
        
        if response.status_code != 202:
            data = response.json()
            logging.error("- FAIL, status code %s returned, detailed error: %s" % (response.status_code,data))
            sys.exit(0)
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in header")
            sys.exit(0)
        logging.info("- PASS, update job ID %s successfully created for firmware package \"%s\"" % (job_id, firmware_image_device.split("\\")[-1]))
            
def idrac_update(firmware_image_device):
    global idrac_update_job_id
    logging.info("- INFO, downloading update package \"%s\" to create update job, this may take a few minutes depending on firmware image size" % firmware_image_device.split("\\")[-1])
                                                                                                                                                                              
    url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
    payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
    files = {
         'UpdateParameters': (None, json.dumps(payload), 'application/json'),
         'UpdateFile': (os.path.basename(firmware_image_device), open(firmware_image_device, 'rb'), 'application/octet-stream')
    }
    if args["x"]:
        headers = {'X-Auth-Token': args["x"]}
        response = requests.post(url, files=files, headers=headers, verify=verify_cert)
    else:
        response = requests.post(url, files=files, verify=verify_cert,auth=(idrac_username,idrac_password))
    
    if response.status_code != 202:
        data = response.json()
        logging.error("- FAIL, status code %s returned, detailed error: %s" % (response.status_code,data))
        sys.exit(0)
    try:
        idrac_update_job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in header")
        sys.exit(0)
    logging.info("- PASS, update job ID %s successfully created for firmware package \"%s\"" % (idrac_update_job_id, firmware_image_device.split("\\")[-1]))

def check_job_status(download_job_id):
    retry_count = 1
    start_time = datetime.now()
    while True:
        check_idrac_connection()
        if retry_count == 10:
            logging.warning("- WARNING, GET command retry count of 10 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, download_job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, download_job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
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
        if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "fail" in data['Oem']['Dell']['JobState'].lower():
            logging.error("- FAIL: Job ID %s failed, current message: %s" % (download_job_id, data['Oem']['Dell']['Message']))
            sys.exit(0)
        elif data["TaskState"] == "Completed" and data["Oem"]["Dell"]["JobState"] or data["TaskState"] == "Completed" or "completed successfully" in data['Oem']['Dell']['Message'].lower():
            logging.info("- PASS, job ID %s successfully marked completed" % download_job_id)
            time.sleep(15)
            break
        elif str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit(0)
        elif "schedule" in data['Oem']['Dell']['Message'].lower():
            print("- PASS, job ID %s successfully marked as scheduled, server reboot needed to apply the update" % data["Id"])
            update_jobs_need_server_reboot.append(download_job_id)
            break
        else:
            logging.info("- INFO: %s job status: %s" % (download_job_id, message_string[0]["Message"].rstrip(".")))
            time.sleep(2)
            continue

def loop_check_final_job_status(reboot_update_job_id):
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        check_idrac_connection()
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, reboot_update_job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, reboot_update_job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
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
        if str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "fail" in data['Message'].lower() or "fail" in data['JobState'].lower():
            logging.error("- FAIL: job ID %s failed, error results: \n%s" % (job_id, data['Message']))
            sys.exit(0)
        elif "completed successfully" in data['Message']:
            logging.info("- PASS, job ID %s successfully marked completed" % reboot_update_job_id)
            break
        else:
            logging.info("- INFO, %s job status not completed, current status: \"%s\"" % (reboot_update_job_id, data['Message'].rstrip(".")))
            time.sleep(60)

def reboot_server():
    logging.info("- INFO, rebooting the server now to apply firmware update(s)")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, Current server power state: %s" % data['PowerState'])
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
            time.sleep(15)
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
    if args["get"]:
        get_FW_inventory()
    elif args["location"]:
        update_jobs_need_server_reboot = []
        idrac_update_flag = False
        directory_dups = (glob.glob("%s\*" % args["location"]))
        for i in directory_dups:
            download_image_create_update_job(i)
            check_job_status(job_id)
        if update_jobs_need_server_reboot == []:
            logging.info("- INFO, no scheduled update jobs detected, server will not reboot")
        else:
            reboot_server()
            for i in update_jobs_need_server_reboot:
                loop_check_final_job_status(i)
        if idrac_update_flag == True:
            logging.info("- INFO, iDRAC update detected, update will now get applied and once completed iDRAC will reboot")
            idrac_update(idrac_dup_package)
            check_job_status(idrac_update_job_id)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

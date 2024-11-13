#!/usr/bin/python3
#
# _author_ = Texas Roemer <administrator@Dell.com>
# _version_ = 8.0
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
from pathlib import Path
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
parser.add_argument('--block-same-version', help='Pass in this argument to block same version update. If the update package matches version device firmwae version, update will not occur. Note: This argument is only supported for iDRAC9, iDRAC10 is not supported.', action="store_true", dest="block_same_version", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- FirmwareUpdateLocalRepoREDFISH.py -ip 192.168.0.120 -u root -p calvin --location C:\\Users\\administrator\\Downloads\\R740xd_repo, this example will apply updates for all DUP packages detected in this directory path.""")
    sys.exit(0)

# Example of local directory contents containing Dell DUPs:
#
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
    global cpld_dup_package
    global cpld_update_flag
    global job_id_created
    if "idrac" in firmware_image_device.lower():
        logging.info("- INFO, iDRAC firmware package detected, this update will get applied at the end due to iDRAC reboot")
        idrac_update_flag = True
        idrac_dup_package = firmware_image_device
        job_id_created = "no"
    elif "cpld" in firmware_image_device.lower():
        logging.info("- INFO, CPLD firmware package detected, this update will get applied at the end due to iDRAC reboot and update must not be stacked with other devices.")
        cpld_update_flag = True
        cpld_dup_package = firmware_image_device
        job_id_created = "no"
    else:
        logging.info("\n- INFO, uploading update package \"%s\" to create update job, this may take a few minutes depending on firmware image size" % firmware_image_device.split("\\")[-1])                                                                                                                                                                           
        url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
        payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
        files = {
             'UpdateParameters': (None, json.dumps(payload), 'application/json'),
             'UpdateFile': (os.path.basename(firmware_image_device), open(firmware_image_device, 'rb'), 'application/octet-stream')
        }
        check_valid_dup = firmware_image_device.split("\\")[-1]
        if not check_valid_dup.lower().endswith("exe"):
            logging.warning("- WARNING, invalid file detected '%s', update will not run" % check_valid_dup)
            job_id_created = "no"
            return
        if args["x"]:
            headers = {'X-Auth-Token': args["x"]}
            response = requests.post(url, files=files, headers=headers, verify=verify_cert)
        else:
            response = requests.post(url, files=files, verify=verify_cert,auth=(idrac_username,idrac_password))
        
        if response.status_code != 202:
            data = response.json()
            logging.error("- FAIL, status code %s returned, detailed error: %s" % (response.status_code,data))
            if response.status_code == 400:
                job_id_created = "no"
                return
            else:    
                sys.exit(0)
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in header")
            sys.exit(0)
        logging.info("- PASS, update job ID %s successfully created for firmware package \"%s\"" % (job_id, firmware_image_device.split("\\")[-1]))
        job_id_created = "yes"

def check_same_version(dup_name):
    if not dup_name.lower().endswith("exe"):
        remove_dup_list.append(dup_name)
        return
    logging.info("\n- INFO, checking update package \"%s\" image version against current device version installed" % dup_name)

    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get firmware inventory details")
        sys.exit(0)
    available_entries = []
    for i in data['Members']:
        for ii in i.items():
            if "/available" in ii[1].lower():
                available_entries.append(ii[1])
    if available_entries == []:
        logging.debug("\n- WARNING, no AVAILABLE entries for deleting payload")
    else:
        for i in available_entries:
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logging.error("- FAIL, GET command failed, error is %s" % data)
                sys.exit(0)
            ETag = response.headers['ETag']
            url = 'https://%s%s' % (idrac_ip, i)
            if args["x"]:
                headers = {'X-Auth-Token': args["x"], "if-match": ETag}
                response = requests.delete(url, headers=headers, verify=verify_cert)
            else:
                headers = {"if-match": ETag}
                response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
            data = response.json()
            if response.status_code == 200:
                logging.debug("\n- PASS, Successfully deleted payload for URI %s" % i)
            else:
                logging.error("\n- FAIL, command failed to delete AVAILABLE URI %s, error: \n%s" % (i, data))
                sys.exit(0)
            
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    try:
        http_push_uri = data['HttpPushUri']
    except:
        logging.error("- FAIL, iDRAC version detected does not support the code to perform same validation check")
        sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, http_push_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s%s' % (idrac_ip, http_push_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    ImageLocation = args["location"]
    filename = dup_name
    ImagePath = os.path.join(ImageLocation, filename)
    ETag = response.headers['ETag']
    url = 'https://%s%s' % (idrac_ip, http_push_uri)
    files = {'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    if args["x"]:
        headers = {'X-Auth-Token': args["x"], "if-match": ETag}
        response = requests.post(url, files=files, headers=headers, verify=verify_cert)
    else:
        headers = {"if-match": ETag}
        response = requests.post(url, files=files, verify=verify_cert,auth=(idrac_username,idrac_password), headers=headers)
    try:
        post_command_response_output = response.json()
    except:
        logging.warning("- WARNING, unable to generate available entry for %s image to compare against installed version, script will skip this image and not install" % filename)
        remove_dup_list.append(filename)
        return
    if response.status_code == 201:
        logging.debug("\n- PASS: POST command passed successfully to download image")
    elif response.status_code == 400 and "firmware update operation because the specified firmware image is for a component that is not in the target system inventory" in post_command_response_output["error"]["@Message.ExtendedInfo"][0]["Message"].lower():
        logging.warning("- WARNING, specified firmware image is for a component that is not in the target system inventory")
        remove_dup_list.append(filename)
        time.sleep(10)
        return
    else:
        logging.error("\n- FAIL: POST command failed to download image payload, status code %s returned" % response.status_code)
        logging.error(post_command_response_output)
        sys.exit(0)
    available_entry = post_command_response_output['Id']
    logging.debug("- INFO, AVAILABLE entry created for download image \"%s\" is \"%s\"" % (filename, available_entry))

    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, available_entry), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, available_entry), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get AVAILABLE entry data, error: \n%s" % data)
        sys.exit(0)
    available_entry_details = {"Name": data["Name"], "Version": data["Version"], "etag": response.headers["ETag"]}
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get current firmware version details, error: \n%s" % data)
        sys.exit(0)
    for i in data["Members"]:
        for ii in i.items():
            if "installed" in ii[1].lower():
                if args["x"]:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                else:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, auth=(idrac_username, idrac_password))
                    data = response.json()
                    if response.status_code != 200:
                        logging.error("\n- ERROR, GET request failed to get URI details for Name and Version, error: \n%s" % data)
                        sys.exit(0)
                    installed_entry_details = {"Name": data["Name"], "Version": data["Version"]}
                    if available_entry_details["Name"] == installed_entry_details["Name"]:
                        logging.info("\n- Device Name: %s" % installed_entry_details["Name"])
                        logging.info("- Installed version detected: %s" % installed_entry_details["Version"])
                        logging.info("- Available package version detected: %s" % available_entry_details["Version"])
                        if installed_entry_details["Version"] != available_entry_details["Version"]:
                            logging.info("\n- INFO, version difference detected, script will apply firmware version %s" % available_entry_details["Version"])
                        elif installed_entry_details["Version"] == available_entry_details["Version"]:
                            logging.info("\n- WARNING, same version detected, script will NOT apply update package version")
                            remove_dup_list.append(filename)
                        url = 'https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, available_entry)
                        if args["x"]:
                            headers = {'X-Auth-Token': args["x"], "if-match": "%s" % available_entry_details["etag"]}
                            response = requests.delete(url, headers=headers, verify=verify_cert)
                        else:
                            headers = {"if-match": "%s" % available_entry_details["etag"]}
                            response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                        data = response.json()
                        if response.status_code == 200:
                            logging.debug("\n- PASS, successfully deleted available entry")
                            time.sleep(30)
                            break
                        else:
                            logging.error("\n- FAIL, command failed to delete available entry, error: \n%s. Entry will auto delete after 30 minutes" % data)
                            break
    
            
def idrac_cpld_update(firmware_image_device):
    global update_job_id
    global cpld_run
    global job_id_created
    cpld_run = False
    logging.info("- INFO, downloading update package \"%s\" to create update job, this may take a few minutes depending on firmware image size" % firmware_image_device.split("\\")[-1])
    if "cpld" in firmware_image_device.lower():
        cpld_run == True    
    url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
    payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
    files = {
         'UpdateParameters': (None, json.dumps(payload), 'application/json'),
         'UpdateFile': (os.path.basename(firmware_image_device), open(firmware_image_device, 'rb'), 'application/octet-stream')
    }
    check_valid_dup = firmware_image_device.split("\\")[-1]
    if not check_valid_dup.lower().endswith("exe"):
        logging.warning("- WARNING, invalid file detected '%s', update will not run" % check_valid_dup)
        job_id_created = "no"
        return
    if args["x"]:
        headers = {'X-Auth-Token': args["x"]}
        response = requests.post(url, files=files, headers=headers, verify=verify_cert)
    else:
        response = requests.post(url, files=files, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        logging.error("- FAIL, POST command failed status code %s returned" % response.status_code)
        try:
            data = response.json()
        except:
            logging.error("- WARNING, unable to get json response from POST call, manually check job queue to see if job ID was created")
            job_id_created = "no"
            return
        print(data)
        job_id_created = "no"
        return
    try:
        update_job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in header")
        sys.exit(0)
    logging.info("- PASS, update job ID %s successfully created for firmware package \"%s\"" % (update_job_id, firmware_image_device.split("\\")[-1]))
    job_id_created = "yes"

def check_job_status(download_job_id):
    retry_count = 1
    start_time = datetime.now()
    schedule_job_status_count = 1
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
        if data["Oem"]["Dell"]["JobState"] == "UserIntervention" and data["Oem"]["Dell"]["PercentComplete"] == 100:
            logging.info("\n- JOB ID %s completed in %s but user intervention is needed, final job message: %s" % (download_job_id, current_time, message_string[0]["Message"].rstrip(".")))
            if "reboot" in data["Oem"]["Dell"]["Message"].lower():
                logging.info("- INFO, rebooting server now for new firmware image installed to become effective")
                reboot_server()
                break
            if "virtual" in data["Oem"]["Dell"]["Message"].lower():
                logging.info("- INFO, performing virtual a/c cycle now for new firmware image installed to become effective")
                oem_ac_power_cycle()
                break
        elif "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "fail" in data['Oem']['Dell']['JobState'].lower():
            logging.error("- FAIL: Job ID %s failed, message: %s" % (download_job_id, data['Oem']['Dell']['Message']))
            sys.exit(0)
        elif data["TaskState"] == "Completed" and data["Oem"]["Dell"]["JobState"] or data["TaskState"] == "Completed" or "completed successfully" in data['Oem']['Dell']['Message'].lower():
            try:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Oem"]["Dell"]["Name"].replace(":",""), download_job_id))
            except:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Name"].replace(":",""), download_job_id))
            if run_idrac_update == True or "idrac" in message_string[0]["Message"].lower():
                break
            else:
                time.sleep(30)
                break
        elif str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            return
        elif "schedule" in data['Oem']['Dell']['Message'].lower():
            if schedule_job_status_count == 1:
                logging.info("- INFO, job status detected as scheduled, script will sleep 1 minute then check if job status has auto moved to running state")
                time.sleep(60)
                schedule_job_status_count += 1
                continue
            else:
                logging.info("- PASS, %s still in scheduled state, server reboot needed to apply the update" % data["Id"])
                update_jobs_need_server_reboot.append(download_job_id)
                time.sleep(30)
                break
        else:
            logging.info("- INFO, %s status: %s" % (download_job_id, message_string[0]["Message"].rstrip(".")))
            time.sleep(2)
            continue

def check_job_status_idrac(download_job_id):
    retry_count = 1
    start_time = datetime.now()
    schedule_job_status_count = 1
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
            time.sleep(3)
            retry_count += 1
            continue
        try:
            data = response.json()
        except:
            logging.warning("- WARNING, unable to get JSON response from get request for polling job status")
            sys.exit(0)
        current_time = str(datetime.now()-start_time)[0:7]   
        message_string = data["Messages"]
        if response.status_code == 200 or response.status_code == 202:
            logging.debug("- PASS, GET request command passed to check job status")
        else:
            logging.error("\n- ERROR, GET request failed to get job ID details, status code %s returned, error: \n%s" % (response.status_code, data))
            retry_count += 1
            continue
        if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "fail" in data['Oem']['Dell']['JobState'].lower():
            logging.error("- FAIL: Job ID %s failed, message: %s" % (download_job_id, data['Oem']['Dell']['Message']))
            sys.exit(0)
        elif data["TaskState"] == "Completed" and data["Oem"]["Dell"]["JobState"] or data["TaskState"] == "Completed" or "completed successfully" in data['Oem']['Dell']['Message'].lower() or "after restarting the server" in data['Oem']['Dell']['Message'].lower():
            try:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Oem"]["Dell"]["Name"].replace(":",""), download_job_id))
            except:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Name"].replace(":",""), download_job_id))
            break
        elif str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit(0)
        else:
            logging.info("- INFO, %s status: %s" % (download_job_id, message_string[0]["Message"].rstrip(".")))
            continue

def chassis_update(firmware_image_device, dup_name):
    global update_job_id
    logging.info("- INFO, downloading update package \"%s\" to create update job, this may take a few minutes depending on firmware image size" % dup_name)                                                                                                                                                                        
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
        update_job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in header")
        sys.exit(0)
    logging.info("- PASS, update job ID %s successfully created" % update_job_id)
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        check_idrac_connection()
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, update_job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, update_job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(30)
            retry_count += 1
            continue 
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit before marking the job as completed, manually check server state and iDRAC job queue\n")
            return
        elif "fail" in data['Message'].lower() or "fail" in data['JobState'].lower():
            logging.error("- FAIL: job ID %s failed, error results: \n%s" % (update_job_id, data['Message']))
            return
        elif "completed successfully" in data['Message']:
            try:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Oem"]["Dell"]["Name"].replace(":",""), update_job_id))
            except:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Name"].replace(":",""), update_job_id))
            time.sleep(30)
            break
        else:
            logging.info("- INFO, %s job status not completed, current status: \"%s\"" % (update_job_id, data['Message'].rstrip(".")))
            time.sleep(60)
            
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
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, reboot_update_job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, reboot_update_job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(30)
            retry_count += 1
            continue 
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code == 500:
            logging.error("- FAIL, status code 500 detected due to internal server error, script will sleep 3 minutes and retry get request")
            time.sleep(180)
            retry_count += 1
            continue
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s, script will sleep 15 seconds and retry get request" % response.status_code)
            time.sleep(15)
            retry_count += 1
            continue
        data = response.json()
        if str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, script stopped\n")
            return
        elif "fail" in data['Message'].lower() or "fail" in data['JobState'].lower():
            logging.error("- FAIL: job ID %s failed, error results: \n%s" % (reboot_update_job_id, data['Message']))
            sys.exit(0)
        elif "completed successfully" in data['Message']:
            try:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Oem"]["Dell"]["Name"].replace(":",""), reboot_update_job_id))
            except:
                logging.info("- PASS, %s job %s successfully marked completed" % (data["Name"].replace(":",""), reboot_update_job_id))
            time.sleep(30)
            break
        else:
            logging.info("- INFO, %s not completed, current status: \"%s\"" % (reboot_update_job_id, data['Message'].rstrip(".")))
            time.sleep(3)

def reboot_server():
    logging.info("- INFO, rebooting server to apply firmware update(s) which require a reboot")
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
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 2 minutes")
            time.sleep(60)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        retry_count = 1
        while True:
            if retry_count == 20:
                logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
                sys.exit(0)
            try:
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            except requests.ConnectionError as error_message:
                logging.info("- INFO, GET request failed due to connection error, script will sleep 15 seconds and retry")
                time.sleep(15)
                retry_count += 1
                continue 
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time >= "0:02:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                time.sleep(60)
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
                    try:
                        data = response.json()
                    except:
                        logging.warning("- WARNING, unable to get json response to validate current power state, retry in 60 seconds")
                        time.sleep(60)
                        if args["x"]:
                            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                        else:
                            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                        try:
                            data = response.json()
                        except:
                            logging.error("- FAIL, retry to get power state failed, script will exit")
                            sys.exit(0)
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
            logging.info("- INFO, iDRAC network connection lost due to slow network response or iDRAC reboot, waiting 30 seconds to access iDRAC again")
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
                        response = requests.get('https://%s/redfish/v1/TaskService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                    else:
                        response = requests.get('https://%s/redfish/v1/TaskService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
                except requests.ConnectionError as error_message:
                    logging.info("- INFO, GET request failed due to connection error, retry")
                    time.sleep(10)
                    continue
                break

def get_idrac_time():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    payload = {"GetRequest":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    try:
        data = response.json()
    except:
        logging.warning("- WARNING, unable to get current iDRAC time which is needed to get LC log update entries, script will now exit")
        sys.exit(0)
    if response.status_code == 200:
        logging.debug("\n- PASS: POST command passed to get iDRAC time, status code 200 returned\n")
    else:
        logging.error("\n- FAIL, POST command failed for %s action, status code %s returned" % response.status_code)
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    return data["TimeData"]


def get_lc_log_entries(start_date_timestamp, end_date_timestamp):
    update_entries = []
    uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries"
    date_range_uri = "%s?$filter=Created ge '%s' and Created le '%s'" % (uri, start_date_timestamp, end_date_timestamp)
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        logging.warning("- WARNING, unable to get LC log entries due to iDRAC reboot, all updates are complete. Please manually check LC logs for update entries")
        sys.exit(0)
    member_count = data["Members@odata.count"]
    for i in data["Members"]:
        if "sup0518" in i["MessageId"].lower() or "red063" in i["MessageId"].lower() or "pr36" in i["MessageId"].lower() or "sup0516" in i["MessageId"].lower() or "red025" in i["MessageId"].lower():
            update_entries.append(i["Message"])
    skip_count = 50
    while member_count >= skip_count:
        date_range_uri = "%s?$filter=Created ge '%s' and Created le '%s'&$top=50&$skip=%s" % (uri, start_date_timestamp, end_date_timestamp, skip_count)
        if args["x"]:
            response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
        try:
            data = response.json()
        except:
            break
        try:
            for i in data["Members"]:
                if "sup0518" in i["MessageId"].lower() or "red063" in i["MessageId"].lower() or "pr36" in i["MessageId"].lower() or "sup0516" in i["MessageId"].lower() or "red025" in i["MessageId"].lower():
                    update_entries.append(i["Message"])
        except:
            break
        skip_count += 50
    logging.info("\n- INFO, script complete, summary of updated device entries logged in LC logs -\n")
    if update_entries == []:
        logging.warning("- WARNING, no update entries detected, either no updates were performed or issues with searching LC logs")
    else:
        update_entries.reverse()
        for i in update_entries:
            print("- %s" % i)

def check_for_user_intervention_job(job_id):
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
            time.sleep(30)
            retry_count += 1
            continue 
        if response.status_code == 500:
            logging.error("- FAIL, status code 500 detected due to internal server error, script will sleep 3 minutes and retry get request")
            time.sleep(180)
            retry_count += 1
            continue
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s, script will sleep 15 seconds and retry get request" % response.status_code)
            time.sleep(15)
            retry_count += 1
            continue
        data = response.json()
        if data["JobState"] == "Completed":
            break
        elif data["JobState"] == "UserIntervention":
            if "reboot" in data["Message"].lower():
                logging.info("- INFO, server reboot required to enable firmware update for %s, server will now reboot" % job_id)
                reboot_flag = True
                break
            elif "virtual" in data["Message"].lower():
                logging.info("- INFO, virtual a/c cycle required to enable firmware update for %s, server will now perform virtual a/c cycle" % job_id)
                ac_flag = True
                break
            else:    
                break
        else:
            break

def oem_ac_power_cycle():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1?$select=PowerState' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1?$select=PowerState' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get current server power state, status code %s returned." % response.status_code)
        logging.warning(data)
        sys.exit(0)
    if data["PowerState"].lower() == "off":
        logging.info("- INFO, server already in OFF state, skipping power off operation")
        return
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" % idrac_ip
    payload = {"ResetType": "ForceOff"}
    if args["x"]:
        headers = {"content-type": "application/json", "X-Auth-Token": args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {"content-type": "application/json"}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to power off the server")
        time.sleep(10)
    else:
        logging.error("\n- FAIL, POST command failed, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        sys.exit(1) 
    url = 'https://%s/redfish/v1/Chassis/System.Embedded.1/Actions/Oem/DellOemChassis.ExtendedReset' % idrac_ip
    payload = {"ResetType": "PowerCycle", "FinalPowerState":"On"}   
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to perform full virtual server a/c power cycle, status code %s returned" % response.status_code)
        logging.info("\n- INFO, wait a few minutes for the process to complete, server will automatically power back on")
    else:
        logging.error("\n- FAIL, POST command failed, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        sys.exit(1)
        
        
    

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
        if not os.path.isdir(args["location"]):
            logging.error("\n- WARNING, value detected for argument --location is not a directory")
            sys.exit(0)
        reboot_flag = False
        ac_flag = False
        idrac_update_flag = False
        run_idrac_update = False
        cpld_update_flag = False
        cpld_run = False
        update_jobs_need_server_reboot = []
        remove_dup_list = []    
        from pathlib import Path
        directory_path = Path(args["location"]).resolve()
        directory_dups = os.listdir(args["location"])
        for i in directory_dups:   
            if not i.lower().endswith("exe"):
                directory_dups.remove(i)
        if directory_dups == []:
            logging.error("\n- WARNING, either directory path is empty or directory contains no valid Windows Dell Update Packages.")
            sys.exit(0)
        if args["block_same_version"]:
            logging.info("\n- INFO, argument --block-same-version detected to check update package version against installed version. This process may take a few minutes to complete depending on number of update packages\n")
            for ii in directory_dups:
                check_same_version(ii)
        if directory_dups == []:
            logging.error("\n- WARNING, either directory path is empty, no valid Windows update packages detected or same update package versions")
            sys.exit(0)
        if directory_dups == remove_dup_list:
            logging.info("\n- WARNING, same versions installed for all update packages detected, no updates will be performed")
            sys.exit(0)
        for i in remove_dup_list:
            if i in directory_dups:
                directory_dups.remove(i)
        start_time = get_idrac_time()
        for i in directory_dups:
            if "chassis" in i.lower():
                logging.info("- INFO, chassis system management DUP detected, update will get applied first")
                if platform.system().lower() == "linux":
                    chassis_directory_dup_path = args["location"] + "/" + i
                if platform.system().lower() == "windows":
                    chassis_directory_dup_path = args["location"] + "\\" + i
                chassis_update(chassis_directory_dup_path, i)
                directory_dups.remove(i)
        for i in directory_dups:
            if not i.endswith("/") or not i.endswith("\\"):
                if platform.system().lower() == "linux":
                    i = str(directory_path) + "/" + i
                if platform.system().lower() == "windows":
                    i = str(directory_path) + "\\" + i
            download_image_create_update_job(i)
            if job_id_created == "no":
                continue
            else:
                check_job_status(job_id)
        if update_jobs_need_server_reboot == [] and cpld_update_flag == False:
            logging.info("\n- INFO, no scheduled update jobs detected, server will not reboot")
        elif update_jobs_need_server_reboot == [] and cpld_update_flag == True:
            logging.info("- INFO, CPLD update detected, update will now get applied and once completed iDRAC will reboot")
            idrac_cpld_update(cpld_dup_package)
            if job_id_created == "yes":
                check_job_status(update_job_id)
                reboot_server()
                cpld_update_flag = False
                loop_check_final_job_status(update_job_id)
        elif update_jobs_need_server_reboot == [] and idrac_update_flag == True:
            logging.info("- INFO, iDRAC update detected, update will now get applied and once completed iDRAC will reboot")
            idrac_cpld_update(idrac_dup_package)
            if job_id_created == "yes":
                check_job_status_idrac(update_job_id)
        else:
            reboot_server()
            for i in update_jobs_need_server_reboot:
                loop_check_final_job_status(i)
        if cpld_update_flag == True and cpld_run == False:
            logging.info("- INFO, CPLD update detected, update will now get applied and once completed iDRAC will reboot")
            idrac_cpld_update(cpld_dup_package)
            if job_id_created == "yes":
                check_job_status(update_job_id)
                reboot_server()
                loop_check_final_job_status(update_job_id)
        if idrac_update_flag == True:
            logging.info("- INFO, iDRAC update detected, update will now get applied and once completed iDRAC will reboot")
            run_idrac_update = True
            idrac_cpld_update(idrac_dup_package)
            if job_id_created == "yes":
                check_job_status_idrac(update_job_id)
        end_time = get_idrac_time()
        get_lc_log_entries(start_time, end_time)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
# Python script using Redfish API to perform multiple BIOS operations (enable HD placeholder attribute and set HD placeholder device as first device in the boot order) using INI file. 
#
# Pseudo code workflow
#
# 1. Confirm IP address can be pinged.
# 2. Check remote API status, confirm LC status report ready.
# 3. Get BIOS attribute HD placeholder current value.
# 4. If HD placeholder attribute is set to Disabled, BIOS config job will get created to enable this attribute.
# 5. Set first device in UEFI boot order as the HD device from INI file, BIOS config job will get created.
# 6. Confirm first device in UEFI boot order is set to correct device.
# 7. All output will be echoed to the screen and also captured in a log file (log file name: "bios_script_logfile.txt")
#
# INI file examples("bios_config.ini" INI file name):
#
# [Parameters]
# idrac_ips=192.168.0.130,192.168.0.140,192.168.0.150
# idrac_username=root
# idrac_password=calvin
# hd_device_fqdd="RAID.Mezzanine.1-1"
#
# NOTE: For hd_device_fqdd pass in your controller FQDD, the one you want to set as first device in the boot order. Recommended to manually run this workflow first
# on a server to see what controller FQDD will be reported.
#
# This example shows passing in multiple iDRAC IPs using a comma separator
#
# [Parameters]
# idrac_ips=192.168.0.130-140
# idrac_username=root
# idrac_password=calvin
# hd_device_fqdd="RAID.Mezzanine.1-1"
#
# This example shows passing in range of iDRAC IPs. Script will loop through IPs starting at 192.168.0.130 up to 192.168.0.140.
#
# NOTES: All iDRAC IPs passed in the INI file must have the same username and password
#        INI file name used to run this script must be "bios_config.ini" and located in the same directory you're running the script from. 

import configparser
import json
import logging
import os
import platform
import random
import re
import requests
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

if os.path.exists("bios_script_logfile.txt"):
    os.remove("bios_script_logfile.txt")
    
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logStreamFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s", datefmt="%H:%M:%S")
consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logStreamFormatter)
consoleHandler.setLevel(level=logging.INFO)
logger.addHandler(consoleHandler)
logFileFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S",)
fileHandler = logging.FileHandler(filename="bios_script_logfile.txt")
fileHandler.setFormatter(logFileFormatter)
fileHandler.setLevel(level=logging.INFO)
logger.addHandler(fileHandler)

config = configparser.ConfigParser()
config.read("bios_config.ini")
config_ini_settings = config.items("Parameters")
idrac_ips = config.get("Parameters","idrac_ips")
idrac_username = config.get("Parameters","idrac_username")
idrac_password = config.get("Parameters","idrac_password")
hd_device_fqdd = config.get("Parameters","hd_device_fqdd")

if "," in idrac_ips:
    idrac_ips = idrac_ips.split(",")
elif "-" in idrac_ips:
    idrac_ips = idrac_ips.split("-")
    build_ip_list = [idrac_ips[0]]
    first_range_number = idrac_ips[0].split(".")[-1]
    second_range_number = idrac_ips[1]
    subnet = idrac_ips[0].split(".")[0]+"."+idrac_ips[0].split(".")[1]+"."+idrac_ips[0].split(".")[2]+"."
    create_range = range(int(first_range_number)+1,int(second_range_number)+1)
    for i in create_range:
        create_string = subnet + str(i)
        build_ip_list.append(create_string)
    idrac_ips = build_ip_list
else:
    idrac_ips = [idrac_ips]

def get_remote_services(idrac_ip):
    # Function to get remote api status, lifecycle controller status
    global get_remote_service_failure
    get_remote_service_failure = "no"
    start_time = datetime.now()
    current_time = str(datetime.now()-start_time)[0:7]
    while True:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % idrac_ip
        headers = {'content-type': 'application/json'}
        payload = {}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code != 200:
            logger.error("POST command failed for GetRemoteServicesAPIStatus method, status code %s returned" % response.status_code)
            get_remote_service_failure = "yes"
            return
        elif current_time >= "0:30:00":
            logger.error("FAIL, Max timeout of 30 minutes reached to poll checking LT ready status, no configuration operations executed. Make sure server is ON and outpof POST in idle state.")
            get_remote_service_failure = "yes"
            return   
        elif data["LCStatus"] == "Ready":
            logger.info("PASS, LC status is ready")
            break
        else: 
            logger.info("LC status not ready, current status: %s, %s" % data["LCStatus"])
            time.sleep(5)
    
def get_hd_placeholder_bios_attribute(idrac_ip):
    # Function to get current BIOS attribute HD placeholder setting
    global job_id
    global hd_placeholder_enabled
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes/HddPlaceholder' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error("GET command failed to get BIOS attribute HddPlaceholder, status code %s returned" % response.status_code)
        logging.error(data)
        return
    if data["Attributes"]["HddPlaceholder"] == "Disabled":
        logger.info("HD placeholder attribute disabled, setting to Enabled")
        hd_placeholder_enabled = "no"
    else:
        logger.info("HD placeholder attribute already enabled")
        hd_placeholder_enabled = "yes"

def set_pending_value_create_job(idrac_ip, attribute_name, attribute_value):
    # Function to set BIOS attribute pending value and create config job
    global job_id
    global set_pending_failure
    set_pending_failure = "no"
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"},"Attributes":{attribute_name:attribute_value}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logger.info("PATCH command passed to set BIOS attribute %s pending value and create next reboot config job" % attribute_name)
    else:
        logger.error("PATCH command failed to set BIOS attribute pending value and create next reboot config job, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("POST command failure:\n %s" % data)
        set_pending_failure = "yes"
        return
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logger.error("FAIL, unable to locate job ID in JSON headers output")
        set_pending_failure = "yes"
        return
    logger.info("BIOS config job ID %s successfully created" % job_id)    

def get_job_status_scheduled(idrac_ip):
    # Function to check BIOS config job status until marked scheduled
    count = 0
    while True:
        if count == 5:
            logging.error("FAIL, GET job status retry count of 5 has been reached, script will exit")
            return
        try:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=False,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logger.error(error_message)
            logger.info("GET request will try again to poll job status")
            time.sleep(5)
            count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logger.error("FAIL, Command failed to check job status, return code %s" % response.status_code)
            logger.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logger.info("Staged config job marked as scheduled")
            break
        else:
            logger.info("Job status not scheduled, current status: %s" % data['Message'])



def loop_job_status(idrac_ip):
    # Function to loop job status until marked completed
    start_time = datetime.now()
    while True:
        try:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=False,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logger.error(error_message)
            logger.info("GET request will try again to poll job status")
            time.sleep(10)
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logger.error("GET command failed to check job status, return code %s" % response.status_code)
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logger.error("Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logger.error("Job ID %s failed, failed message: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            logger.info("Job %s successfully marked completed" % job_id)
            time.sleep(60)
            # Delete job ID
            url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellJobService/Actions/DellJobService.DeleteJobQueue" % idrac_ip
            payload = {"JobID":job_id}
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
            if response.status_code == 200:
                logger.debug("PASS, successfully deleted job ID %s" % job_id)
                break
            else:
                logger.error("Unable to delete job ID %s, status code %s returned" % (job_id, response.status_code))
                break
        else:
            logger.info("Job status not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def reboot_server(idrac_ip):
    # Function to reboot the server for executing BIOS config job
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    logger.info("Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logger.info("POST command passed to gracefully power OFF server")
            logging.info("Script will now verify the server was able to perform a graceful shutdown. If the server was unable to, forced shutdown will be invoked in 3 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            logger.error("Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logger.error("Extended Info Message: {0}".format(response.json()))
            return
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logger.info("GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:03:00":
                logger.info("Unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("POST command passed to perform forced shutdown")
                    time.sleep(15)
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        logger.info("GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        logging.error("Server not in OFF state, current power status is %s" % data['PowerState'])
                        return   
            else:
                continue 
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logger.info("POST command passed to power ON server")
        else:
            logger.error("Command failed to power ON server, status code is: %s\n" % response.status_code)
            logger.error("Extended Info Message: {0}".format(response.json()))
            return
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logger.info("Command passed to power ON server, code return is %s" % response.status_code)
        else:
            logger.error("Command failed to power ON server, status code is: %s\n" % response.status_code)
            logger.error("Extended Info Message: {0}".format(response.json()))
            return
    else:
        logger.error("Unable to get current server power state to perform either reboot or power on")
        return
        
def ping_confirm_valid_ip(idrac_ip):
    # Check ping connection, valid IP address on the network
    global ping_success 
    ping_success = "yes"
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        logger.error("Unable to determine OS type, check iDRAC connection function will not execute")
        ping_success = "no"
    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
    if execute_command != 0:
        logger.error("Ping request failed for IP %s, script will skip using this IP" % idrac_ip)
        ping_success = "no"

def get_current_boot_order(idrac_ip):
    global boot_order_already_set
    boot_order_already_set = "no"
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error("GET command failed to get UEFI boot order, status code %s returned" % response.status_code)
        logging.error(data)
        return
    for i in data["Attributes"]["UefiBootSeq"]:
        if i["Index"] == 0:
            device_string = i["Id"].split("#")[2]
            if device_string.lower() == hd_device_fqdd.lower():
                logger.info("First device in UEFI boot order already set to %s, script done for iDRAC %s" % (hd_device_fqdd, idrac_ip))
                boot_order_already_set = "yes"
            else:
                logger.error("First device in boot order not set to %s, current first device: %s" % (hd_device_fqdd, device_string))
                
def get_new_boot_order(idrac_ip):
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellBootSources' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error("GET command failed to get UEFI boot order, status code %s returned" % response.status_code)
        logging.error(data)
        return
    for i in data["Attributes"]["UefiBootSeq"]:
        if i["Index"] == 0:
            device_string = i["Id"].split("#")[2]
            if device_string.lower() == hd_device_fqdd.lower():
                logger.info("First device in UEFI boot order successfully set to %s" % hd_device_fqdd)
            else:
                logger.error("First device in boot order not set to %s, current first device: %s" % (hd_device_fqdd, device_string))
                                                                            
if __name__ == "__main__":
    for idrac_address in idrac_ips:
        ping_confirm_valid_ip(idrac_address)
        if ping_success == "no":
            continue
        if platform.python_version()[0] == "3":
            logger.debug("Correct version of Python detected to run this script")
        else:
            logger.error("Incorrect Python version detected. Python 3 version is required to execute this script")
            sys.exit(0)
        logger.debug("Executing script to enable HD placeholder attribute if disabled and set HD device as first device in UEFI boot order for iDRAC %s" % idrac_address)
        get_remote_services(idrac_address)
        if get_remote_service_failure == "yes":
           continue
        get_current_boot_order(idrac_address)
        if boot_order_already_set == "yes":
            continue
        get_hd_placeholder_bios_attribute(idrac_address)
        if hd_placeholder_enabled != "yes":
            set_pending_value_create_job(idrac_address, "HddPlaceholder", "Enabled")
            if set_pending_failure == "yes":
                continue
            else:
                get_job_status_scheduled(idrac_address)
                reboot_server(idrac_address)
                loop_job_status(idrac_address)
        set_pending_value_create_job(idrac_address, "SetBootOrderFqdd1", hd_device_fqdd)
        if set_pending_failure == "yes":
            continue
        else:
            get_job_status_scheduled(idrac_address)
            reboot_server(idrac_address)
            loop_job_status(idrac_address)
            get_new_boot_order(idrac_address)  
    logger.info("Script complete, script logs also captured in \"bios_script_logfile.txt\" file")

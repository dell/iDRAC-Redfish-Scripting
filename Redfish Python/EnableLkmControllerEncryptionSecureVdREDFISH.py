# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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

# Python script using Redfish API with OEM actions to perform multiple storage operations on iDRAC(s) using INI file. 
#
# Pseudo code workflow
#
# 1. Confirm IP address can be pinged.
# 2. Check remote API status, confirm LC and RT status both report ready.
# 3. Get storage controllers which support enabling local key management (LKM).
# 4. Enable LKM if not already enabled.
# 5. Get current VDs already created for storage controller.
# 6. Secure any VD detected behind the storage controller which supports encryption.
# 7. Confirm newly encrypted VDs are secured.
# 8. All output will be echoed to the screen and also captured in a log file (log file name: "LKM_script_logfile.txt")
#
# INI file examples("config_LKM.ini" INI file name):
#
# [Parameters]
# idrac_ips=192.168.0.130,192.168.0.140,192.168.0.150
# idrac_username=root
# idrac_password=calvin
# key_id=testkey
# passphrase=Test1234#
#
# This example shows passing in multiple iDRAC IPs using a comma separator
#
# [Parameters]
# idrac_ips=192.168.0.130-140
# idrac_username=root
# idrac_password=calvin
# key_id=testkey
# passphrase=Test1234#
#
# This example shows passing in range of iDRAC IPs. Script will loop through IPs starting at 192.168.0.130 up to 192.168.0.140.
#
# NOTES: All iDRAC IPs passed in the INI file must have the same username and password
#        INI file name used to run this script must be "config_LKM.ini" and located in the same directory you're running the script from. 

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

if os.path.exists("LKM_script_logfile.txt"):
    os.remove("LKM_script_logfile.txt")
    
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logStreamFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s", datefmt="%H:%M:%S")
consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logStreamFormatter)
consoleHandler.setLevel(level=logging.INFO)
logger.addHandler(consoleHandler)
logFileFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S",)
fileHandler = logging.FileHandler(filename="LKM_script_logfile.txt")
fileHandler.setFormatter(logFileFormatter)
fileHandler.setLevel(level=logging.INFO)
logger.addHandler(fileHandler)

config = configparser.ConfigParser()
config.read("config_LKM.ini")
config_ini_settings = config.items("Parameters")
idrac_ips = config.get("Parameters","idrac_ips")
idrac_username = config.get("Parameters","idrac_username")
idrac_password = config.get("Parameters","idrac_password")
key_id = config.get("Parameters","key_id")
passphrase = config.get("Parameters","passphrase")
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
    # Function to get remote api status, lifecycle controller and realtime monitoring status
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
            logger.error("FAIL, POST command failed for GetRemoteServicesAPIStatus method, status code %s returned" % response.status_code)
            get_remote_service_failure == "yes"
            break
        elif current_time >= "0:30:00":
            logger.error("FAIL, Max timeout of 30 minutes reached to poll checking RT and LT ready status, no configuration operations executed. Make sure server is ON and outpof POST in idle state.")

            get_remote_service_failure == "yes"
            break     
        elif data["LCStatus"] == "Ready" and data["RTStatus"] == "Ready":
            logger.info("PASS, LC and RT status is ready")
            break
        else: 
            logger.info("LC and RT status not ready, current status: %s, %s" % (data["LCStatus"], data["RTStatus"]))
            time.sleep(5)
    
def get_supported_controllers(idrac_ip):
    # Function to get current storage controllers supported to enable LKM
    global supported_controller_LKM
    supported_controller_LKM = []
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("FAIL, GET command failed to get storage controller FQDDs, status return code %s" % response.status_code)
        return
    data = response.json()
    controller_list = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
    for i in controller_list:
        if "ahci" not in i.lower() or "pci" not in i.lower() or "nonraid" not in i.lower() or "cpu" not in i.lower(): 
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to controller properties, status return code %s" % response.status_code)
                return
            data = response.json()
            try:
                if "localkey" in data["Oem"]["Dell"]["DellController"]["EncryptionCapability"].lower():
                    logger.info("LKM supported controller detected: %s" % i)
                    if "localkey" in data["Oem"]["Dell"]["DellController"]["EncryptionMode"].lower():
                        logger.info("LKM already enabled for controller %s" % i)
                        supported_controller_LKM.append({i:"Enabled"})
                    else:
                        supported_controller_LKM.append({i:"Disabled"})
            except:
                logger.warning("Unable to get OEM properties for controller %s, skipping this controller" % i)

def enable_controller_encryption(idrac_ip, storage_controller):
    # Enable LKM for the controller
    global job_id
    global fail_enable_encryption
    fail_enable_encryption = "no"
    logger.info("Enabling LKM encryption for controller %s" % storage_controller)
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService/Actions/DellRaidService.SetControllerKey' % idrac_ip
    payload={"TargetFQDD":storage_controller,"Key":passphrase,"Keyid":key_id}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logger.debug("PASS, POST command passed to set %s controller key" % storage_controller)
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logger.error("FAIL, unable to locate job ID in JSON headers output")
            fail_enable_encryption = "yes"
        logger.info("Job %s successfully created to enable controller %s encryption" % (job_id, storage_controller))
    else:
        logger.error("POST command failed to set the controller key for controller %s" % storage_controller)
        fail_enable_encryption = "yes"
                   
def get_secure_vds(idrac_ip, supported_controller_FQDD):
    # Function to get current VDs detected for LKM enabled controller
    global secure_new_VDs
    secure_new_VDs = []
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, supported_controller_FQDD),verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("GET command failed to get VD FQDDs, status return code %s" % response.status_code)
        return
    data = response.json()
    vd_list = []
    if data['Members'] == []:
        logger.warning("GET command returned no VDs detected for controller %s" % supported_controller_FQDD)
        return
    else:
        for ii in data['Members']:
            vd_list.append(ii['@odata.id'].split("/")[-1])
    for vd_FQDD in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, vd_FQDD),verify=False, auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logger.error("GET command failed to get VD properties, status return code %s" % response.status_code)
            return
        data = response.json()
        if data["Encrypted"] == False:
            secure_new_VDs.append(vd_FQDD)

def encrypt_new_VD(idrac_ip, vd_FQDD):
    # Function to secure (encrypt) VDs already created
    global job_id
    global fail_enable_encryption
    global secure_new_VDs_job_creation
    global job_creation_success
    fail_enable_encryption = "no"
    job_creation_success = "no"
    secure_new_VDs_job_creation = []
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService/Actions/DellRaidService.LockVirtualDisk' % (idrac_ip)
    payload = {"TargetFQDD": vd_FQDD}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logger.debug("PASS: POST command passed to secure virtual disk \"%s\"" % vd_FQDD)
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logger.error("Unable to locate job ID in JSON headers output")
            fail_enable_encryption = "yes"
        logger.info("Job %s successfully created to secure %s VD" % (job_id, vd_FQDD))
        secure_new_VDs_job_creation.append(vd_FQDD)
        job_creation_success = "yes"
    elif response.status_code == 400:
        if "not security capable" in data["error"]["@Message.ExtendedInfo"][0]["Message"].lower():
            logger.debug("WARNING, VD %s does not support enabling encryption")
        else:
            logger.error("POST command failed to secure VD %s" % vd_FQDD)
    else:
        logger.error("POST command failed to secure VD %s" % vd_FQDD)

def get_secure_vds_new_status(idrac_ip, vd_FQDD):
    # Function to get secured status for newly encrypted VDs
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, vd_FQDD),verify=False, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("GET command failed to get VD properties, status return code %s" % response.status_code)
        return
    data = response.json()
    if data["Encrypted"] == True:
        logger.info("PASS, VD %s successfully secured" % vd_FQDD)
    elif data["Encrypted"] == False:
        logger.error("VD %s not secured" % vd_FQDD)

def loop_job_status(idrac_ip):
    # Function to loop job status until marked completed
    start_time = datetime.now()
    while True:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=False,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logger.error("GET command failed to check job status, return code %s" % response.status_code)
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logger.error("Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logger.error("Job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            logger.info("PASS, job %s successfully marked completed" % job_id)
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
        logger.info("Executing script to enable LKM controller encryption and secure VD(s) for iDRAC %s" % idrac_address)
        get_remote_services(idrac_address)
        if get_remote_service_failure == "yes":
           continue
        get_supported_controllers(idrac_address)
        if supported_controller_LKM == []:
            logger.info("No supported controllers detected to enable LKM, skipping iDRAC %s" % idrac_address)
            continue
        for i in supported_controller_LKM:
            for ii in i.items():
                if ii[1] == "Disabled":
                    enable_controller_encryption(idrac_address, ii[0])
                    time.sleep(5)
                    if fail_enable_encryption == "yes":
                        logger.warning("Failed to enable %s controller encryption, skipping secure VD step" % ii[0])
                        continue
                    loop_job_status(idrac_address)   
                get_secure_vds(idrac_address, ii[0])
                if secure_new_VDs == []:
                    logger.warning("No supported VDs detected or all detected VDs already secured")
                    continue
                for vd_FQDD_string in secure_new_VDs:
                    encrypt_new_VD(idrac_address, vd_FQDD_string)
                    if job_creation_success == "yes":
                        time.sleep(5)
                        loop_job_status(idrac_address)
                if secure_new_VDs_job_creation == []:
                    logger.warning("No new config jobs created to secure VDs, either no supported VDs detected or existing supported VDs already secured for %s controller" % ii[0])
                    continue
                else:
                    for vd_FQDD_secured in secure_new_VDs_job_creation:
                        get_secure_vds_new_status(idrac_address, vd_FQDD_secured)
    logger.info("Script complete, script logs also captured in \"LKM_script_logfile.txt\" file")

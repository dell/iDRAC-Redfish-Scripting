# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2026, Dell, Inc.
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
# 3. Get supported iDRAC licenses installed to confirm iLKM is supported.
# 4. Enable iDRAC iLKM setting.
# 5. Get supported controllers (PERC and BOSS) and enable iLKM on these controllers.
# 6. Create VDs for PERC if any drive(s) shows up as Ready status and not secured.
# 7. Secure all VDs behind PERC which can be secured. 
# 8. Validate all drives and VDs are secure. 
# 9. All output will be echoed to the screen and also captured in a log file (log file name: "iLKM_script_logfile.txt")
#
# INI file examples("config_iLKM.ini" ini file name):
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
#        INI file name used to run this script must be "config_iLKM.ini" and located in the same directory you're running the script from. 

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

if os.path.exists("iLKM_script_logfile.txt"):
    os.remove("iLKM_script_logfile.txt")
    
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logStreamFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s", datefmt="%H:%M:%S")
consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logStreamFormatter)
consoleHandler.setLevel(level=logging.INFO)
logger.addHandler(consoleHandler)
logFileFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S",)
fileHandler = logging.FileHandler(filename="iLKM_script_logfile.txt")
fileHandler.setFormatter(logFileFormatter)
fileHandler.setLevel(level=logging.INFO)
logger.addHandler(fileHandler)

config = configparser.ConfigParser()
config.read("config_iLKM.ini")
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
            time.sleep(15)


def get_supported_iDRAC_licenses(idrac_ip):
    # Function to get supported iDRAC licenses, SEKM license and either Enterprise or Datacenter license must be installed to support iLKM.
    global iDRAC_supported_licenses_installed
    iDRAC_supported_licenses_installed = "no"
    datacenter_license = "no"
    enterprise_license = "no"
    sekm_license = "no"
    response = requests.get('https://%s/redfish/v1/LicenseService/Licenses?$select=Members' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("FAIL, GET command failed to get iDRAC license details, status return code %s" % response.status_code)
        return
    data = response.json()
    for i in data["Members"]:
        for ii in i.items():
            response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to get individual license details, status return code %s" % response.status_code)
                return
            data = response.json()
            if "datacenter" in data["Description"].lower() and "idrac" in data["Description"].lower():
                datacenter_license = "yes"
            elif "enterprise" in data["Description"].lower() and "idrac" in data["Description"].lower():
                enterprise_license = "yes"
            elif "key manager" in data["Description"].lower():
                sekm_license = "yes"
    if sekm_license == "yes" and datacenter_license == "yes" or enterprise_license == "yes":
        logger.info("PASS, correct iDRAC licenses are installed to enable iLKM")
        iDRAC_supported_licenses_installed = "yes"


def set_reboot_jobtype_powercycle(idrac_ip):
    # Function to set rebot job type to powercycle. This setting will speed up the overall workflow. 
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/System.Embedded.1" % idrac_ip
    headers = {'content-type': 'application/json'}
    payload = {"Attributes":{"Job.1.RebootJobType":"Powercycle"}}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error("FAIL, PATCH command failed to set reboot job type to powercycle for iDRAC %s, status code %s returned" % (idrac_ip, response.status_code))
        return


def get_set_iDRAC_iLKM_status(idrac_ip):
    # Function to get iDRAC iLKM current status, if enabled or disabled. If disabled then enable it. 
    global iDRAC_iLKM_current_setting
    iDRAC_iLKM_current_setting = ""
    response = requests.get("https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1?$select=Attributes/SEKM.1.iLKMStatus" % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("FAIL, GET command failed to get iDRAC iLKM current status, status return code %s" % response.status_code)
        return
    data = response.json()
    iDRAC_iLKM_current_setting = data["Attributes"]["SEKM.1.iLKMStatus"]
    if iDRAC_iLKM_current_setting == "Enabled":
        logger.info("WARNING, current iDRAC iLKM setting already set to Enabled, set will not be performed")
    elif iDRAC_iLKM_current_setting == "Disabled":
        logger.info("INFO, current iDRAC iLKM setting is Disabled, enabling iLKM")
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.EnableiLKM' % idrac_ip
        headers = {'content-type': 'application/json'}
        payload = {"KeyID": key_id, "Passphrase": passphrase}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code != 202:
            logger.error("FAIL, POST command failed to enable iLKM for iDRAC %s, status code %s returned" % (idrac_ip, response.status_code))
            iDRAC_iLKM_current_setting = "fail"
        try:
            job_id_uri = response.headers["Location"]
        except:
            logger.error("FAIL, unable to find job ID URI in headers POST response, headers output is:\n%s" % response.headers)
            return
        loop_count = 0
        time.sleep(10)
        while loop_count != 20:
            if loop_count == 20:
                logger.error("FAIL, unable to detect completed job status for iDRAC %s, script will exit" % idrac_ip)
                return
            response = requests.get("https://%s%s" % (idrac_ip, job_id_uri),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to get job status details, status return code %s" % response.status_code)
                return
            data = response.json()
            if data["JobState"] == "Completed" and "success" in data["Message"].lower():
                logger.info("PASS, iDRAC iLKM setting successfully enabled")
                break
            elif "error" in data["Message"].lower() or "fail" in data["Message"].lower():
                logger.error("FAIL, job ID failed to enable iLKM for iDRAC %s, review iDRAC LC logs and job queue for more details" % idrac_ip)
                return
            else:
                logger.info("INFO, job ID not marked completed, will check status again in 10 seconds")
                time.sleep(10)
                loop_count += 1
                continue

               
def get_supported_controllers_enable_iLKM(idrac_ip):
    # Function to get current storage controllers supported to enable iLKM
    global job_id_URIs_enable_iLKM_dict
    global controllers_enable_iLKM
    job_id_URIs_enable_iLKM_dict = {idrac_ip:[]}
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logger.error("FAIL, GET command failed to get storage controller FQDDs, status return code %s" % response.status_code)
        return
    data = response.json()
    controller_list = []
    controllers_enable_iLKM = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
    for i in controller_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logger.error("FAIL, GET command failed to controller properties, status return code %s" % response.status_code)
            return
        data = response.json()
        if "boss" in data["Name"].lower() or "perc" in data["Name"].lower():
            if data["Oem"]["Dell"]["DellController"]["EncryptionCapability"] == "Capable" and data["Oem"]["Dell"]["DellController"]["SecurityStatus"] == "Enabled" or data["Oem"]["Dell"]["DellController"]["SecurityStatus"] == "SecurityKeyAssigned":
                logger.info("WARNING, supported controller %s detected to enable iLKM but iLKM is already enabled, POST call to enable will not run" % data["Id"])
            elif data["Oem"]["Dell"]["DellController"]["EncryptionCapability"] == "Capable" and data["Oem"]["Dell"]["DellController"]["SecurityStatus"] != "Enabled" or data["Oem"]["Dell"]["DellController"]["SecurityStatus"] != "SecurityKeyAssigned":
                logger.info("INFO, supported controller %s detected to enable iLKM but iLKM is not enabled" % data["Id"])
                controllers_enable_iLKM.append(i)
    controllers_enable_iLKM.sort()
    controllers_enable_iLKM.reverse()
    for i in controllers_enable_iLKM:
        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService/Actions/DellRaidService.EnableSecurity" % idrac_ip
        headers = {'content-type': 'application/json'}
        payload = {"TargetFQDD":i, "@Redfish.OperationApplyTime": "OnReset"}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code != 202:
            logger.error("FAIL, POST command failed to enable iLKM for controller %s, status code %s returned" % (i, response.status_code))
            continue
        try:
            job_id = response.headers["Location"].split("/")[-1]
        except:
            logger.error("FAIL, unable to find job ID URI in headers POST response, headers output is:\n%s" % response.headers)
            return
        logger.info("PASS, POST command passed to enable iLKM for controller %s, job ID %s created" % (i, job_id))
        job_id_URIs_enable_iLKM_dict[idrac_ip].append(job_id)
        

def loop_job_status(idrac_ip, job_id):
    # Function to loop job status until marked completed
    start_time = datetime.now()
    reboot_performed = "no"
    while True:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=False,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code == 200 or response.status_code == 202:
            logger.debug("- PASS, GET request passed to check job status")
        else:
            logger.error("GET command failed to check job status, return code %s" % response.status_code)
            return
        data = response.json()
        if str(current_time)[0:7] >= "1:00:00":
            logger.error("Timeout of 1 hour has been hit, script stopped\n")
            return
        elif "fail" in data["Message"].lower() or data["JobState"] == "Failed":
            logger.error("Job ID %s failed, failed message: %s" % (job_id, data["Message"]))
            return
        elif data["JobState"] == "Scheduled" and reboot_performed == "no":
            logger.warning("WARNING, job ID %s detected as scheduled, server reboot is required to run this job" % job_id)
            url = "https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" % idrac_ip
            payload = {"ResetType": "ForceRestart"}
            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
            if response.status_code == 204:
                logger.info("PASS, POST command passed to reboot the server")
                reboot_performed = "yes"
                continue
            else:
                logger.error("FAIL, command failed to reboot the server, status code %s returned\n" % response.status_code)
                logger.error(response.json())
                return
                           
        elif data["JobState"] == "Completed":
            logger.info("PASS, job %s successfully marked completed" % job_id)
            time.sleep(10)
            break
        else:
            logger.info("Job status not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def confirm_iLKM_controller_enable(idrac_ip):
    # Function to validate iLKM is successfully enabled on the controller
    for i in controllers_enable_iLKM:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logger.error("FAIL, GET command failed to get iLKM status for controller %s, status return code %s" % (i, response.status_code))
            return
        data = response.json()
        if data["Oem"]["Dell"]["DellController"]["SecurityStatus"] == "Enabled" or data["Oem"]["Dell"]["DellController"]["SecurityStatus"] == "SecurityKeyAssigned":
            logger.info("PASS, confirmed iLKM is enabled on controller %s" % i)
        else:
            logger.error("FAIL, iLKM not enabled on controller %s, current security status: %s" % (i, data["Oem"]["Dell"]["DellController"]["SecurityStatus"]))
            break


def confirm_controller_drives_secured(idrac_ip):
    # Function to validate controller drives are secured (unlocked)
    for i in controllers_enable_iLKM:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logger.error("FAIL, GET command failed to get controller details for %s, status return code %s" % (i, response.status_code))
            return
        data = response.json()
        for i in data["Drives"]:
            for ii in i.items():
                response = requests.get("https://%s%s" % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                if response.status_code != 200:
                    logger.error("FAIL, GET command failed to get drive encryption status, status return code %s" % (i, response.status_code))
                    return
            data = response.json()
            if data["EncryptionAbility"] == "None":
                continue
            elif data["EncryptionStatus"] == "Unlocked":
                logger.info("PASS, drive %s validated as secured (unlocked)" % ii[1].split("/")[-1])
            else:
                logger.error("FAIL, drive %s not secured (unlocked), current status %s" % (ii[1].split("/")[-1], data["EncryptionStatus"]))
                continue


def create_VDs(idrac_ip):
    # Function to create one drive RAID 0 for all encryption capable drives in ready state
    for i in controllers_enable_iLKM:
        if "raid" in i.lower():
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to get controller details for %s, status return code %s" % (i, response.status_code))
                return
            data = response.json()
            for i in data["Drives"]:
                for ii in i.items():
                    response = requests.get("https://%s%s" % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                    if response.status_code != 200:
                        logger.error("FAIL, GET command failed to get drive encryption status, status return code %s" % (i, response.status_code))
                        return
                    data = response.json()
                    if data["Oem"]["Dell"]["DellPhysicalDisk"]["RaidStatus"] == "Ready" and data["EncryptionAbility"] == "SelfEncryptingDrive":
                        logger.info("INFO, drive %s detected as encryption capable and in ready state, secured VD will be created" % ii[1].split("/")[-1])
                        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes" % (idrac_ip, ii[1].split(":")[-1])
                        headers = {'content-type': 'application/json'}
                        payload = {"RAIDType": "RAID0", "Links": {"Drives": [{"@odata.id": ii[1]}]}}
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
                        if response.status_code != 202:
                            logger.error("FAIL, POST command failed to create RAID 0 VD for drive %s, status code %s returned" % (ii[1], response.status_code))
                            print(data)
                            continue
                        try:
                            job_id = response.headers["Location"].split("/")[-1]
                        except:
                            logger.error("FAIL, unable to find job ID URI in headers POST response, headers output is:\n%s" % response.headers)
                            return
                        logger.info("PASS, POST command passed to create one drive RAID 0 VD using drive %s, job ID %s created" % (ii[1].split("/")[-1], job_id))
                        loop_job_status(idrac_ip, job_id)


def get_unsecured_VDs_secure_VDs(idrac_ip):
    # Function to get all unsecured VDs for PERC controller and secure
    valid_VDs_to_secure = []
    for i in controllers_enable_iLKM:
        if "raid" in i.lower():
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to get controller VD(s) for %s, status return code %s" % (i, response.status_code))
                return
            data = response.json()
            for ii in data["Members"]:
                for iii in ii.items():
                    response = requests.get('https://%s%s' % (idrac_ip, iii[1]),verify=False,auth=(idrac_username, idrac_password))
                    if response.status_code != 200:
                        logger.error("FAIL, GET command failed to get controller details for %s, status return code %s" % (i, response.status_code))
                        return
                    data = response.json()
                    if data["Oem"]["Dell"]["DellVirtualDisk"]["RaidStatus"] == "Online" and data["Encrypted"] == True:
                        logger.info("INFO, online VD %s already secured, skipping POST call to secure" % data["Id"])
                        continue
                    elif data["Oem"]["Dell"]["DellVirtualDisk"]["RaidStatus"] == "Online" and data["Encrypted"] == False:
                        valid_VDs_to_secure.append(data["Id"])
                        VD_ID = data["Id"]
                        logger.info("INFO, online VD %s detected as not secured" % data["Id"])
                        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService/Actions/DellRaidService.SecureVirtualDisk" % idrac_ip
                        headers = {'content-type': 'application/json'}
                        payload = {"TargetFQDD": data["Id"]}
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
                        data = response.json()
                        if response.status_code != 202:
                            logger.error("FAIL, POST command failed to secure VD %s, status code %s returned" % (data["Id"], response.status_code))
                            print(data)
                            continue
                        try:
                            job_id = response.headers["Location"].split("/")[-1]
                        except:
                            logger.error("FAIL, unable to find job ID URI in headers POST response, headers output is:\n%s" % response.headers)
                            return
                        logger.info("PASS, POST command passed to secure VD %s, job ID %s created" % (VD_ID, job_id))
                        time.sleep(10)
                        loop_job_status(idrac_ip, job_id)
    if valid_VDs_to_secure != []:
        for i in valid_VDs_to_secure:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes/%s' % (idrac_ip, i.split(":")[-1], i),verify=False,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logger.error("FAIL, GET command failed to get VD details for %s, status return code %s" % (i, response.status_code))
                return
            data = response.json()
            if data["Oem"]["Dell"]["DellVirtualDisk"]["RaidStatus"] == "Online" and data["Encrypted"] == True:
                logger.info("PASS, online VD %s successfully secured" % i)
            else:
                logger.error("FAIL, VD %s is not secured, current secured status" %s % (i, data["Encrypted"]))

            
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
        logger.info("Executing script to enable iDRAC iLKM feature and secure drives for iDRAC %s" % idrac_address)
        get_remote_services(idrac_address)
        if get_remote_service_failure == "yes":
           continue
        get_supported_iDRAC_licenses(idrac_address)
        #set_reboot_jobtype_powercycle(idrac_address)
        if iDRAC_supported_licenses_installed == "no":
            logger.error("FAIL, missing iDRAC licenses to enable iLKM, iLKM will not be enabled on iDRAC %s" % idrac_address)
            continue
        get_set_iDRAC_iLKM_status(idrac_address)
        if iDRAC_iLKM_current_setting == "fail":
            logger.error("- WARNING, unable to enable iDRAC iLKM setting for iDRAC %s, script will not proceed with this workflow. Check iDRAC LC logs for more details" % idrac_address)
            continue
        get_supported_controllers_enable_iLKM(idrac_address)
        if job_id_URIs_enable_iLKM_dict[idrac_address] == []:
            logger.error("WARNING, no job IDs successfully created for iDRAC %s to enable iLKM on storage controllers, check iDRAC LC logs for more details" % idrac_address)
            continue
        time.sleep(10)
        for i in job_id_URIs_enable_iLKM_dict.items():
            logger.info("INFO, checking all job(s) are marked successfully completed for iDRAC %s" % i[0])
            for ii in i[1]:
                logger.info("INFO, checking job ID %s job status" % ii)
                loop_job_status(i[0], ii)
        get_remote_services(idrac_address)
        confirm_iLKM_controller_enable(idrac_address)
        create_VDs(idrac_address)
        get_unsecured_VDs_secure_VDs(idrac_address)
        confirm_controller_drives_secured(idrac_address)
        logger.info("PASS, iLKM workflow solution complete for iDRAC %s\n" % idrac_address)
    logger.info("Script complete, script logs also captured in \"iLKM_script_logfile.txt\" file")

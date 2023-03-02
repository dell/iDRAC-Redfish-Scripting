#!/usr/bin/python3
#
#_author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 8.0
#
# Copyright (c) 2022, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Python module for iDRAC Redfish support to perform multiple workflows. 

import base64
import getpass
import json
import logging
import os
import platform
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def set_iDRAC_script_session(script_examples=""):
    """Function to set iDRAC session used to execute all workflows for this session: pass in iDRAC IP, iDRAC username and iDRAC password. It will also prompt for SSL certificate verification for all Redfish calls and finally prompt to create X-auth token session. By creating X-auth token session, all Redfish calls executed will use this X-auth token session for authentication instead of username/password."""
    global creds
    global x_auth_token
    if script_examples:
        print("\n- IdracRedfishSupport.set_iDRAC_script_session(), this example will prompt the user to input iDRAC IP, iDRAC username, iDRAC password, SSL cert verification and create X-auth token session")
    else:
        x_auth_token = "no"
        creds = {}
        idrac_ip = input(str("- Enter iDRAC IP: "))
        creds["idrac_ip"] = idrac_ip
        idrac_username = input(str("- Enter iDRAC username: "))
        creds["idrac_username"] = idrac_username
        idrac_password = getpass.getpass("- Enter iDRAC %s password: " % idrac_username)
        creds["idrac_password"] = idrac_password
        verify_cert = input(str("- Verify SSL certificate, pass in True to verify or False to ignore: "))
        if verify_cert.lower() == "true":
            creds["verify_cert"] = True
        elif verify_cert.lower() == "false":
            creds["verify_cert"] = False
        else:
            logging.info("- INFO, invalid value entered to verify SSL certificate")
            return
        user_response = input(str("- Create iDRAC X-auth token session? Pass in \"y\" for yes or \"n\" for no. Creating iDRAC X-auth token session, all Redfish commands will be executed using this X-auth token for auth instead of username/password: "))
        if user_response.lower() == "y":
            x_auth_token = "yes"
            response = requests.get('https://%s/redfish/v1' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("\n- ERROR, GET request failed, status code %s returned, check login credentials" % (response.status_code))
                return
            else:
                data = response.json()
            if response.status_code != 200:
                logging.warning("\n- WARNING, GET request failed to get Redfish version, status code %s returned" % response.status_code)
                return
            else:
                pass
            redfish_version = int(data["RedfishVersion"].replace(".",""))
            if redfish_version >= 160:
                session_uri = "redfish/v1/SessionService/Sessions"
            elif redfish_version < 160:
                session_uri = "redfish/v1/Sessions"
            else:
                logging.info("- INFO, unable to select URI based off Redfish version")
                return
            url = 'https://%s/%s' % (creds["idrac_ip"], session_uri)
            payload = {"UserName":creds["idrac_username"],"Password":creds["idrac_password"]}
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            data = response.json()
            if response.status_code == 201:
                logging.info("\n- PASS, iDRAC X auth token successfully created. X auth sessions URI \"%s\"" % response.headers["Location"])
            else:
                try:
                    logging.error("\n- ERROR, unable to create X-auth_token session, status code %s returned, detailed error results:\n %s" % (response.status_code, data))
                except:
                    logging.error("\n- ERROR, unable to create X-auth_token session, status code %s returned" % (response.status_code))
                return
            creds["idrac_x_auth_token"] = response.headers["X-Auth-Token"]
        elif user_response.lower() != "n":
            logging.error("- ERROR, invalid value entered to create iDRAC x-auth token session")
            return

def return_iDRAC_script_session_details(script_examples=""):
    """Function to return iDRAC IP and iDRAC username session information that was captured by get_iDRAC_creds()"""
    if script_examples:
        print("\n- IdracRedfishSupport.return_iDRAC_script_session_details(), this example will return current iDRAC session details for iDRAC IP and username only")
    else:
        print("iDRAC IP: %s" % creds["idrac_ip"])
        print("iDRAC username: %s" % creds["idrac_username"])
    
def get_storage_controllers(script_examples=""):
    """Function to get server storage controller FQDDs"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_controllers(), this example will return current storage controller FQDDs detected. These FQDDs can be used to execute other storage functions to get physcial disks, virtual disks, reset controller are some examples.")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, status code %s returned, detailed error results:\n%s" % (response.status_code, data))
            return
        print("\n- Server controller(s) detected -\n")
        controller_list = []
        for i in data['Members']:
            for ii in i.items():
                controller = ii[1].split("/")[-1]
                controller_list.append(controller)
                print(controller)

def get_storage_controller_details(script_examples="", controller_fqdd=""):
    """Function to get details for a specific storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_controller_details(controller_fqdd='RAID.Integrated.1-1'), this example will return detailed information for storage controller RAID.Integrated.1-1")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        logging.info("\n - Detailed controller information for %s -\n" % controller_fqdd)
        for i in data.items():
            pprint(i)

def get_storage_disks(script_examples="", controller_fqdd=""):
    """Function to get drive FQDDs for storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_disks(controller_fqdd='RAID.Integrated.1-1'), this example will return disk FQDDs detected for storage controller RAID.Integrated.1-1")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        drive_list=[]
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        if data['Drives'] == []:
            logging.warning("\n- WARNING, no drives detected for %s" % controller_fqdd)
            return
        else:
            logging.info("\n- Drive(s) detected for %s -\n" % controller_fqdd)
            for i in data['Drives']:
                drive_list.append(i['@odata.id'].split("/")[-1])
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (creds["idrac_ip"], i['@odata.id'].split("/")[-1]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (creds["idrac_ip"], i['@odata.id'].split("/")[-1]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                data = response.json()
                if response.status_code != 200:
                    logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
                    return
                else:
                    print(i['@odata.id'].split("/")[-1])

def get_storage_disk_details(script_examples="", controller_fqdd=""):
    """Function to get detailed information for all drives detected behind storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_disk_details(controller_fqdd='RAID.Integrated.1-1'), this example will return detailed information for all disks behind storage controller RAID.Integrated.1-1")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        drive_list=[]
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        if data['Drives'] == []:
            logging.warning("\n- WARNING, no drives detected for %s" % controller_fqdd)
            return
        else:
            logging.info("\n- Drive(s) detected for %s -\n" % controller_fqdd)
            for i in data['Drives']:
                drive_list.append(i['@odata.id'].split("/")[-1])
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (creds["idrac_ip"], i['@odata.id'].split("/")[-1]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (creds["idrac_ip"], i['@odata.id'].split("/")[-1]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                data = response.json()
                if response.status_code != 200:
                    logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
                    return
                else:
                    print("\n----- %s drive details -----\n" % i['@odata.id'].split("/")[-1]) 
                    pprint(data)

def get_storage_enclosures(script_examples=""):
    """Function to get server storage enclosure(s)"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_enclosures(), this example will return all server storage enclosures detected.")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Chassis' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Chassis' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        backplane_uris = []
        if len(data['Members']) == 1:
            logging.error("\n- ERROR, no backplanes detected for server. Either backplane type not supported to get data and server has no backplane")
            return
        logging.info("\n - Backplane URIs detected for server -\n")
        for i in data['Members']:
            for ii in i.items():
                if ii[1] != '/redfish/v1/Chassis/System.Embedded.1':
                    print(ii[1])
                    backplane_uris.append(ii[1])
        for i in backplane_uris:
            if x_auth_token == "yes":
                response = requests.get('https://%s%s' % (creds["idrac_ip"], i),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})
            else:
                response = requests.get('https://%s%s' % (creds["idrac_ip"], i),verify=False,auth=(creds["idrac_username"], creds["idrac_password"]))
            logging.info("\n----- Detailed information for URI \"%s\" -----\n" % i)
            data = response.json()
            if response.status_code != 200:
                logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
                return
            for ii in data.items():
                pprint(ii)

def get_virtual_disks(script_examples="", controller_fqdd=""):
    """Function to get virtual disk FQDDs for storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_virtual_disks(controller_fqdd='RAID.SL.3-1'), this example will return all virtual disks detected for controller RAID.SL.3-1")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        vd_list=[]
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- ERROR, status code %s returned. Check to make sure you passed in correct controller FQDD string for argument value" % response.status_code)
            return
        elif data['Members'] == []:
            logging.warning("\n- WARNING, no volume(s) detected for %s" % controller_fqdd)
            return
        else:
            for i in data['Members']:
                vd_list.append(i['@odata.id'].split("/")[-1])
        logging.info("\n- Volume(s) detected for %s controller -\n" % controller_fqdd)
        for ii in vd_list:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], ii),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], ii),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            try:
                print("%s, Volume type: %s, RAID type: %s" % (ii, data["VolumeType"], data["RAIDType"]))
            except:
                print("%s, Volume type: %s" % (ii, data["VolumeType"]))

def get_virtual_disk_details(script_examples="", controller_fqdd=""):
    """Function to get details for all virtual disks behind storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_virtual_disks(controller_fqdd='RAID.SL.3-1'), this example will return detailed virtual disk information for all VDs detected behind controller RAID.SL.3-1")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        vd_list=[]
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- ERROR, status code %s returned. Check to make sure you passed in correct controller FQDD string for argument value" % response.status_code)
            return
        elif data['Members'] == []:
            logging.warning("\n- WARNING, no volume(s) detected for %s" % controller_fqdd)
            return
        else:
            logging.info("\n- Volume(s) detected for %s controller -\n" % controller_fqdd)
            for i in data['Members']:
                vd_list.append(i['@odata.id'].split("/")[-1])
                print(i['@odata.id'].split("/")[-1])
        for ii in vd_list:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], ii),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], ii),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code != 200:
                logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
                return
            print("\n----- Detailed Volume information for %s -----\n" % ii)
            for i in data.items():
                pprint(i)

def reset_controller(script_examples="", controller_fqdd=""):
    """Function to reset the storage controller which will delete all virtual disks. Supported function argument: controller_fqdd"""
    global job_id
    if script_examples:
        print("\n- IdracRedfishSupport.reset_controller(controller_fqdd='RAID.SL.3-1'), this example will reset controller RAID.SL.3-1")
    else:
        payload={"TargetFQDD": controller_fqdd}
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ResetConfig' % (creds["idrac_ip"])
        method = "ResetConfig"
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to reset storage controller %s, status code %s returned" % (controller_fqdd, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- ERROR, unable to locate job ID in JSON headers output")
                return
            logging.info("- INFO, Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
        else:
            logging.error("\n- ERROR, POST command failed to reset storage controller %s, status code is %s" % (controller_fqdd, response.status_code))
            data = response.json()
            logging.info("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()

def change_virtual_disk_attributes(script_examples="", vd_fqdd="", diskcachepolicy="", readcachepolicy="", writecachepolicy=""):
    """Function to change virtual disk attributes. Supported function arguments: vd_fqdd (possible value: VD FQDD), diskcachepolicy (possible values: Enabled and Disabled), readcachepolicy (Off, ReadAhead and AdaptiveReadAhead), writecachepolicy (ProtectedWriteBack, UnprotectedWriteBack and WriteThrough)."""
    global job_id
    if script_examples:
        print("\n- IdracRedfishSupport.change_virtual_disk_attributes(vd_fqdd=\"Disk.Virtual.3:RAID.Mezzanine.1-1\", diskcachepolicy=\"Disabled\",writecachepolicy=\"UnprotectedWriteBack\",readcachepolicy=\"Off\"), this example shows changing VD disk, read and write cache policy attributes.")
    else:
        payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
        if diskcachepolicy:
            payload["Oem"]={"Dell":{"DellVolume":{"DiskCachePolicy": diskcachepolicy}}}
        if readcachepolicy:
            payload["ReadCachePolicy"] = readcachepolicy
        if writecachepolicy:
            payload["WriteCachePolicy"] = writecachepolicy
        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes/%s/Settings" % (creds["idrac_ip"], vd_fqdd.split(":")[-1], vd_fqdd)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: PATCH command passed to change VD attributes, status code %s returned" % response.status_code)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- ERROR, unable to locate job ID in JSON headers output")
                return
            logging.info("- INFO, Job ID %s successfully created" % job_id)
        else:
            logging.error("\n- ERROR, PATCH command failed to change VD attributes, status code %s returned" % response.status_code)
            data = response.json()
            logging.info("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code != 200:
            logging.error("- ERROR, GET command failed, detailed error information: %s" % data)
            return
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def loop_job_status_final():
    """Function to loop checking final job status, this function cannot be called individually and is leveraged only by other functions after POST action is executed to create a job ID"""
    start_time = datetime.now()
    while True:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        current_time=(datetime.now()-start_time)
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- ERROR, Command failed to check job status, return code is %s" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- ERROR: Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- ERROR, job ID %s failed, final job status message: %s" % (job_id, data['Message']))
            logging.info("- INFO, check iDRAC Lifecycle Logs for more details about the job failure")
            return
        elif "Lifecycle Controller in use" in data["Message"]:
            logging.warning("- WARNING, Lifecycle Controller in use detected, job will start when Lifecycle Controller is available. Check server state to make sure it is out of POST and iDRAC job queue to confirm no jobs are already executing.")
            return
        elif data['JobState'] == "Completed":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % (data['Message'].strip(".")))
            time.sleep(3)
            
def create_virtual_disk(script_examples="", controller_fqdd="", disk_fqdds="", raid_level="", vd_name="", vd_size="", vd_stripesize="", secure="", diskcachepolicy="", readcachepolicy="", writecachepolicy=""):
    """Function to create virtual disk. Function arguments: controller_fqdd, disk_fqdds (if you\'re passing in multiple drives for VD creation, pass them in as a list), raid_level, supported integer values: 0, 1, 5, 6, 10, 50 and 60 (not all RAID levels are supported on each storage contoller), vd_name is optional (if not passed in, controller will set using default name), vd_size is optional (integer value in bytes) and if not passed in VD creation will use the full disk size, vd_stripesize is optional (integer value in bytes) and if not passed in controller will assign the default stripesize for the RAID level, secure is optional (pass in value of True to secure the VD during VD creation), diskcachepolicy is optional (possible values: Enabled and Disabled), readcachepolicy is optional (Off, ReadAhead and AdaptiveReadAhead), writecachepolicy (ProtectedWriteBack, UnprotectedWriteBack and WriteThrough)."""
    global job_id
    global job_type
    if script_examples:
        print("""\n- IdracRedfishSupport.create_virtual_disk(controller_fqdd="RAID.Mezzanine.1-1", disk_fqdds="Disk.Bay.13:Enclosure.Internal.0-1:RAID.Mezzanine.1-1", raid_level=0, vd_name="RAID_ZERO", vd_size=107374182400, vd_stripesize=131072), this example will create 100GB RAID 0 with stripesize 128KB
        \n- IdracRedfishSupport.create_virtual_disk(controller_fqdd="RAID.Mezzanine.1-1", disk_fqdds=["Disk.Bay.19:Enclosure.Internal.0-1:RAID.Mezzanine.1-1","Disk.Bay.20:Enclosure.Internal.0-1:RAID.Mezzanine.1-1"],raid_level=1), this example will create RAID 1 using full disk size""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code != 200:
            logging.error("\n- ERROR, GET command failed, status code %s returned" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (creds["idrac_ip"], controller_fqdd)
        data = response.json()
        get_version = data['FirmwareVersion'].split(".")[:2]
        get_version = int("".join(get_version))
        final_disks_list=[]
        if get_version < 440:
            raid_levels={0:"NonRedundant",1:"Mirrored",5:"StripedWithParity",10:"SpannedMirrors",50:"SpannedStripesWithParity"}
            try:
                volume_type = raid_levels[raid_level]
            except:
                logging.error("\n- ERROR, invalid RAID level value entered")
                return
        elif get_version >= 440:
            raid_levels={0:"RAID0",1:"RAID1",5:"RAID5",6:"RAID6",10:"RAID10",50:"RAID50",60:"RAID60"}
            try:
                volume_type = raid_levels[raid_level]
            except:
                logging.error("\n- ERROR, invalid RAID level value entered")
                return
        if type(disk_fqdds) == list:
            for i in disk_fqdds:
                uri_string = "/redfish/v1/Systems/System.Embedded.1/Storage/Drives/" + i
                create_dict = {"@odata.id":uri_string}
                final_disks_list.append(create_dict)
        else:
            uri_string = "/redfish/v1/Systems/System.Embedded.1/Storage/Drives/" + disk_fqdds
            create_dict = {"@odata.id":uri_string}
            final_disks_list.append(create_dict)
        if get_version < 440:
            payload = {"VolumeType":volume_type,"Drives":final_disks_list}
        elif get_version >= 440:
            payload = {"RAIDType":volume_type,"Drives":final_disks_list}
        if vd_size:
            payload["CapacityBytes"] = vd_size
        if vd_stripesize:
            payload["OptimumIOSizeBytes"] = vd_stripesize
        if vd_name:
            payload["Name"] = vd_name
        if secure:
            payload["Encrypted"] = True
        if diskcachepolicy:
            payload["Oem"]={"Dell":{"DellVolume":{"DiskCachePolicy": diskcachepolicy}}}
        if readcachepolicy:
            payload["ReadCachePolicy"] = readcachepolicy
        if writecachepolicy:
            payload["WriteCachePolicy"] = writecachepolicy
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to create \"%s\" virtual disk, status code 202 returned" % volume_type)
            time.sleep(5)
        else:
            logging.error("\n- ERROR, POST command failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.info("\n- POST command failure:\n %s" % data)
            return
        get_header_location = response.headers["Location"]
        try:
            job_id = get_header_location.split("/")[-1]
        except:
            logging.error("\n- ERROR, unable to locate job ID in the headers response, check job queue if job ID was created.")
            return
            
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
        logging.info("\n- PASS, \"%s\" %s job ID successfully created" % (job_type, job_id))

        if job_type == "staged":
            logging.info("- INFO, staged config job detected, server will validate scheduled job status before rebooting the server")
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except requests.ConnectionError as error_message:
                    print(error_message)
                    return
                statusCode = response.status_code
                if statusCode != 200:
                    logging.error("\n- ERROR, Command failed to check job status, return code is %s" % statusCode)
                    logging.info("Extended Info Message: {0}".format(req.json()))
                    return
                time.sleep(5)
                data = response.json()
                if data['Message'] == "Task successfully scheduled.":
                    logging.info("- INFO, staged config job marked as scheduled")
                    user_response = input(str("- INFO, job ID marked as scheduled, would you like to reboot the server now to execute the job? Pass in \"y\" to reboot now or \"n\" to not reboot the server now: "))
                    if user_response.lower() == "y":
                        logging.info("- INFO, user selected to reboot the server now to execute the config job")
                        reboot_server()
                        loop_job_status_final()
                        break
                    if user_response.lower() == "n":
                        logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                        break
                else:
                    print("- INFO: JobStatus not scheduled, current status: %s\n" % data['Message'])
        if job_type == "realtime":
            logging.info("- INFO, realtime config job detected, no reboot needed to create the VD")
            loop_job_status_final()
        

def reboot_server():
    """Function to reboot the server to execute configuration or updates jobs that require server reboot to apply. This function cannot be called directly and will be called by other functions after POST action is executed to create a job ID"""
    if x_auth_token == "yes":
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
    data = response.json()
    logging.info("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % creds["idrac_ip"]
        payload = {'ResetType': 'GracefulShutdown'}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 204:
            logging.info("- PASS, POST action passed to gracefully power OFF server")
            time.sleep(10)
        else:
            logging.error("\n- ERROR, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
        count = 0
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify server is in OFF state")
                break
            elif count == 20:
                logging.info("- INFO, unable to graceful shutdown the server, will perform forced shutdown now")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % creds["idrac_ip"]
                payload = {'ResetType': 'ForceOff'}
                if x_auth_token == "yes":
                    headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
                if response.status_code == 204:
                    logging.info("- PASS, POST action passed to forcefully power OFF server")
                    time.sleep(15)
                    break
                else:
                    logging.error("\n- ERROR, Command failed to gracefully power OFF server, status code: %s\n" % response.status_code)
                    logging.info("Extended Info Message: {0}".format(response.json()))
                    return
            else:
                time.sleep(2)
                count+=1
                continue
        payload = {'ResetType': 'On'}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 204:
            logging.info("- PASS, POST action passed to power ON server")
        else:
            logging.error("\n- ERROR, POST action failed to power ON server, status code is: %s\n" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % creds["idrac_ip"]
        payload = {'ResetType': 'On'}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 204:
            logging.info("- PASS, POST action passed to power ON server")
        else:
            logging.error("\n- ERROR, Command failed to power ON server, status code: %s\n" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
    else:
        logging.error("- ERROR, unable to get current server power state to perform either reboot or power on")
        return


def get_current_server_power_state(script_examples=""):
    """Function to get current server power state and supported possible values for changing server power state"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_current_server_power_state(), this example will get current server power state and possible supported values for executing set_server_power_state()")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- ERROR, GET command failed, status code %s returned" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
        logging.info("\n- INFO, Current server power state: %s\n" % data['PowerState'])
        logging.info("- Supported values to change server power state:\n")
        for i in data['Actions']['#ComputerSystem.Reset']['ResetType@Redfish.AllowableValues']:
            print(i)


def set_server_power_state(script_examples="", power_state_value=""):
    """Function to change server power state to perform power operations. Supported function argument: power_state_value (supported values: execute "IdracRedfishSupport.get_current_server_power_state()" to get supported possible values)"""
    if script_examples:
        print("""\n- IdracRedfishSupport.set_server_power_state(power_state_value="ForceOff"), this example will set server power state to ForceOff (force shutdown the server to off state).
        \n- IdracRedfishSupport.set_server_power_state(power_state_value="GracefulRestart"), this example will set server power state to GracefulRestart (graceful shutdown of the server and reboot)""")
    else:
        logging.info("\n- INFO, setting new server power state value: %s" % (power_state_value))
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % creds["idrac_ip"]
        payload = {'ResetType': power_state_value}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 204:
            logging.info("\n- PASS, status code %s returned, server power state successfully set to \"%s\"\n" % (response.status_code, power_state_value))
        else:
            logging.error("\n- ERROR, POST command failed for action ComputerSystem.Reset, status code %s returned\n" % response.status_code)
            print(response.json())
            return


def get_remote_service_api_status(script_examples=""):
    """Function to get the server remote services status. This will return: lifecycle controller(LC) status, real time monitoring (RT) status, overall server status, Telemetry status(if supported) and overall status."""
    if script_examples:
        print("\n- IdracRedfishSupport.get_remote_service_api_status(), this example will return LC, RT, server and Telemetry status.")
    else:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (creds["idrac_ip"])
        method = "GetRemoteServicesAPIStatus"
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data=response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code 200 returned\n" % method)
        else:
            logging.error("\n- ERROR, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.info("\n- POST command failure results:\n %s" % data)
            return
        for i in data.items():
            if i[0] != "@Message.ExtendedInfo":
                print("%s: %s" % (i[0], i[1]))

def delete_virtual_disk(script_examples="", virtual_disk_fqdd=""):
    """Function to delete storage controller virtual disk. Supported function argument: virtual_disk_fqdd (pass in virtual disk FQDD string)"""
    global job_id
    global job_type
    if script_examples:
        print("\n- IdracRedfishSupport.delete_virtual_disk(virtual_disk_fqdd='Disk.Virtual.1:RAID.Mezzanine.1-1'), this example will delete VD 1 for controller RAID.Mezzanine.1-1")
    else:
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], virtual_disk_fqdd)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: DELETE command passed to delete \"%s\" virtual disk, status code 202 returned" % virtual_disk_fqdd)
            time.sleep(5)
        else:
            logging.error("\n- ERROR, DELETE command failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.info("\n- DELETE command failure:\n %s" % data)
            return
        get_header_location = response.headers["Location"]
        try:
            job_id = get_header_location.split("/")[-1]
        except:
            logging.error("\n- ERROR, unable to locate job ID in the headers response, check job queue if job ID was created.")
            return          
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
        print("\n- PASS, \"%s\" %s jid successfully created to delete virtual disk" % (job_type, job_id))

        if job_type == "staged":
            print("- INFO, staged config job detected, server will validate scheduled job status before rebooting the server")
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except requests.ConnectionError as error_message:
                    logging.error(error_message)
                    return
                if response.status_code != 200:
                    logging.error("\n- ERROR, GET command failed to check job status, status code %s returned" % response.status_code)
                    logging.info("Extended Info Message: {0}".format(req.json()))
                    return
                time.sleep(5)
                data = response.json()
                if data['Message'] == "Task successfully scheduled.":
                    logging.info("- INFO, staged config job marked as scheduled")
                    user_response = input(str("- INFO, job ID marked as scheduled, would you like to reboot the server now to execute the job? Pass in \"y\" to reboot now or \"n\" to not reboot the server now: "))
                    if user_response.lower() == "y":
                        logging.info("- INFO, user selected to reboot the server now to execute the config job")
                        reboot_server()
                        loop_job_status_final()
                        break
                    if user_response.lower() == "n":
                        logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                        break
                else:
                    logging.info("- INFO: job status not marked as scheduled, current status: %s\n" % data['Message'])
        if job_type == "realtime":
            logging.info("- INFO, realtime config job detected, no reboot needed to execute storage operation")
            loop_job_status_final()


def initialize_virtual_disk(script_examples="", virtual_disk_fqdd="", init_type=""):
    """Function to initialize virtual disk. Supported function arguments: virtual_disk_fqdd and init_type (supported values: Fast and Slow)."""
    global job_id
    global job_type
    if script_examples:
        print("\n- IdracRedfishSupport.initialize_virtual_disk(virtual_disk_fqdd='Disk.Virtual.1:RAID.Mezzanine.1-1', init_type='Fast'), this example will run fast init on virtual disk 1.")
    else:
        controller = virtual_disk_fqdd.split(":")[-1]
        payload={"InitializeType":init_type}
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes/%s/Actions/Volume.Initialize' % (creds["idrac_ip"], controller, virtual_disk_fqdd)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to initialize \"%s\" virtual disk, status code 202 returned" % virtual_disk_fqdd)
            time.sleep(5)
        else:
            logging.error("\n- ERROR, POST command failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error("\n- POST command failure:\n %s" % data)
            return
        get_header_location = response.headers["Location"]
        try:
            job_id = get_header_location.split("/")[-1]
        except:
            logging.error("\n- ERROR, unable to locate job ID in the headers response, check job queue if job ID was created.")
            return   
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
        logging.info("\n- PASS, \"%s\" %s job ID successfully created" % (job_type, job_id))

        if job_type == "staged":
            logging.info("- INFO, staged config job detected, server will validate scheduled job status before rebooting the server")
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except requests.ConnectionError as error_message:
                    logging.error(error_message)
                    return
                if response.status_code != 200:
                    logging.error("\n- ERROR, GET command failed to check job status, return code %s" % response.status_code)
                    logging.error("Extended Info Message: {0}".format(req.json()))
                    return
                time.sleep(5)
                data = response.json()
                if data['Message'] == "Task successfully scheduled.":
                    logging.info("- INFO, staged config job marked as scheduled")
                    user_response = input(str("- INFO, job ID marked as scheduled, would you like to reboot the server now to execute the job? Pass in \"y\" to reboot now or \"n\" to not reboot the server now: "))
                    if user_response.lower() == "y":
                        logging.info("- INFO, user selected to reboot the server now to execute the config job")
                        reboot_server()
                        loop_job_status_final()
                        break
                    if user_response.lower() == "n":
                        logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                        break
                else:
                    logging.info("- INFO: job status not scheduled, current status: %s\n" % data['Message'])
        if job_type == "realtime":
            logging.info("- INFO, realtime config job detected, no reboot needed to execute storage operation")
            loop_job_status_final()


def secure_erase_disk(script_examples="", controller_fqdd="", disk_fqdd=""):
    """Function to secure erase (cryptographic erase) disk (HDD/SSD or NVMe type), supported function arguments: controller_fqdd and disk_fqdd. Note: Disk must not be part of a virtual disk for secure erase to pass."""
    global job_id
    global job_type
    if script_examples:
        print("\n- IdracRedfishSupport.secure_erase_disk(controller_fqdd='RAID.Mezzanine.1-1', disk_fqdd='Disk.Bay.0:Enclosure.Internal.0-1:RAID.Mezzanine.1-1'), this example will secure erase disk 0 behind storage controller RAID.Mezzanine.1-1")
    else:
        payload={}
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Drives/%s/Actions/Drive.SecureErase' % (creds["idrac_ip"], controller_fqdd, disk_fqdd)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to secure erase disk \"%s\", status code 202 returned" % disk_fqdd)
            time.sleep(5)
        else:
            logging.error("\n- ERROR, POST command failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error("\n- POST command failure:\n %s" % data)
            return
        get_header_location = response.headers["Location"]
        try:
            job_id = get_header_location.split("/")[-1]
        except:
            logging.error("\n- ERROR, unable to locate job ID in the headers response, check job queue if job ID was created.")
            return    
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
        logging.info("\n- PASS, \"%s\" %s job ID successfully created" % (job_type, job_id))
        if job_type == "staged":
            logging.info("- INFO, staged config job detected, server will validate scheduled job status before rebooting the server")
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except requests.ConnectionError as error_message:
                    logging.error(error_message)
                    return
                if response.status_code != 200:
                    logging.error("\n- ERROR, GET command failed to check job status, return code is %s" % response.status_code)
                    logging.error("Extended Info Message: {0}".format(req.json()))
                    return
                time.sleep(5)
                data = response.json()
                if data['Message'] == "Task successfully scheduled.":
                    logging.info("- INFO, staged config job marked as scheduled")
                    user_response = input(str("- INFO, job ID marked as scheduled, would you like to reboot the server now to execute the job? Pass in \"y\" to reboot now or \"n\" to not reboot the server now: "))
                    if user_response.lower() == "y":
                        logging.info("- INFO, user selected to reboot the server now to execute the config job")
                        reboot_server()
                        loop_job_status_final()
                        break
                    if user_response.lower() == "n":
                        logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                        break
                else:
                    print("- INFO: JobStatus not scheduled, current status: %s\n" % data['Message'])
        if job_type == "realtime":
            logging.info("- INFO, realtime config job detected, no reboot needed to execute storage operation")
            loop_job_status_final()

def assign_disk_hotspare(script_examples="", hotspare_type="", disk_fqdd="", virtual_disk_fqdd="default"):
    """Function to assign disk hotspare, global or dedicated. Supported function arguments: hotspare_type (supported values are dedicated or global), disk_fqdd and virtual_disk_fqdd (only required if assigning dedicated hotspare)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.assign_disk_hotspare(hotspare_type="global", disk_fqdd="Disk.Bay.6:Enclosure.Internal.0-1:RAID.Mezzanine.1-1"), this example will assign disk 6 as global hotspare.
        \n- IdracRedfishSupport.assign_disk_hotspare(hotspare_type="dedicated", disk_fqdd="Disk.Bay.6:Enclosure.Internal.0-1:RAID.Mezzanine.1-1"), virtual_disk_fqdd="Disk.Virtual.0:RAID.Mezzanine.1-1"), this example will assign disk 6 as dedicated hotspare for RAID 1 virtual disk 0.""")
    else:
        method = "AssignSpare"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.AssignSpare' % (creds["idrac_ip"])
        if hotspare_type.lower() == "global":
            payload={"TargetFQDD":disk_fqdd}
        elif hotspare_type.lower() == "dedicated":
            payload={"TargetFQDD":disk_fqdd,"VirtualDiskArray":[virtual_disk_fqdd]}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to set disk \"%s\" as \"%s\" hot spare" % (disk_fqdd, hotspare_type))
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method))
        else:
            logging.error("\n- FAIL, POST command failed to set disk %s as %s hot spare" % (disk_fqdd, hotspare_type))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def unassign_disk_hotspare(script_examples="", disk_fqdd=""):
    """Function to unassign disk hotspare. Supported function argument: disk_fqdd."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.unassign_disk_hotspare(disk_fqdd="Disk.Bay.6:Enclosure.Internal.0-1:RAID.Mezzanine.1-1"), this example will unassign disk 6 as a hotspare.""")
    else:
        method = "UnassignSpare"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.UnassignSpare' % (creds["idrac_ip"])
        payload={"TargetFQDD":disk_fqdd}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to unassign disk \"%s\" as hotspare" % (disk_fqdd))
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                print("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method))
        else:
            logging.error("\n- FAIL, POST command failed to unassign disk \"%s\" as hot spare" % (disk_fqdd))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def set_storage_controller_key(script_examples="", controller_fqdd="", key_id=""):
    """Function to set the storage controller key \"enable encryption\" for Local Key Management (LKM). Supported function arguments: controller_fqdd and key_id (unique string value). Once function is executed, it will prompt you to enter key passphrase to set (minimum length is 8 characters, must have at least 1 upper and 1 lowercase, 1 number and 1 special character. Refer to Dell PERC documentation for more information)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.set_storage_controller_key(controller_fqdd="RAID.Mezzanine.1-1", key_id="testkey"), this example will set controller LKM encryption. Script will prompt you to enter new passphrase.""")
    else:
        method = "SetControllerKey"
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['Oem']['Dell']['DellController']['SecurityStatus'] == "EncryptionNotCapable":
            logging.warning("\n- WARNING, storage controller %s does not support encryption" % controller_fqdd)
            return
        else:
            pass
        key_passphrase = getpass.getpass("- Enter new key passphrase to set: ")
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.SetControllerKey' % (creds["idrac_ip"])
        payload={"TargetFQDD":controller_fqdd,"Key":key_passphrase,"Keyid":key_id}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to set the controller key for controller %s" % controller_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                print("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            logging.error("\n- FAIL, POST command failed to set the controller key for controller %s" % controller_fqdd)
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()

def rekey_storage_controller_key(script_examples="", controller_fqdd="", encryption_mode="", key_id="default"):
    """Function to rekey storage controller key (Local Key Management (LKM) or Secure Enterprise Key Manager (SEKM). Supported function arguments: controller_fqdd, encryption_mode (supported values are SEKM or LKM) and key_id (only supported for LKM, you can pass in either current string value set or change to a new string value). If LKM rekey is being performed, function will prompt you to enter current key passphrase, then set new key passphrase."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.rekey_storage_controller_key(controller_fqdd="RAID.Mezzanine.1-1", encryption_mode="LKM", key_id="newkey"), this example will rekey controller key for RAID.Mezzanine.1-1. It will prompt user to enter current passphrase and new passphrase.""")
    else:
        method = "ReKey"
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        current_key_id = data["Oem"]["Dell"]["DellController"]["KeyID"]
        if data['Oem']['Dell']['DellController']['SecurityStatus'] == "EncryptionNotCapable":
            logging.warning("\n- WARNING, storage controller %s does not support encryption" % controller_fqdd)
            return
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ReKey' % (creds["idrac_ip"])
        if encryption_mode.upper() == "LKM":
            old_key_passphrase = getpass.getpass("- Enter current key passphrase: ")
            new_key_passphrase = getpass.getpass("- Enter new key passphrase to set: ")
            if key_id == "default":
                payload={"Mode":"LKM","TargetFQDD":controller_fqdd,"OldKey":old_key_passphrase,"NewKey":new_key_passphrase,"Keyid":current_key_id}
            else:
                payload={"Mode":"LKM","TargetFQDD":controller_fqdd,"OldKey":old_key_passphrase,"NewKey":new_key_passphrase,"Keyid":key_id}
        elif encryption_mode.upper() == "SEKM":
            payload={"Mode":"SEKM","TargetFQDD":controller_fqdd}
        else:
            logging.error("- FAIL, invalid value or missing value for encryption_mode argument")
            return
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to rekey the controller for %s" % controller_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            logging.error("\n- FAIL, POST command failed to set the controller key for controller %s" % controller_fqdd)
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def remove_storage_controller_key(script_examples="", controller_fqdd=""):
    """Function to remove storage controller key for Local Key Management (LKM) configured. Supported function argument: controller_fqdd."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.remove_storage_controller_key(controller_fqdd="RAID.Mezzanine.1-1"), this example will remove controller key for RAID.Mezzanine.1-1.""")
    else:
        method = "RemoveControllerKey"
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['Oem']['Dell']['DellController']['SecurityStatus'] == "EncryptionNotCapable":
            print("\n- WARNING, storage controller %s does not support encryption" % controller_fqdd)
            return
        else:
            pass
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.RemoveControllerKey' % (creds["idrac_ip"])
        payload={"TargetFQDD":controller_fqdd}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            print("\n- PASS: POST command passed to remove controller key for controller %s" % controller_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                print("- FAIL, unable to locate job ID in JSON headers output")
                return
            print("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            print("\n- FAIL, POST command failed to remove controller key for controller %s" % controller_fqdd)
            data = response.json()
            print("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            print("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            print("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()

def check_consistency_virtual_disk(script_examples="", virtual_disk_fqdd=""):
    """Function to check consitency for a virtual disk. Supported function argument: virtual_disk_fqdd."""
    global job_id
    global job_type
    if script_examples:
        print("""\n- IdracRedfishSupport.check_consistency_virtual_disk(virtual_disk_fqdd="Disk.Virtual.0:RAID.Mezzanine.1-1"), this example will check consistency for virtual disk 0.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], virtual_disk_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (creds["idrac_ip"], virtual_disk_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        payload = {}
        for i in data.items():
            if i[0] == "Operations":
                if i[1] != []:
                    for ii in i[1]:
                        logging.error("\n- FAIL, Unable to run Check Consistency due to operation already executing on VD. Current operation executing: %s, PrecentComplete %s" % (ii['OperationName'],ii['PercentageComplete']))
                        return
        controller_fqdd = virtual_disk_fqdd.split(":")[-1]
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes/%s/Actions/Volume.CheckConsistency' % (creds["idrac_ip"], controller_fqdd,virtual_disk_fqdd)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to check consistency for virtual disk %s, status code 202 returned" % (virtual_disk_fqdd))
            time.sleep(5)
        else:
            logging.error("\n- FAIL, POST command failed, status code is %s" % response.status_code)
            data = response.json()
            logging.error("\n- POST command failure:\n %s" % data)
            return
        get_header_location = response.headers["Location"]
        try:
            job_id = get_header_location.split("/")[-1]
        except:
            logging.error("\n- FAIL, unable to locate job ID in the headers response, check job queue if job ID was created.")
            return   
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
        logging.info("\n- PASS, \"%s\" %s job ID successfully created" % (job_type, job_id))
        if job_type == "staged":
            logging.info("- INFO, staged config job detected, server will validate scheduled job status before rebooting the server")
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except requests.ConnectionError as error_message:
                    logging.error(error_message)
                    return
                if response.status_code != 200:
                    logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                    logging.error("Extended Info Message: {0}".format(req.json()))
                    return
                time.sleep(5)
                data = response.json()
                if data['Message'] == "Task successfully scheduled.":
                    logging.info("- INFO, staged config job marked as scheduled")
                    user_response = input(str("- INFO, job ID marked as scheduled, would you like to reboot the server now to execute the job? Pass in \"y\" to reboot now or \"n\" to not reboot the server now: "))
                    if user_response.lower() == "y":
                        logging.info("- INFO, user selected to reboot the server now to execute the config job")
                        reboot_server()
                        loop_job_status_final()
                        logging.info("\n- INFO, check iDRAC Lifecycle Logs for more details on check consistency process, if any errors were found")
                        break
                    if user_response.lower() == "n":
                        logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                        break
                else:
                    logging.info("- INFO: job status not marked as scheduled, current status: %s\n" % data['Message'])
        if job_type == "realtime":
            logging.info("- INFO, realtime config job detected, no reboot needed to execute storage operation")
            loop_job_status_final()
            logging.info("\n- INFO, check iDRAC Lifecycle Logs for more details on check consistency process, if any errors were found")

def secure_virtual_disk(script_examples="", virtual_disk_fqdd=""):
    """Function to secure virtual disk (disks part of the virtual disk must be encryption capable (SED). Supported function argument: virtual disk FQDD."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.secure_virtual_disk(virtual_disk_fqdd="Disk.Virtual.0:RAID.Mezzanine.1-1"), this example will secure virtual disk 0.""")
    else:
        method = "SecureVirtualDisk"
        controller_fqdd = virtual_disk_fqdd.split(":")[-1]
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (creds["idrac_ip"], controller_fqdd),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['Oem']['Dell']['DellController']['SecurityStatus'] == "EncryptionNotCapable":
            logging.warning("\n- WARNING, storage controller %s does not support encryption" % controller_fqdd)
            return
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.LockVirtualDisk' % (creds["idrac_ip"])
        payload={"TargetFQDD":virtual_disk_fqdd}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to secure virtual disk %s" % virtual_disk_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            logging.error("\n- FAIL, POST command failed to secure virtual disk %s" % virtual_disk_fqdd)
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def set_controller_boot_virtual_disk(script_examples="", controller_fqdd="", virtual_disk_fqdd=""):
    """Function to set controller boot virtual disk. Supported function arguments: controller_fqdd and virtual_disk_fqdd"""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.set_controller_boot_virtual_disk(controller_fqdd="RAID.Mezzanine.1-1",virtual_disk_fqdd="Disk.Virtual.2:RAID.Mezzanine.1-1"), this example will set VD 2 as controller boot virtual disk.""")
    else:
        method = "SetBootVD"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.SetBootVD' % (creds["idrac_ip"])
        payload={"ControllerFQDD":controller_fqdd, "VirtualDiskFQDD":virtual_disk_fqdd}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to set boot virtual disk %s" % virtual_disk_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            logging.error("\n- FAIL, POST command failed to set boot virtual disk %s" % virtual_disk_fqdd)
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()

def rename_virtual_disk(script_examples="", virtual_disk_fqdd="", vd_name=""):
    """Function to rename virtual disk. Supported function arguments: virtual_disk_fqdd and vd_name."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.rename_virtual_disk(virtual_disk_fqdd="Disk.Virtual.0:RAID.Mezzanine.1-1", vd_name="RAID0_Win2019"), this example will rename VD 0 to RAID0_Win2019""")
    else:
        method = "RenameVD"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.RenameVD' % (creds["idrac_ip"])
        payload={"TargetFQDD":virtual_disk_fqdd, "Name":vd_name}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to rename boot virtual disk %s" % virtual_disk_fqdd)
            time.sleep(5)
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
        else:
            logging.error("\n- FAIL, POST command failed to rename boot virtual disk %s" % virtual_disk_fqdd)
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()

def get_current_iDRAC_sessions(script_examples=""):
    """Function to get current active iDRAC sessions."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_current_iDRAC_sessions(), this example will return current active running iDRAC sessions.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/SessionService/Sessions?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/SessionService/Sessions?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- FAIL, status code %s returned, detailed error results:\n%s" % (response.status_code, data))
            return
        logging.info("\n- Current active iDRAC sessions -\n")
        controller_list=[]
        for i in data['Members']:
            pprint(i)
            print("\n")

def delete_iDRAC_session(script_examples="", session_id=""):
    """Function to delete one current iDRAC session. Supported function argument: session_id (pass in integer value of the session ID to delete. If needed, execute get_current_iDRAC_sessions() to get session IDs.)"""
    if script_examples:
        print("""\n- IdracRedfishSupport.delete_iDRAC_session(session_id=12), this example will delete current iDRAC session ID 12.""")
    else:
        url = 'https://%s/redfish/v1/SessionService/Sessions/%s' % (creds["idrac_ip"], str(session_id))
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: DELETE command passed to delete iDRAC session ID %s, status code %s returned" % (str(session_id), response.status_code))
        else:
            logging.error("\n- FAIL, DELETE command failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error("\n- DELETE command failure:\n %s" % data)
            return

def get_server_slot_information(script_examples=""):
    """Function to get server slot information. This includes PSUs, Fans, DIMMs, CPUs, IDSDM, vFlash, PCIe, and disks."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_server_slot_information(), this example will return slot details for all hardware devices detected in the server.""")
    else:
        try:
            os.remove("slot_collection.txt")
        except:
            pass
        open_file = open("slot_collection.txt","a")
        time_now = datetime.now()
        current_date_time = "- iDRAC IP %s, data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (creds["idrac_ip"], time_now.month, time_now.day, time_now.year, time_now.hour, time_now.minute, time_now.second)
        open_file.writelines(current_date_time)
        open_file.writelines("\n\n")
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- FAIL, status code %s returned, detailed error results:\n%s" % (response.status_code, data))
            return
        for i in data['Members']:
            pprint(i)
            open_file.writelines("%s\n" % i)
            print("\n")
            open_file.writelines("\n")
        number_list=[i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (creds["idrac_ip"], seq),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (creds["idrac_ip"], seq),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 400:
                if "out of range" in data['error']['@Message.ExtendedInfo'][0]['Message']:
                    break
                else:
                    logging.error("- FAIL, status code %s returned, detailed error results:\n%s" % (response.status_code, data))
                    return    
            elif response.status_code != 200:
                logging.error("- FAIL, status code %s returned, detailed error results:\n%s" % (response.status_code, data))
                return
            elif "Members" not in data:
                break
            for i in data['Members']:
                for ii in i.items():
                    slot_collection_entry = ("%s: %s" % (ii[0],ii[1]))
                    print(slot_collection_entry)
                    open_file.writelines("%s\n" % slot_collection_entry)
                print("\n")
                open_file.writelines("\n")
        logging.info("- INFO, slot collection information also captured in \"slot_collection.txt\" file")
        open_file.close()

def get_iDRAC_current_job_queue(script_examples=""):
    """Function to get current iDRAC job queue."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_iDRAC_current_job_queue(), this example will return current iDRAC job queue, all job IDs completed, running, scheduled or failed.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- FAIL, get request failed, status code %s returned" % response.status_code)
            data = response.json()
            print(data)
            return
        data = response.json()
        if data["Members"] == []:
            logging.info("\n- INFO, job queue empty. No job IDs or reboot IDs detected.")
            return
        logging.info("\n- Current job IDs in the job queue for iDRAC %s:\n" % creds["idrac_ip"])
        time.sleep(2)
        for i in data["Members"]:
            pprint(i)
            print("\n")

def delete_iDRAC_job_id_or_job_queue(script_examples="", job_id=""):
    """Function to either delete single job ID or clear the job queue. Supported function argument: job_id (pass in either job ID to delete single job or string \"clear\" to delete all jobs in the job queue. If needed, execute IdracRedfishSupport.get_iDRAC_current_job_queue() to get current iDRAC job queue."""
    if script_examples:
        print("""\n- IdracRedfishSupport.delete_iDRAC_job_id_or_job_queue(job_id="JID_292828393894"), this example will delete a single job ID.)
        \n- IdracRedfishSupport.delete_iDRAC_job_id_or_job_queue(job_id="clear"), this example will clear iDRAC job queue, all jobs will be deleted.""")
    else:
        url = "https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % creds["idrac_ip"]
        if job_id.lower() == "clear":
            payload = {"JobID":"JID_CLEARALL"}
            logging.info("- INFO, deleting the job queue, this may up to 1 minute to complete depending on the number of job ids")
        else:
            payload = {"JobID":job_id}    
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            if job_id.lower() == "clear":
                logging.info("- PASS: DeleteJobQueue action passed to delete all job IDs in the job queue")
            else:
                logging.info("- PASS: DeletjobQueue action passed to delete job ID %s" % job_id)
        else:
            logging.error("- FAIL, DeletjobQueue action failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error(data)
            return

def get_pcie_device_or_function_inventory(script_examples="", user_input=""):
    """Function to get either PCIe device or PCIe function inventory data. Supported function argument: user_input (supported values: "device" or "function")."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_pcie_device_or_function_inventory(user_input="device"), this example will return PCIe device information.
        \n- IdracRedfishSupport.get_pcie_device_or_function_inventory(user_input="function"), this example will return PCIe function information.""")
    else:
        if user_input.lower() == "device":
            user_input = "PCIeDevices"
        elif user_input.lower() == "function":
            user_input = "PCIeFunctions"
        else:
            logging.error("- WARNING, incorrect value entered for user_input argument")
            return
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- FAIL, get request failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error(data)
            return
        data = response.json()
        pcie_devices=[]
        try:
            os.remove("%s.txt" % user_input)
        except:
            pass
        open_file = open("%s.txt" % user_input,"a")
        for i in data[user_input]:
            for ii in i.items():
                print(ii[1])
                pcie_devices.append(ii[1])
        for i in pcie_devices:
            if x_auth_token == "yes":
                response = requests.get('https://%s%s' % (creds["idrac_ip"], i),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s%s' % (creds["idrac_ip"], i),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code != 200:
                logging.error("- FAIL, get request failed, status code %s returned" % response.status_code)
                data = response.json()
                logging.error(data)
                return
            data = response.json()
            open_file.writelines("\n")
            message = "\n----- URI \"%s\" details -----\n" % i
            logging.info(message)
            open_file.writelines(message)
            for ii in data.items():
                device = "%s: %s" % (ii[0], ii[1])
                pprint(ii)
                open_file.writelines("%s%s" % ("\n",device))
        open_file.close()
        logging.info("\n- Output also captured to file \"%s\"" % ("%s.txt" % user_input))

def reset_iDRAC(script_examples=""):
    """Function to reset (reboot) iDRAC. This will only reboot the iDRAC, it will not reset any iDRAC settings to default values."""
    if script_examples:
        print("""\n- IdracRedfishSupport.reset_iDRAC(), this example will reset(reboot) iDRAC.""")
    else:
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % creds["idrac_ip"]
        payload={"ResetType":"GracefulRestart"}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 204:
            logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC" % response.status_code)
        else:
            data=response.json()
            logging.error("\n- FAIL, status code %s returned, detailed error is: \n%s" % (response.status_code, data))
            return
        time.sleep(15)
        logging.info("- INFO, iDRAC will now reset and be back online within a few minutes.")

def set_idrac_default_settings(script_examples="", reset_type=""):
    """Function to reset iDRAC to default settings. Supported function argument: reset_type (supported values: "All"(Reset all iDRAC's configuration to default and reset user to shipping password value.), "ResetAllWithRootDefaults"(Reset all iDRAC's configuration to default and reset user to root\calvin) and "Default"(Reset all iDRAC's configuration to default and preserve user, network settings). Note: Make sure to pass in the exact case for the value. NOTE: If you execute this function to reset iDRAC to default settings, make sure to rerun IdracRedfishSupport.set_iDRAC_script_session() to set the session again."""
    if script_examples:
        print("""\n- IdracRedfishSupport.set_idrac_default_settings(reset_type="ResetAllWithRootDefaults"), this example will reset all iDRAC's configuration to default and reset user 2 to root\calvin credentials.""")
    else:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults' % creds["idrac_ip"]
        payload = {"ResetType": reset_type}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC to default settings using reset type \"%s\"" % (response.status_code, args["r"]))
        else:
            logging.error("\n- FAIL, status code %s returned, unable to reset iDRAC to default settings" % response.status_code)
            return
        time.sleep(15)
        logging.info("\n- iDRAC will now reset to default settings and restart the iDRAC. iDRAC should be back up within a few minutes.")

def get_message_registry(script_examples="", message_id=""):
    import os
    """Function to get complete iDRAC message registry which returns message IDs and message strings or a specific entry. Supported function argument: message_id."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_message_registry(), this example will return complete iDRAC message registry.
        \n- IdracRedfishSupport.get_message_registry(message_id="CPU0001"), this example will only return details for message ID CPU0001.""")
    elif message_id != "":
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("- FAIL, get request failed, status code %s returned" % response.status_code)
            data = response.json()
            logging.error(data)
            return
        for i in data['Messages'].items():
            if i[0].lower() == message_id.lower():
                logging.info("\n- Details for message ID %s -\n" % message_id)
                pprint(i)
                #print("\nMessage ID: %s" % i[0])
                #for ii in i[1].items():
                #    print("%s: %s" % (ii[0], ii[1]))
                #print("\n")
                return
            else:
                pass
        logging.error("\n - FAIL, either invalid message ID was passed in or message ID does not exist on this iDRAC version")
    else:
        try:
            os.remove("message_registry.txt")
        except:
            pass
        open_file = open("message_registry.txt","a")
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        for i in data['Messages'].items():
            message = "Message ID: %s" % i[0]
            pprint(i)
            print("\n")
            open_file.writelines("\n%s"% message)
            for ii in i[1].items():
                message = "%s: %s" % (ii[0], ii[1])
                open_file.writelines("\n%s"% message)
            message = "\n"
            open_file.writelines("%s"% message)
        open_file.close()
        current_dir = os.getcwd()
        logging.info("\n- INFO, output also captured in \"%s\\message_registry.txt\" file" % os.getcwd())


def change_bios_password(script_examples="", password_type="", set_password="", change_password="", delete_password="", reboot=""):
    """Function to set, change or delete BIOS passwords. Script will prompt you to enter password strings. Supported function arguments: password_type (supported values: SysPassword, SetupPassword, PersistentMemPassphrase), set_password (supported_value: True), change_password (supported_value: True), delete_password (supported_value: True) and reboot (supported values: yes and no)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.change_bios_password(password_type="SysPassword", set_password=True, reboot="yes"), this example will reboot the server now to set BIOS system password.).
        \n- IdracRedfishSupport.change_bios_password(password_type="SetupPassword", change_password=True, reboot="yes"), this example will reboot the server now to change BIOS setup password.
        \n- IdracRedfishSupport.change_bios_password(password_type="SetupPassword", delete_password=True, reboot="no"), this example will not reboot the server to delete BIOS setup password. Job is still scheduled and will execute on next server manual reboot.""")
    else:
        if password_type.lower() == "syspassword":
            password_name = "SysPassword"
        elif password_type.lower() == "setuppassword":
            password_name = "SetupPassword"
        elif password_type.lower() == "persistentmempassphrase":
            password_name = "PersistentMemPassphrase"
        else:
            logging.error("\n- FAIL, invalid value passed in for password_type argument")
            return
        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ChangePassword" % creds["idrac_ip"]
        if delete_password:
            current_password = getpass.getpass("- Enter current %s: " % password_type)
            payload = {"PasswordName":password_name,"OldPassword":current_password,"NewPassword":""}
            logging.info("\n- INFO, deleting BIOS %s" % password_name)
        elif set_password:
            new_password = getpass.getpass("- Enter new %s: " % password_type)
            payload = {"PasswordName":password_name,"NewPassword":new_password}
            logging.info("\n- INFO, setting new BIOS %s" % password_name)
        elif change_password:
            current_password = getpass.getpass("- Enter current %s: " % password_type)
            new_password = getpass.getpass("- Enter new %s: " % password_type)
            payload = {"PasswordName":password_name,"OldPassword":current_password,"NewPassword":new_password}
            logging.info("- INFO, changing BIOS %s" % password_name)
        else:
            logging.error("- FAIL, argument not detected to set, change or delete password")
            return
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.__dict__
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: status code %s returned for POST action Bios.ChangePassword" % response.status_code)
        else:
            logging.error("\n- FAIL, POST command failed to change password, errror code %s returned" % response.status_code)
            detail_message=str(response.__dict__)
            logging.error(detail_message)
            return
        payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % creds["idrac_ip"]
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 200:
            logging.info("- PASS: POST command passed to create target config job, status code %s returned" % response.status_code)
        else:
            logging.error("\n- FAIL, POST command failed to create BIOS config job, status code %s returned" % response.status_code)
            detail_message=str(response.__dict__)
            logging.error(detail_message)
            return
        data = response.json()
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in JSON headers output")
            return
        logging.info("- INFO: %s job ID successfully created" % job_id)
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code != 200:
                logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                return
            time.sleep(10)
            data = response.json()
            if data['Message'] == "Task successfully scheduled.":
                logging.info("- PASS, %s job id successfully scheduled" % job_id)
                if reboot.lower() == "yes":
                    logging.info("- INFO, user selected to reboot the server now to execute the config job")
                    if password_type.lower() == "syspassword" and set_password == True or change_password == True:
                        logging.info("\n- INFO, setting or changing BIOS system password detected. After the job executes and reboots the server, server will halt during POST for user to input system password. This is needed for the server to complete POST which will mark the job completed.\n")
                        time.sleep(10)
                        reboot_server()
                        loop_job_status_final()
                        break
                    else:
                        reboot_server()
                        loop_job_status_final()
        
                elif reboot.lower() == "no":
                    logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                    break
                else:
                    logging.warning("- WARNING, invalid value passed in for argument reboot")
                    break
                break
            else:
                logging.info("- INFO: JobStatus not scheduled, current status: %s" % data['Message'])

                
def bios_device_recovery(script_examples=""):
    """Function to recover corrupted server BIOS. During this process, server will power OFF, power ON, recover the BIOS firmware, reboot and process will be complete. Check iDRAC Lifecycle Logs for more details/status on the recovery process."""
    if script_examples:
        print("""\n- IdracRedfishSupport.bios_device_recovery(), this example will execute BIOS recovery process to recover server with corrupted BIOS.""")
    else:
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService/Actions/DellBIOSService.DeviceRecovery' % (creds["idrac_ip"])
        method = "DeviceRecovery"
        payload={"Device":"BIOS"}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202 or response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return

def get_bios_attribute_registry(script_examples="", attribute_name=""):
    """Function to get BIOS attribute registry. Getting attribute information is helpful to configure BIOS attributes (get supported possible values, dependencies, attribute type). Default behavior will get the complete BIOS attribute registry. Supported function argument: attribute_name (pass in exact BIOS string name value due to case sensitive."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_bios_attribute_registry(), this example will return complete BIOS attribute registry.
        \n- IdracRedfishSupport.get_bios_attribute_registry(attribute_name="MemTest"), this example will return only attribute registry details for BIOS attribute MemTest.""")
    else:
        if attribute_name:
            print("\n")
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            for i in data['RegistryEntries']['Attributes']:
                if attribute_name in i.values():
                    logging.info("- Details for attribute %s -\n" % attribute_name)
                    pprint(i)
                    return
            logging.error("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure attribute name is type correctly since its case sensitive" % attribute_name)
            return
        else:
            try:
                os.remove("bios_attribute_registry.txt")
            except:
                pass
            open_file = open("bios_attribute_registry.txt","a")
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            for i in data['RegistryEntries']['Attributes']:
                pprint(i)
                print("\n")
                for ii in i.items():
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    message = "\n"
                    open_file.writelines(message)
                message = "\n"
                open_file.writelines(message)
            current_dir = os.getcwd()
            logging.info("\n- Attribute registry is also captured in \"%s\\bios_attribute_registry.txt\" file" % current_dir)
            open_file.close()

def get_bios_attributes(script_examples="", attribute_name=""):
    """Function to get BIOS attributes with their current settings. Use attribute_name function argument to only return details for a specific attribute. NOTE: Make sure to pass in exact attribute name string due to case sensitive support."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_bios_attributes(), this example will return all BIOS attributes detected with current values.
        \n- IdracRedfishSupport.get_bios_attributes(attribute_name="MemTest"), this example will return only current value for BIOS attribute MemTest""")
    else:
        if attribute_name:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            data = response.json()
            for i in data['Attributes'].items():
                if i[0] == attribute_name:
                    logging.info("\n- Attribute name, current value details - \n")
                    pprint(i)
                    return
            logging.error("\n- FAIL, unable to get attribute current value. Either attribute doesn't exist for this BIOS version, typo in attribute name or case incorrect")
            return
        else:
            try:
                os.remove("bios_attributes.txt")
            except:
                pass
            open_file = open("bios_attributes.txt","a")
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            data = response.json()
            bios_attribute_string = "\n--- BIOS Attributes ---\n"
            print(bios_attribute_string)
            open_file.writelines(bios_attribute_string)
            for i in data['Attributes'].items():
                pprint(i)
                attribute_name = "Attribute Name: %s\t" % (i[0])
                open_file.writelines(attribute_name)
                attribute_value = "Attribute Value: %s\n" % (i[1])
                open_file.writelines(attribute_value)
            current_dir = os.getcwd()    
            logging.info("\n- Attributes are also captured in \"%s\\bios_attributes.txt\" file" % current_dir)
            open_file.close()

def set_bios_attributes(script_examples="", attribute_name="", attribute_value="", reboot=""):
    """Function to set either one or multiple BIOS attributes. Supported function arguments: attribute_name, attribute_value and reboot(supported values are yes and no). Make sure to pass in attribute name exactly due to case senstive. Example: MemTest will pass but memtest will fail. If you want to configure multiple attributes, make sure to use a comma separator between each attribute name and attribute value. If needed, see examples for passing in multiple attribute names and values."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.set_bios_attributes(attribute_name="MemTest,EmbSata",attribute_value="Disabled,AhciMode",reboot="yes"), this example will reboot the server now to set BIOS attribute MemTest to Disabled and EmbSata to AhciMode.
        \n- IdracRedfishSupport.set_bios_attributes(attribute_name="MemTest",attribute_value="Enabled",reboot="no"), this example will not reoot the server now to set BIOS attribute MemTest to Eanbled. Config job is still scheduled and will execute on next server manual reboot.""")
    else:
        bios_attribute_payload = {"Attributes":{}}
        attribute_names = attribute_name.split(",")
        attribute_values = attribute_value.split(",")
        for i,ii in zip(attribute_names, attribute_values):
            bios_attribute_payload["Attributes"][i] = ii
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        data = response.json()
        for i in bios_attribute_payload["Attributes"].items():
            for ii in data['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    if ii['Type'] == "Integer":
                        bios_attribute_payload['Attributes'][i[0]] = int(i[1])
        for i in bios_attribute_payload["Attributes"].items():
            print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % creds["idrac_ip"]
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
        payload_patch.update(bios_attribute_payload)
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        statusCode = response.status_code
        if response.status_code == 202 or response.status_code == 200:
            logging.info("\n- PASS: PATCH command passed to set BIOS attribute pending values and create config job, status code %s returned" % response.status_code)
        else:
            logging.error("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create config job, status code is %s" % response.status_code)
            data = response.json()
            logging.error("\n- POST command failure is:\n %s" % data)
            return
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in JSON headers output")
            return
        logging.info("- INFO: %s job ID successfully created" % job_id)
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code != 200:
                logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                return
            time.sleep(10)
            data = response.json()
            if data['Message'] == "Task successfully scheduled.":
                logging.info("- PASS, %s job id successfully scheduled" % job_id)
                if reboot.lower() == "yes":
                    logging.info("- INFO, user selected to reboot the server now to execute the config job")
                    reboot_server()
                    loop_job_status_final()
                elif reboot.lower() == "no":
                    logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                    break
                else:
                    logging.info("- INFO, invalid value passed in for argument reboot")
                    break
                break
            else:
                logging.info("- INFO: job status not marked as scheduled, current status: %s" % data['Message'])

def boot_to_network_iso(script_examples="", attach_iso="", detach_iso="", get_attach_status="", share_ip="", share_type="", share_name="", image_name="", share_username=""):
    """Function to either get network ISO attach status, boot to network ISO or detach network ISO. When you execute function to attach ISO and attach is successful, server will automatically reboot. Supported function arguments: attach_iso (supported value: True), detach_iso (supported value: True), get_attach_status (supported value: True), share_ip, share_name, image_name, share_username (only required for CIFS share) and share_type (supported values: NFS and CIFS. Note: If using CIFS share it will prompt you to enter CIFS share password)."""
    global concrete_job_uri
    if script_examples:
        print("""\n- IdracRedfishSupport.boot_to_network_iso(attach_iso=True, share_ip="192.168.0.130", share_type="NFS", share_name="/nfs", image_name="VMware-VMvisor-7.iso"), this example will attach ISO on NFS share and reboot the server to boot to it.
        \n- IdracRedfishSupport.boot_to_network_iso(get_attach_status=True), this example will get current attach ISO status.
        \n- IdracRedfishSupport.boot_to_network_iso(detach_iso=True), this example will detach attached ISO.
        \n- IdracRedfishSupport.boot_to_network_iso(attach_iso=True, share_ip="192.168.0.140", share_type="CIFS", share_name="cifs_share", image_name="VMware-VMvisor-7.iso"), share_username="administrator", this example will first prompt to enter CIFS username password, then boot from ISO on CIFS share.""")
    else:
        if get_attach_status:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (creds["idrac_ip"])
            payload={}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, POST command failed to get ISO attach status, status code is %s" % (response.status_code))
                data = response.json()
                logging.error("\n-POST command failure results:\n %s" % data)
                return
            logging.info("\n- INFO, Current ISO attach status: %s" % data['ISOAttachStatus'])
        elif detach_iso:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachISOImage' % (creds["idrac_ip"])
            payload={}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 200 or response.status_code == 202:
                logging.info("\n- PASS: POST command passed to detach ISO image, status code %s returned" % response.status_code)
            else:
                logging.error("\n- FAIL, POST command failed to detach ISO image, status code %s returned" % response.status_code)
                data = response.json()
                logging.error("\n-POST command failure results:\n %s" % data)
                return
        elif attach_iso:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.BootToNetworkISO' % (creds["idrac_ip"])
            method = "BootToNetworkISO"
            headers = {'content-type': 'application/json'}
            payload={}
            if share_ip:
                payload["IPAddress"] = share_ip
            if share_type:
                payload["ShareType"] = share_type.upper()
            if share_name:
                payload["ShareName"] = share_name
            if image_name:
                payload["ImageName"] = image_name
            if share_type.upper() == "CIFS" and share_username:
                cifs_password = getpass.getpass("- Enter CIFS share password: ")
                payload["UserName"] = share_username
                payload["Password"] = cifs_password
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 202 or response.status_code == 200:
                logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
                try:
                    concrete_job_uri = response.headers['Location']
                except:
                    logging.error("- FAIL, unable to locate concrete job URI in JSON headers output")
                    return
                logging.info("- INFO, task service URI created for method %s: %s\n" % (method, concrete_job_uri))
                check_concrete_job_uri_status()
            else:
                logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return

def check_concrete_job_uri_status():
    """Function to check URI concrete job ID status for OEM Operating System Deployment (OSD) actions. The function will only be called by functions who execute an action to perform OSD operations. This function cannot be executed as a standalone function to perform an operation."""
    from datetime import datetime
    start_time=datetime.now()
    while True:
        if x_auth_token == "yes":
            response = requests.get('https://%s%s' % (creds["idrac_ip"], concrete_job_uri),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s%s' % (creds["idrac_ip"], concrete_job_uri),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        current_time=str((datetime.now()-start_time))[0:7]
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202 or response.status_code == 200:
            logging.info("- INFO, GET command passed to get task details")
        else:
            logging.error("\n- FAIL, command failed to check job status, status code %s returned" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data= response.json()
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            return
        elif data['TaskState'] == "Completed":
            if "Fail" in data['Messages'][0]['Message'] or "fail" in data['Messages'][0]['Message']:
                logging.error("- FAIL: task failed, detailed error results: %s" % data.items())
                return        
            elif "completed successful" in data['Messages'][0]['Message'] or "command was successful" in data['Messages'][0]['Message']:
                logging.info("\n- PASS, task successfully marked completed")
                logging.info("\n- Final detailed task results -\n")
                for i in data.items():
                    if '@odata.type' in i[0]:
                        pass
                    elif i[0] == 'Messages':
                        for ii in i[1][0].items():
                            print("%s: %s" % (ii[0], ii[1]))   
                    else:
                        print("%s: %s" % (i[0], i[1]))
                break
            else:
                logging.error("- FAIL, unable to get final task message string")
                return
        elif data['TaskState'] == "Exception":
            logging.error("\n- FAIL, final detailed task results -\n")
            for i in data.items():
                if '@odata.type' in i[0]:
                    pass
                elif i[0] == 'Messages':
                    for ii in i[1][0].items():
                        print("%s: %s" % (ii[0], ii[1]))   
                else:
                    print("%s: %s" % (i[0], i[1]))
            return
        else:
            logging.info("- INFO, task not completed, current status: \"%s\"" % (data['TaskState']))
            time.sleep(10)

def unpack_and_attach_driver_pack(script_examples="", get_driver_packs="", get_attach_status="", attach_driver_pack="", detach_driver_pack=""):
    """Function to get either supported OS driver packs, attach status, attach driver pack or detach driver pack. Supported function arguments: get_driver_packs (supported value: True), get_attach_status (supported value: True), attach_driver_pack (supported value: Pass in OS driver pack string name) and detach_driver_pack (supported_value: True)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.unpack_and_attach_driver_pack(attach_driver_pack="Microsoft Windows Server 2022"), this example will attach Windows Server 2022 driver pack.
        \n- IdracRedfishSupport.unpack_and_attach_driver_pack(get_attach_status=True), this example will get current attach driver pack status.
        \n- IdracRedfishSupport.unpack_and_attach_driver_pack(detach_iso=True), this example will detach attached driver pack. 
        \n- IdracRedfishSupport..unpack_and_attach_driver_pack(get_driver_packs=True), this example will get driver pack details for supported operating systems.""")
    else:
        if get_driver_packs:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetDriverPackInfo' % (creds["idrac_ip"])
            payload={}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, POST command failed to get driver pack information, status code is %s" % (response.status_code))
                data = response.json()
                logging.error("\n-POST command failure results:\n %s" % data)
                return
            logging.info("\n- Driver packs supported for iDRAC %s\n" % creds["idrac_ip"])
            for i in data['OSList']:
                i = i.replace("\n","")
                print(i)
        elif get_attach_status:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (creds["idrac_ip"])
            headers = {'content-type': 'application/json'}
            payload={}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, POST command failed to get driver pack attach status, status code: %s" % (response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return
            logging.info("\n- INFO, Current driver pack attach status: %s" % data['DriversAttachStatus'])
        elif attach_driver_pack:
            global concrete_job_uri
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.UnpackAndAttach' % (creds["idrac_ip"])
            method = "UnpackAndAttach"
            payload={"OSName":attach_driver_pack}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 202 or response.status_code == 200:
                logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
                try:
                    concrete_job_uri = response.headers['Location']
                except:
                    logging.error("- FAIL, unable to locate task URI in JSON headers output")
                    return
                logging.info("- INFO, task URI created for method %s: %s\n" % (method, concrete_job_uri))
                check_concrete_job_uri_status()
            else:
                logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return
        elif detach_driver_pack:
            url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachDrivers' % (creds["idrac_ip"])
            payload={}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 200 or response.status_code == 202:
                logging.info("\n- PASS: POST command passed to detach driver pack, status code %s returned" % response.status_code)
            else:
                logging.error("\n- FAIL, POST command failed to detach driver pack, status code %s returned" % response.status_code)
                data = response.json()
                logging.info("\n-POST command failure results:\n %s" % data)
                return

def manage_iDRAC_time(script_examples="", get_time="", set_time=""):
    """Function to either get or set iDRAC time. Supported function arguments: get_time (supported value: True) and set_time (NOTE: execute get_time argument to see the correct date/time format to use)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.manage_iDRAC_time(get_time=True), this example will return current iDRAC date and time.
        \n- IdracRedfishSupport.manage_iDRAC_time(set_time="2022-01-07T16:15:05-06:00"), this example will set new iDRAC date and time.""")
    else:
        if get_time:
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (creds["idrac_ip"])
            method = "ManageTime"
            payload={"GetRequest":True}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data=response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, POST command failed for %s action, status code %s returned" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return
            for i in data.items():
                if i[0] != "@Message.ExtendedInfo":
                    print("\n- %s: %s" % (i[0], i[1]))
        elif set_time:
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (creds["idrac_ip"])
            method = "ManageTime"
            payload={"GetRequest":False, "TimeData":set_time}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data=response.json()
            if response.status_code == 200:
                logging.info("\n- PASS: POST command passed for %s action to SET iDRAC time, status code 200 returned\n" % method)
            else:
                logging.error("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return

def clear_foreign_config_controller(script_examples="", controller_fqdd=""):
    """Function to clear foreign configuration for storage controller. Supported function argument: controller_fqdd."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.clear_foreign_config_controller(controller_fqdd="RAID.Integrated.1-1"), this example will clear foreign configuration for controller RAID.integrated.1-1""")
    else:
        payload={"TargetFQDD": controller_fqdd}
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ClearForeignConfig' % (creds["idrac_ip"])
        method = "ClearForeignConfig"
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to clear foreign config for controller %s, status code %s returned" % (controller_fqdd, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
        else:
            logging.error("\n- FAIL, POST command failed to clear foreign config for storage controller %s, status code is %s" % (controller_fqdd, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def import_foreign_config_controller(script_examples="", controller_fqdd=""):
    """Function to import foreign configuration for storage controller. Supported function argument: controller_fqdd."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.import_foreign_config_controller(controller_fqdd="RAID.Integrated.1-1"), this example will import foreign configuration for controller RAID.integrated.1-1""")
    else:
        payload={"TargetFQDD": controller_fqdd}
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ImportForeignConfig' % (creds["idrac_ip"])
        method = "ImportForeignConfig"
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed to import foreign config for controller %s, status code %s returned" % (controller_fqdd, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
        else:
            logging.error("\n- FAIL, POST command failed to import foreign config for storage controller %s, status code %s" % (controller_fqdd, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(5)
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if data['JobType'] == "RAIDConfiguration":
            logging.info("- INFO, staged config job created, server will now reboot to execute the config job")
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            logging.info("- INFO, realtime config job created, job will get applied in real time with no server reboot needed")
        loop_job_status_final()


def reset_bios_default_settings(script_examples="", reboot=""):
    """Function to reset BIOS to default settings. Supported function argument: reboot (supported_values: yes and no). Reboot server is needed to execute the operation. If you pass in no for reboot, operation is still scheduled and will execute on next server reboot."""
    if script_examples:
        print("""\n- IdracRedfishSupport.reset_bios_default_settings(reboot="yes"), this example will reboot the server now to reset BIOS to default settings.""")
    else:
        url = "https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ResetBios" % creds["idrac_ip"]
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.__dict__
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: status code %s returned for POST command to reset BIOS to default settings" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed, status code %s returned" % response.status_code)
            detail_message = str(response.__dict__)
            logging.error(detail_message)
            return
        if reboot.lower() == "yes":
            logging.info("- INFO, user selected to reboot the server now to perform BIOS reset to defaults")
            reboot_server()
            return
        elif reboot.lower() == "no" or reboot == "":
            logging.info(" INFO, user selected to not reboot the server now. Reset to BIOS defaults is still scheduled and will execute on next server manual reboot.")
            return
        else:
            logging.info("- INFO, either incorrect value or missing reboot argument")
            return
        
def get_current_bios_boot_order(script_examples=""):
    """Function to get current BIOS boot mode and boot order."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_current_bios_boot_order(), this example will return current BIOS boot mode and the boot order.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes/BootMode' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes/BootMode' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            current_boot_mode = data['Attributes']['BootMode']
        else:
            logging.error("- ERROR, GET command failed to get current boot mode, status code %s returned" % response.status_code)
            return
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions?$expand=*($levels=1)' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions?$expand=*($levels=1)' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code != 200:
            logging.error("- ERROR, GET command failed to get current boot order, status code %s returned" % response.status_code)
            return
        logging.info("\n- Current boot order detected for BIOS boot mode \"%s\" -\n" % current_boot_mode)
        if data["Members"] == []:
            logging.warning("- WARNING, no boot order devices detected for BIOS boot mode %s" % current_boot_mode)
            return
        for i in data["Members"]:
            print("- Boot order device %s -\n" % count)
            pprint(i)
            print("\n")


def change_bios_boot_order(script_examples="", boot_order_devices="", reboot=""):
    """Function to change BIOS boot order. Supported function arguments: boot_order_devices (possible value: pass in one or multiple boot order device IDs. If passing in multiple devices, use a comma separator. NOTE: If needed, execute IdracRedfishSupport.get_current_bios_boot_order() to get boot order devices). reboot (possible values: yes and no. If you pass in no for reboot, the config job is still created and will execute on next server manual reboot)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.change_bios_boot_order(boot_order_devices="Boot0000", reboot="yes"), this example will reboot the server now to set Boot0000 entry as first device in the boot order.")
        \n - IdracRedfishSupport.change_bios_boot_order(boot_order_devices="Boot0004,Boot0009,Boot0000", reboot="no"), this examples shows setting the boot order passing in multipe devices. Server will not reboot now but the job will execute on next server manual reboot.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes/BootMode' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes/BootMode' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            current_boot_mode = data['Attributes']['BootMode']
        else:
            logging.error("- ERROR, GET command failed to get current boot mode, status code %s returned" % response.status_code)
            return
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"]
        if "," in boot_order_devices:
            boot_order_ids = boot_order_devices.split(",")
        else:
            boot_order_ids = [boot_order_devices]
        payload = {"Boot":{"BootOrder":boot_order_ids}}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: PATCH command passed to change %s boot order sequence" % current_boot_mode)
        else:
            logging.error("\n- FAIL, PATCH command failed to change %s boot order sequence, status code is %s" % (current_boot_mode, response.status_code))
            detail_message=str(response.__dict__)
            logging.error(detail_message)
            return
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers PATCH response, headers output is:\n%s" % response.headers)
            return
        logging.info("- PASS, job ID \"%s\" successfully created" % (job_id))
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code == 200:
                pass
                time.sleep(10)
            else:
                logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                return
            data = response.json()
            if data['Message'] == "Task successfully scheduled.":
                logging.info("- PASS, %s job id successfully scheduled" % job_id)
                if reboot.lower() == "yes":
                    print("- INFO, user selected to reboot the server now to execute the config job")
                    reboot_server()
                    loop_job_status_final()
                elif reboot.lower() == "no":
                    logging.info("- INFO, user selected to NOT reboot the server now to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
                    break
                else:
                    logging.error("- ERROR, invalid value passed in for argument reboot")
                    break
                break
            else:
                logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

def system_erase(script_examples="", get_supported_components="", erase_components=""):
    """Function to execute iDRAC system erase operation. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash. Supported function arguments: get_supported_components (possible value: True), erase_components (pass in one or more multiple component values and make sure to pass in exact string case. If passing in multiple component values, use a comma separator. Once system erase job is completed, server will power off and reset the iDRAC, stay in off state once the iDRAC is back up."""
    if script_examples:
        print("""\n- IdracRedfishSupport.system_erase(get_supported_components=True), this example will return supported component values to perform system erase operation.")
        \n - IdracRedfishSupport.system_erase(erase_components="LCData,CryptographicErasePD,IDRAC"), this example will excute system erase to erase Lifecycle Controller data, crypto erase drives and reset iDRAC to default settings.""")
    else:
        if get_supported_components:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, GET command failed to get supported component values,status code %s returned" % response.status_code)
                return
            logging.info("\n- Supported component values for System Erase operation -\n")
            for i in data['Actions']['#DellLCService.SystemErase']['Component@Redfish.AllowableValues']:
                print(i)
        elif erase_components:
            method = "SystemErase"
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SystemErase' % (creds["idrac_ip"])    
            headers = {'content-type': 'application/json'}
            if "," in erase_components:
                component_list = erase_components.split(",")
                payload={"Component":erase_components}
            else:
                payload={"Component":[erase_components]}
            logging.info("\n- INFO, component(s) selected for System Erase operation -\n")
            for i in payload["Component"]:
                print(i)
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            data = response.json()
            if response.status_code == 202:
                logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
            else:
                logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                return
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
                return
            logging.info("- PASS, job ID %s successfuly created for %s method" % (job_id, method))
            start_time=datetime.now()
            count_number = 0
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            logging.info("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
            start_job_status_message = data['Message']
            retry_count = 1
            while True:
                try:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                except:
                    if retry_count == 10:
                        logging.info("- INFO, retry count of 10 has been reached to communicate with iDRAC, script will exit")
                        return
                    else:
                        logging.info("- INFO, lost iDRAC network connection, retry GET request after 10 second sleep delay")
                        retry_count += 1
                        time.sleep(15)
                        continue    
                current_time = (datetime.now()-start_time)
                if response.status_code == 200:
                    current_job_status = data['Message']
                else:
                    print("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
                data = response.json()
                new_job_status_message = data['Message']
                if str(current_time)[0:7] >= "2:00:00":
                    logging.error("\n- FAIL: Timeout of 2 hours has elapsed, script stopped\n")
                    return
                elif data['JobState'] == "Failed" or "Fail" in data['Message'] or "Unable" in data['Message'] or "Invalid" in data['Message'] or "fail" in data['Message'] or "Cannot" in data['Message'] or "cannot" in data['Message']:
                    logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
                    return
                elif data['Message'] == "Job completed successfully.":
                    logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                    for i in data.items():
                        if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                            pass
                        else:
                            print("%s: %s" % (i[0],i[1]))
                    logging.info("\n- INFO, server is in OFF state due to System Erase process completed, iDRAC will now reboot.")
                    if "BIOS" in erase_components:
                        logging.info("- INFO, BIOS component selected. Once iDRAC is back up, manually power on the server for BIOS to complete reset to defaults operation.")
                        return
                    else:
                        return
                else:
                    if start_job_status_message != new_job_status_message:
                        logging.info("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
                        start_job_status_message = new_job_status_message
                    else:
                        pass
                    continue

def get_iDRAC_attribute_registry(script_examples="", attribute_name=""):
    """Function to get iDRAC attribute registry. Getting attribute information is helpful to configure iDRAC attributes (get supported possible values, dependencies, attribute type). Supported function argument: attribute_name."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_iDRAC_attribute_registry(), this example will return complete iDRAC attribute registry.")
        \n - IdracRedfishSupport.get_iDRAC_attribute_registry(attribute_name="SNMPAlert.8.SNMPv3UserID"), this example will return attribute registry details for only this attribute.""")
    else:
        if attribute_name:
            print("\n")
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                    logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                    return
            elif response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            found = ""
            for i in data['RegistryEntries']['Attributes']:
                if attribute_name in i.values():
                    found = "yes"
                    for ii in i.items():
                        print("%s: %s" % (ii[0],ii[1]))
            if found != "yes":
                logging.error("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % attribute_name)
                return
        else:
            try:
                os.remove("iDRAC_attribute_registry.txt")
            except:
                pass
            open_file = open("iDRAC_attribute_registry.txt","a")
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            for i in data['RegistryEntries']['Attributes']:
                pprint(i)
                print("\n")
                for ii in i.items():
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    message = "\n"
                    open_file.writelines(message)
                message = "\n"
                open_file.writelines(message)
            current_dir = os.getcwd()
            logging.info("\n- Attribute registry is also captured in \"%s\\iDRAC_attribute_registry.txt\" file" % current_dir)
            open_file.close()

def get_iDRAC_attributes(script_examples="", group_name="", attribute_name=""):
    """Function to get iDRAC attributes which also includes Lifecycle Controller and System attributes. Supported function arguments: group_name (supported values: idrac, lc and system) and attribute_name (pass in attribute name if you only want to return details for a specific attribute."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_iDRAC_attributes(group_name="idrac"), this example will return all iDRAC attributes and their current values.")
        \n - IdracRedfishSupport.get_iDRAC_attributes(group_name="idrac", attribute_name="SupportAssist.1.HostOSProxyPassword"), this example will return details for only this attribute.""")
    elif group_name:
            if group_name.lower() == "idrac":
                uri = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
            elif group_name.lower() == "lc":
                uri = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % creds["idrac_ip"]
            elif group_name.lower() == "system":
                uri = 'https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % creds["idrac_ip"]
            else:
                print("- INFO, either missing or incorrect value for group_name argument")
                return
            if x_auth_token == "yes":
                response = requests.get(uri,verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get(uri,verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code == 401:
                logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                return
            elif response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            attributes_dict=data['Attributes']
            if attribute_name:
                for i in attributes_dict:
                    if i == attribute_name:
                        logging.info("\nAttribute Name: %s, Current Value: %s" % (i, attributes_dict[i]))
                        return
                logging.error("\n- FAIL, unable to locate attribute \"%s\". Either current iDRAC version installed doesn\'t support this attribute or iDRAC missing required license" % attribute_name)
                return
            logging.info("\n- %s Attribute Names and Values:\n" % group_name.upper())
            sorted_dict={}
            try:
                os.remove("attributes.txt")
            except:
                pass
            open_file = open("attributes.txt","a")
            for i in attributes_dict.items():
                if 'odata' not in i[0]:
                    sorted_dict[i[0]] = i[1]
            try:
                for i in sorted(sorted_dict.iterkeys()):
                    message = "Name: %s, Value: %s" % (i, sorted_dict[i])
                    print(message)
                    open_file.writelines("%s\n" % message)
            except:
                for i in attributes_dict:
                    message = "Name: %s, Value: %s" % (i, attributes_dict[i])
                    print(message)
                    open_file.writelines("%s\n" % message)
            open_file.close()
            current_dir = os.getcwd()
            logging.info("\n- INFO, attribute details also copied to \"%s\\attributes.txt\" file" % current_dir)
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def set_iDRAC_attributes(script_examples="", group_name="", attribute_names="", attribute_values=""):
    """Function to set iDRAC, Lifecycle Controller or System attributes. Supported function arguments: group_name (supported values: idrac, lc and system), attribute_names (pass in one or more attribute name. If passing in multiple names use comma separator) and attribute values (make sure the values you pass in match the number of attribute names)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.set_iDRAC_attributes(group_name="idrac", attribute_names="SNMPAlert.1.State,SNMPAlert.2.State",attribute_values="Enabled,Enabled"), this example shows configuring multiple iDRAC attributes.
        \n - IdracRedfishSupport.set_iDRAC_attributes(group_name="system", attribute_names="ServerPwr.1.PSRapidOn", attribute_values="Enabled"), this example shows configuring one system attribute.""")
    else:
        if group_name.lower() == "idrac":
            uri = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
        elif group_name.lower() == "lc":
            uri = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % creds["idrac_ip"]
        elif group_name.lower() == "system":
            uri = 'https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % creds["idrac_ip"]
        else:
            print("- INFO, either missing or incorrect value for group_name argument")
            return
        if x_auth_token == "yes":
            response = requests.get(uri,verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get(uri,verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        payload = {"Attributes":{}}
        attribute_names_list = attribute_names.split(",")
        attribute_values_list = attribute_values.split(",")
        for i,ii in zip(attribute_names_list, attribute_values_list):
            payload["Attributes"][i] = ii
        print("\n- INFO, configuring \"%s\" attributes\n" % group_name.upper())
        for i in payload["Attributes"].items():
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
                logging.error("\n- Detailed failure results:\n %s" % data)
                return
            for ii in data['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    for iii in ii.items():
                        if iii[0] == "Type":
                            if iii[1] == "Integer":
                                payload["Attributes"][i[0]] = int(i[1])
        for i in payload["Attributes"].items():
            print(" Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(uri, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(uri, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully set \"%s\" attribute(s), status code %s returned\n" % (group_name.upper(), response.status_code))
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            logging.error("\n- FAIL, Command failed to set %s attributes(s), status code: %s\n" % (group_name.upper(),statusCode))
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        
def export_hardware_inventory(script_examples="", get_supported_share_types="", export_hw_inventory="", share_ip="", share_type="", share_name="", share_username="", share_password="", ignore_cert_warning="", filename=""):
    """Function to export server hardware inventory locally or network shares. Supported function arguments: get_supported_share_types (possible value: True, export_hw_inventory (possible value: True), share_type (execute IdracRedfishSupport.export_hardware_inventory(get_supported_share_types=True) to get supported share type values), share_ip, share_name, share_username (required for CIFS or auth enabled for HTTP/HTTPS), share_userpassword (required for CIFS or auth enabled for HTTP/HTTPS), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (HW inventory will only be exported in XML format) filename argument is optional, if you do not pass in this argument default filename hwinv.xml will be used."""
    method = "ExportHWInventory"
    if script_examples:
        print("""\n- IdracRedfishSupport.export_hardware_inventory(get_supported_share_types=True), this example will return supported share types for export HW inventory.
        \n- IdracRedfishSupport.export_hardware_inventory(export_hw_inventory=True, share_type="local", filename="R740_HW_inv.xml"), this example will export server HW inventory locally.
        \n- IdracRedfishSupport.export_hardware_inventory(export_hw_inventory=True, share_type="NFS", filename="R650_HW_inv.xml", share_ip="192.168.0.130", share_name="/nfs"), this example will export HW inventory to NFS share.""")
    elif get_supported_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        logging.info("\n- Supported network share types for ExportHWInventory Action -\n")
        for i in data['Actions'].items():
            if i[0] == "#DellLCService.ExportHWInventory":
                for ii in i[1]['ShareType@Redfish.AllowableValues']:
                    print(ii)
        return
    elif export_hw_inventory and share_type:
        global job_id
        payload = {}
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportHWInventory' % (creds["idrac_ip"])
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            if share_type.lower() == "local":
                payload["ShareType"] = share_type.title()
            else:
                payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if filename:
                payload["FileName"] = filename
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if ignore_cert_warning:
            payload["IgnoreCertWarning"] = ignore_cert_warning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        if share_type.lower() == "local":
            if response.headers['Location'] == "/redfish/v1/Dell/hwinv.xml":
                if x_auth_token == "yes":
                    response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                if filename:
                    export_filename = filename
                else:
                    export_filename = "hwinv.xml"    
                with open(export_filename, "wb") as output:
                    output.write(response.content)
                logging.info("\n- INFO, check your local directory for hardware inventory XML file \"%s\"" % export_filename)
                return
            else:
                logging.error("- ERROR, unable to locate exported hardware inventory URI in headers output. Manually run GET on URI %s to see if file can be exported." % response.headers['Location'])
                return
        else:
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
                return
            logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
            from datetime import datetime
            start_time=datetime.now()
            while True:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                current_time=(datetime.now()-start_time)
                if response.status_code != 200:
                    logging.error("\n- FAIL, Command failed to check job status, return code %s" % statusCode)
                    logging.error("Extended Info Message: {0}".format(response.json()))
                    return
                data = response.json()
                if str(current_time)[0:7] >= "0:05:00":
                    logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                    return
                elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
                    logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                    return
                elif data['JobState'] == "Completed":
                    if data['Message'] == "Hardware Inventory Export was successful":
                        logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                    else:
                        logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                    for i in data.items():
                        if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                            print("%s: %s" % (i[0],i[1]))
                    break
                else:
                    logging.info("- INFO, job state not marked completed, current job status is running, polling again")
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def export_iDRAC_lifecycle_logs(script_examples="", get_supported_share_types="", export_lc_logs="", share_ip="", share_type="", share_name="", share_username="", share_password="", ignore_cert_warning="", filename=""):
    """Function to export iDRAC Lifecycle (LC) logs locally or network shares. Supported function arguments: get_supported_share_types (possible value: True, export_lc_logs (possible value: True), share_type (execute IdracRedfishSupport.export_iDRAC_lifecycle_logs(get_supported_share_types=True), share_ip, share_name, share_username (if auth is enabled), share_userpassword (if auth is enabled), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (iDRAC LC logs will only be exported in XML format). Filename is optional, if you do not pass in this argument default filename lclog.xml will be used."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_iDRAC_lifecycle_logs(get_supported_share_types=True), this example will return supported share types for export iDRAC LC logs.
        \n- IdracRedfishSupport.export_iDRAC_lifecycle_logs(export_lc_logs=True, share_type="local", filename="R740_LC_logs.xml"), this example will export iDRAC LC logs locally.
        \n- IdracRedfishSupport.export_iDRAC_lifecycle_logs(export_lc_logs=true, share_type="NFS", filename="R650_LC_logs.xml", share_ip="192.168.0.130", share_name="/nfs"), this example will export iDRAC LC logs to NFS share.""")
    elif get_supported_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        logging.info("\n- Supported network share types for ExportLCLog action -\n")
        for i in data['Actions'].items():
            if i[0] == "#DellLCService.ExportLCLog":
                for ii in i[1]['ShareType@Redfish.AllowableValues']:
                    print(ii)
    elif export_lc_logs and share_type:
        global job_id
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportLCLog' % (creds["idrac_ip"])
        method = "ExportLCLog"
        payload = {}
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            if share_type.lower() == "local":
                payload["ShareType"] = share_type.title()
            else:
                payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if filename:
                payload["FileName"] = filename
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if ignore_cert_warning:
            payload["IgnoreCertWarning"] = ignore_cert_warning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        if share_type.lower() == "local":
            if response.headers['Location'] == "/redfish/v1/Dell/lclog.xml":
                if x_auth_token == "yes":
                    response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                if filename:
                    export_filename = filename
                else:
                    export_filename = "lclog.xml"    
                with open(export_filename, "wb") as output:
                    output.write(response.content)
                logging.info("\n- INFO, check your local directory for exported LC log \"%s\"" % export_filename)
                return
            else:
                logging.error("- ERROR, unable to locate exported LC log URI in headers output. Manually run GET on URI %s to see if file can be exported." % response.headers['Location'])
                return
        else:
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
                return
            logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
            start_time = datetime.now()
            while True:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                current_time = (datetime.now()-start_time)
                if response.status_code != 200:
                    logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
                    logging.error("Extended Info Message: {0}".format(response.json()))
                    return
                data = response.json()
                if str(current_time)[0:7] >= "0:05:00":
                    logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                    return
                elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
                    logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                    return
                elif data['JobState'] == "Completed":
                    if data['Message'] == "LCL Export was successful":
                        logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                    else:
                        logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                    for i in data.items():
                        if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                            print("%s: %s" % (i[0],i[1]))
                    break
                else:
                    logging.info("- INFO, job state not marked completed, current job status is running, polling again")
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def export_server_factory_configuration(script_examples="", get_supported_share_types="", export_factory_config="", share_ip="", share_type="", share_name="", share_username="", share_password="", ignore_cert_warning="", filename=""):
    """Function to export server factory configuration to a network share. Supported function arguments: get_supported_share_types (possible value: True, export_factory_config (possible value: True), share_type, share_ip, share_name, share_username (required for CIFS and HTTP/HTTPS if auth is enabled), share_userpassword (required for CIFS and HTTP/HTTPS if auth is enabled), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (factory inventory will only be exported in XML format)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_server_factory_configuration(get_supported_share_types=True), this example will return supported share types for export factory configuration.
        \n- IdracRedfishSupport.export_server_factory_configuration(export_factory_config=True, share_type="local"), this example will export factory configuration XML file locally. 
        \n- IdracRedfishSupport.export_server_factory_configuration(export_factory_config=True, share_type="NFS", filename="R740_factory_config.xml", share_ip="192.168.0.130), this example will export server factory configuration to NFS share.""")
    elif get_supported_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        logging.info("\n- Supported network share types for ExportFactoryConfiguration action -\n")
        for i in data['Actions'].items():
            if i[0] == "#DellLCService.ExportFactoryConfiguration":
                for ii in i[1]['ShareType@Redfish.AllowableValues']:
                    print(ii)
    elif export_factory_config and share_type:
        global job_id
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportFactoryConfiguration' % (creds["idrac_ip"])
        method = "ExportFactoryConfiguration"
        payload = {}
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            if share_type.lower() == "local":
                payload["ShareType"] = share_type.title()
            else:
                payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if filename:
                payload["FileName"] = filename
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if ignore_cert_warning:
            payload["IgnoreCertWarning"] = ignore_cert_warning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        if share_type.lower() == "local":
            if response.headers['Location'] == "/redfish/v1/Dell/factoryconfig.xml":
                while True:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"], headers={'X-Auth-Token': creds["idrac_x_auth_token"]})   
                    else:
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    export_filename = "factoryconfig.xml"    
                    with open(export_filename, "wb") as output:
                        output.write(response.content)
                    logging.info("\n- INFO, check your local directory for factory config XML file \"%s\"" % export_filename)
                    return
            else:
                data = response.json()
                logging.error("- ERROR, unable to locate factory config XML URI in headers output, JSON response: \n%s" % data)
                return                      
        else:
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
                return
            logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
            start_time = datetime.now()
            while True:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                current_time = (datetime.now()-start_time)
                if response.status_code == 401:
                    logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
                    return
                elif response.status_code != 200:
                    logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
                    logging.error("Extended Info Message: {0}".format(response.json()))
                    return
                data = response.json()
                if str(current_time)[0:7] >= "0:05:00":
                    logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                    return
                elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
                    logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                    return
                elif data['JobState'] == "Completed":
                    if data['Message'] == "Factory Configuration Export was successful":
                        logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                    else:
                        logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                    for i in data.items():
                        if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                            print("%s: %s" % (i[0],i[1]))
                    break
                else:
                    logging.info("- INFO, job state not marked completed, current job status is running, polling again")
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def export_server_screen_shot(script_examples="", file_type=""):
    """Function to export server screenshot saved by iDRAC. This image will be exported in base64 format to a file. You will need to take this content and use a utility which can convert base64 to PNG for viewing the image. Supported function argument: file_type (supported values: LastCrashScreenShot, Preview and ServerScreenShot. NOTE: Make sure to pass in the exact case value)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.export_server_screen_shot(file_type="LastCrashScreenShot"), this example will export last server crash screenshot.
        \n- IdracRedfishSupport.export_server_screen_shot(file_type="ServerScreenShot"), this example will export current server screenshot.""")
    elif file_type:
        payload={}
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportServerScreenShot' % (creds["idrac_ip"])
        method = "ExportServerScreenShot"
        payload["FileType"] = file_type
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202 or response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        try:
            os.remove("export_screenshot.txt")
        except:
            pass
        with open("export_screenshot.txt","w") as x:
            x.writelines(data['ServerScreenShotFile'])
        logging.info("\n- PASS, screenshot exported locally to file \"export_screenshot.txt\". Take the contents and copy to a utility which can convert base64 into PNG file to view the screenshot")
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def export_server_video_log(script_examples="", file_type=""):
    """Function to export server video log saved by iDRAC. Supported function argument: file_type(supported values: BootCaptureVideo and CrashCaptureVideo. NOTE: make sure to pass in the exact case value). Extract the video files(dvc format) from the zip to view them."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_server_video_log(file_type="BootCaptureVideo"), this example will export latest boot capture video.
        \n- IdracRedfishSupport.export_server_video_log(file_type="CrashCaptureVideo"), this example will export latest crash capture video.""")
    elif file_type:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportVideoLog' % (creds["idrac_ip"])
        method = "ExportVideoLog"
        payload={"ShareType":"Local","FileType":file_type}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s" % (method, response.status_code))
            data = response.json()
            logging.info("\n- POST command failure results:\n %s" % data)
            return
        time.sleep(10)
        try:
            video_log_capture_zip_uri = response.headers['Location']
        except:
            logging.error("- FAIL, unable to locate video capture URI in POST response output")
            return
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"], headers={'X-Auth-Token': creds["idrac_x_auth_token"]})   
            else:
                response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            export_filename = "bootlogs.zip"    
            with open(export_filename, "wb") as output:
                output.write(response.content)
            logging.info("\n- INFO, check your local directory for \"%s\" file. To watch the video capture files(dvc format), download the video player from the iDRAC GUI/Maintenance/Troubleshooting page." % export_filename)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def export_server_thermal_history(script_examples="", get_supported_share_types="", export_thermal_history="", share_ip="", share_type="", share_name="", share_username="", share_password="", filename="", file_type=""):
    """Function to export server thermal history to a network share. Supported function arguments: get_supported_share_types (possible value: True), export_thermal_history (possible value: True), share_type, share_ip, share_name, share_username (required for CIFS only), share_userpassword (required for CIFS only), filename (pass in unique failename), file_type (pass in file type for exported file, either CSV or XML."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_server_thermal_history(get_supported_share_types=True), this example will get supported share types for export.
        \n- IdracRedfishSupport.export_server_thermal_history(export_thermal_history=True, share_ip="192.168.0.130", share_type="NFS", share_name="/nfs", filename="r740_thermal_history.csv", file_type="CSV"), this example will export thermal history to NFS share in CSV file format.""")
    elif get_supported_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        logging.info("\n- Supported network share types for ExportThermalHistory action -\n")
        for i in data['Actions'].items():
            if i[0] == "#DellMetricService.ExportThermalHistory":
                for ii in i[1]['ShareType@Redfish.AllowableValues']:
                    print(ii)
    elif export_thermal_history and share_ip and share_type and share_name:
        global job_id
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService/Actions/DellMetricService.ExportThermalHistory' % (creds["idrac_ip"])
        method = "ExportThermalHistory"
        payload = {}
        if share_ip:
            payload["IPAddress"] = share_ip
        if file_type:
            payload["FileType"] = file_type
        if share_type:
            payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if filename:
                payload["FileName"] = filename
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return 
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            return
        logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
        start_time = datetime.now()
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            current_time=(datetime.now()-start_time)
            if response.status_code != 200:
                logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                return
            data = response.json()
            if str(current_time)[0:7] >= "0:05:00":
                logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                return
            elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
                logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                return
            elif data['JobState'] == "Completed":
                if data['Message'] == "The command was successful":
                    logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                else:
                    logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                logging.info("- INFO, job state not marked completed, current job status is running, polling again")
                time.sleep(5)
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def convert_drives_RAID(script_examples="", drives=""):
    """Function to convert drives from non RAID(non ready) to RAID(ready) state. Supported function argument: drives (possible values: pass in one more multiple disk FQDDs. If passing in multiple disk FQDDs, use comma separator)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.convert_drives_RAID(drives="Disk.Bay.2:Enclosure.Internal.0-1,Disk.Bay.3:Enclosure.Internal.0-1"), this example shows converting multiple drives to RAID(ready) state.""")
    elif drives:
        method = "ConvertToRAID"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ConvertToRAID' % (creds["idrac_ip"])
        if "," in drives:
            convert_drives = drives.split(",")
        else:
            convert_drives = [drives]
        payload={"PDArray": convert_drives}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method))
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def convert_drives_nonRAID(script_examples="", drives=""):
    """Function to convert drives from RAID(ready) to non RAID(not ready) state. Support function argument: drives (possible values: pass in one more multiple disk FQDDs. If passing in multiple disk FQDDs, use comma separator)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.convert_drives_nonRAID(drives="Disk.Bay.2:Enclosure.Internal.0-1,Disk.Bay.3:Enclosure.Internal.0-1"), this example shows converting multiple drives to nonRAID(not ready) state.""")
    elif drives:
        method = "ConvertToNonRAID"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ConvertToNonRAID' % (creds["idrac_ip"])
        if "," in drives:
            convert_drives = drives.split(",")
        else:
            convert_drives = [drives]
        payload={"PDArray": convert_drives}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method))
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def export_clear_serial_datalogs(script_examples="", enable_capture_serial="", export_serial_data="", clear_serial_data="", disable_capture_serial=""):
    """Function to either enable serial data capture, export serial data or clear serial data. NOTE: This feature requires iDRAC Datacenter license. Supported function arguments: enable_capture_serial (possible value: True), export_serial_data (possible value: True), clear_serial_data (possible value: True), disable_capture_serial (possible value: True)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_clear_serial_datalogs(enable_capture_serial=True), this example shows enabling serial capture for iDRAC.
        \n- IdracRedfishSupport.export_clear_serial_datalogs(export_serial_data=True), this example shows export iDRAC captured serial data.
        \n- IdracRedfishSupport.export_clear_serial_datalogs(clear_serial_data=True), this example show clearing iDRAC cached serial data.
        \n- IdracRedfishSupport.export_clear_serial_datalogs(disabled_capture_data=True), this example shows disabling iDRAC serial capture feature.""")
    elif enable_capture_serial:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
        payload = {"Attributes":{"SerialCapture.1.Enable":"Enabled","Serial.1.Enable":"Enabled"}}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully set attributes to enable serial data capture, status code %s returned\n" % response.status_code)
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
            else:
                pass
        else:
            logging.error("\n- FAIL, Command failed to set attributes, status code : %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
    elif export_serial_data:
        method = "SerialDataExport"
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataExport' % (creds["idrac_ip"])
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            logging.error("\n- POST command failure results:\n %s" % response.__dict__)
            return
        try:
            os.remove("serial_data_logs.txt")
        except:
            pass
        filename_open = open("serial_data_logs.txt", "w")
        dict_response = response.__dict__['_content']
        string_convert = str(dict_response)
        string_convert = string_convert.lstrip("'b")
        string_convert = string_convert.rstrip("'")
        string_convert = string_convert.split("\\n")
        for key in string_convert:
            key = key.replace("\\r", "")
            key = key.replace("\\t", "")
            filename_open.writelines(key)
            filename_open.writelines("\n")
        filename_open.close()
        logging.info("- INFO, Exported serial logs captured to file \"%s\\%s\"" % (os.getcwd(), "serial_data_logs.txt"))
    elif clear_serial_data:
        method = "SerialDataClear"
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataClear' % (creds["idrac_ip"])
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 204:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            logging.error("\n- POST command failure results:\n %s" % response.__dict__)
            return
    elif disable_capture_serial:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
        payload = {"Attributes":{"SerialCapture.1.Enable":"Disabled"}}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to successfully disable attribute for serial data capture, status code %s returned\n" % response.status_code)
            if "error" in data.keys():
                logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
                logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            logging.error("\n- FAIL, Command failed to set attributes, status code : %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def supportassist_status_accept_EULA(script_examples="", get_EULA_status="", accept_EULA=""):
    """Function to manage SupportAssist End User License Agreement (EULA). Supported function arguments: get_EULA_status (supported value: True) and accept_EULA (supported value: True)"""
    if script_examples:
        print("""\n- IdracRedfishSupport.supportassist_status_accept_EULA(get_EULA_status=True), this example will get current SupportAssist EULA status.
        \n- IdracRedfishSupport.supportassist_status_accept_EULA(accept_EULA=True), this example will accept SupportAssist EULA.""")
    elif accept_EULA:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistAcceptEULA' % (creds["idrac_ip"])
        method = "SupportAssistAcceptEULA"
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("- PASS, %s method passed and End User License Agreement (EULA) has been accepted" % method)
        else:
            data = response.json()
            logging.error("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
    elif get_EULA_status:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (creds["idrac_ip"])
        method = "SupportAssistGetEULAStatus"
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("- PASS, %s method passed to get End User License Agreement (EULA) status" % method)
        else:
            data = response.json()
            logging.error("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
        logging.info("\n- Current Support Assist End User License Agreement Information -\n")
        for i in data.items():
            if "ExtendedInfo" not in i[0]:
                print("%s: %s" % (i[0],i[1]))
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def supportassist_register(script_examples="", get_register_status="", register="", city="", companyname="", country="", email="", firstname="", lastname="", phonenumber="", state="", street="", zipcode=""):
    """Function to register SupportAssist, either get current register status or register SupportAssist. Supported function arguments: get_register_status (supported value: True), register (supported value: True), city, companyname, country, email (optional for register), firstname, lastname, phonenumber, state, street and zipcode."""
    if script_examples:
        print("""\n- IdracRedfishSupport.supportassist_register(get_register_status=True), this example shows getting SupportAssist register status.
        \n- IdracRedfishSupport.supportassist_register(register=True, city="Austin", companyname="Dell Inc", country="US",email="test@dell.com", firstname="lab", lastname="tester", phonenumber="512-123-1234", state="Texas", street="1234 1st street", zipcode="78758"), this example shows registering SupportAssist feature.""")
    elif get_register_status:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (creds["idrac_ip"])
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("- PASS, POST command passed to get SupportAssist registered status")
        else:
            data = response.json()
            logging.error("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
        logging.info("- INFO, current SupportAssist registered status for iDRAC %s: %s" % (creds["idrac_ip"], data["IsRegistered"]))     
    elif register and city and companyname and country and firstname and lastname and phonenumber and state and street and zipcode:            
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
        payload = {"Attributes":{"OS-BMC.1.AdminState":"Enabled"}}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("- PASS, POST command passed to enable iDRAC attribute OS-BMC.1.AdminState")
        else:
            logging.error("\n- FAIL, POST command failed, status code %s returned" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistRegister' % (creds["idrac_ip"])
        method = "SupportAssistRegister"
        payload = {"City":city, "CompanyName":companyname, "Country":country, "PrimaryEmail":email, "PrimaryFirstName":firstname, "PrimaryLastName":lastname, "PrimaryPhoneNumber":phonenumber, "State":state, "Street1": street,"Zip":zipcode}
        print("\n- Parameters passed in for SupportAssistRegister action -\n")
        for i in payload.items():
            print ("%s: %s" % (i[0], i[1]))
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS, SupportAssistRegister action passed, status code %s returned" % response.status_code)
        else:
            logging.error("\n- FAIL, SupportAssistRegister action failed, status code %s returned. Detailed error results:\n" % response.status_code)
            data = response.__dict__
            logging.error(data["_content"])
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def export_support_assist_collection(script_examples="", get_supported_share_types="", export_collection="", share_ip="", share_type="", share_name="", share_username="", share_password="", filter_pii="", data_selector=""):
    """Function to export SupportAssist collection either locally or to a network share. Supported function arguments: get_supported_share_types (supported value: True), export_collection (supported value: True), share_ip, share_type, share_name, share_username, share_password, filter_pii (supported values: No and Yes) and data_selector (supported values: DebugLogs, HWData, OSAppData, TTYLogs and TelemetryReports. You can pass in one or multiple values. If passing in multiple, use a comma separator. Supported values are also case sensitive)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_support_assist_collection(get_supported_share_types=True), this example shows getting supported share types for exporting SupportAssist collection.
        \n- IdracRedfishSupport.export_support_assist_collection(export_collection=True, share_type="Local",data_selector="HWData"), this example shows exporting SupportAssist collection locally.
        \n- IdracRedfishSupport.export_support_assist_collection(export_collection=True, share_type="NFS",data_selector="HWData,TTYLogs",share_name="/nfs",share_ip="192.168.0.130"), this example shows exporting SupportAssist collection to NFS share.""")
    elif get_supported_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202 or response.status_code == 200:
            logging.info("- PASS, GET command passed to get LCService OEM extension")
        else:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % (method, response.status_code))
            logging.error("\n- Detailed failure results:\n %s" % data)
            return
        logging.info("\n- Supported network share types for SupportAssistCollection action -\n")
        for i in data['Actions'].items():
            if i[0] == "#DellLCService.SupportAssistCollection":
                for ii in i[1]['ShareType@Redfish.AllowableValues']:
                    print(ii)
    elif export_collection and share_type:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection' % (creds["idrac_ip"])
        method = "SupportAssistCollection"    
        payload={}
        if filter_pii:
            payload["Filter"] = filter_pii
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            if share_type.lower() == "local":
                payload["ShareType"] = share_type.title()
            else:
                payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if data_selector:
            if "," in data_selector:
                data_selector = data_selector.split(",")
                payload["DataSelectorArrayIn"] = data_selector
            else:
                payload["DataSelectorArrayIn"] = [data_selector]
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            return
        logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
        start_time = datetime.now()
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            current_time=(datetime.now()-start_time)
            if response.status_code != 200:
                logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                return
            data = response.json()
            try:
                if response.headers['Location'] == "/redfish/v1/Dell/sacollect.zip" or response.headers['Location'] == "/redfish/v1/Oem/Dell/sacollect.zip":
                    logging.info("- PASS, job ID %s successfully marked completed" % job_id)
                    if x_auth_token == "yes":
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"], headers={'X-Auth-Token': creds["idrac_x_auth_token"]})   
                    else:
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], response.headers['Location']), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    SA_export_filename = "sacollect.zip"    
                    with open(SA_export_filename, "wb") as output:
                        output.write(response.content)
                    logging.info("\n- INFO, check your local directory for SupportAssist collection zip file \"%s\"" % SA_export_filename)
                    return
                else:
                    data = response.json()
                    logging.error("- ERROR, unable to locate SA collection URI in headers output, JSON response: \n%s" % data)
                    return
            except:
                if str(current_time)[0:7] >= "1:00:00":
                    logging.error("\n- FAIL: Timeout of 1 hour has been hit, script stopped\n")
                    return
                elif data['JobState'] == "CompletedWithErrors":
                        logging.info("\n- INFO, SA collection completed with errors, please check iDRAC Lifecycle Logs for more details")
                        return
                elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "error" in data['Message'] or "Error" in data['Message']:
                    logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                    return
                elif data['JobState'] == "Completed":
                    if data['Message'] == "The SupportAssist Collection and Transmission Operation is completed successfully.":
                        logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                    else:
                        logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                    for i in data.items():
                        if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                            pass
                        else:
                            print("%s: %s" % (i[0],i[1]))
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (creds["idrac_ip"]),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
                    service_tag = data['Oem']['Dell']['DellSystem']['NodeID']
                    logging.info("\n- SA exported log file located on your network share should be in ZIP format with server service tag \"%s\" in the file name" % service_tag)
                    break
                else:
                    logging.info("- INFO, job status not complete, check status again in 30 seconds")
                    time.sleep(30)
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def firmware_update_multipart_upload(script_examples="", get_fw_inventory="", fw_image_path="", reboot=""):
    """Function to either get current firmware inventory or update firmware for one supported device. Supported function arguments: (get_fw_inventory (possible value: True), firmware_image_path (pass in the complete directory path with firmware image name. Firmware image must be Windows Dell Update Package EXE file) and reboot (supported values: yes and no). Reboot server is required for certain devices to apply the firmware (Examples: BIOS, NIC, PERC). Refer to iDRAC user guide update section for more details."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.firmware_update_multipart_upload(fw_image_path="C:\\Users\\administrator\\Downloads\\Diags_R650.EXE"), this example will update DIAGS. This device is an immediate update so no reboot argument is needed.
        \n- IdracRedfishSupport.firmware_update_multipart_upload(fw_image_path="C:\\Users\\administrator\\Downloads\\H745_A16.EXE",reboot="no"), this example shows updating H745 storage controller. Update job is scehduled but will not auto reboot. Update job will execute on next server manual reboot.
        \n- IdracRedfishSupport.firmware_update_multipart_upload(fw_image_path="C:\\Users\\administrator\\Downloads\\H745_A16.EXE",reboot="yes"), this example will reboot the server now to update H745 storage controller.""")
    elif get_fw_inventory:
        logging.info("\n- INFO, getting current firmware inventory for iDRAC %s -\n" % creds["idrac_ip"])
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("- INFO, GET command passed to get firmware inventory")
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        for i in data['Members']:
            pprint(i)
            print("\n")
    elif fw_image_path:
        start_time = datetime.now()
        print("\n- INFO, downloading update package to create update job, this may take a few minutes depending on firmware image size")
        url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % creds["idrac_ip"]
        if reboot.lower() == "yes":
            payload = {"Targets": [], "@Redfish.OperationApplyTime": "Immediate", "Oem": {}}
        elif reboot.lower() == "no":
            payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
        else:
            payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
        files = {"UpdateParameters": (None, json.dumps(payload), "application/json"),
             "UpdateFile": (os.path.basename(fw_image_path), open(fw_image_path, "rb"), "application/octet-stream")}
        if x_auth_token == "yes":
            headers = {'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, files=files, headers=headers, verify=creds["verify_cert"])
        else:
            response = requests.post(url, files=files, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("- PASS, POST command passed for multipart upload")
        else:
            data = response.json()
            logging.error("- FAIL, status code %s returned, detailed error: %s" % (response.status_code,data))
            return
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in header")
            return
        logging.info("- PASS, update job ID %s successfully created, script will now loop polling the job status\n" % job_id)
        retry_count = 1
        while True:
            if retry_count == 20:
                logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
                return
            try:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            except requests.ConnectionError as error_message:
                logging.info("- INFO, GET request failed due to connection error, retry")
                time.sleep(10)
                retry_count += 1
                continue
            data = response.json()
            if response.status_code == 200 or response.status_code == 202:
                logging.info("- PASS, GET command passed to get job status details")
            else:
                logging.error("- FAIL, GET command failed to get job ID details, status code %s returned, detailed error: %s" % (response.status_code, data))
                return
            if data["TaskState"] == "Completed":
                logging.info("\n- INFO, job ID marked completed, detailed final job status results:\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0],i[1]))
                logging.info("\n- JOB ID %s completed in %s" % (job_id, current_time))
                return
            current_time = str(datetime.now()-start_time)[0:7]   
            data = response.json()
            message_string = data["Messages"]
            if str(current_time)[0:7] >= "0:30:00":
                logging.error("\n- FAIL: Timeout of 30 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
                return
            elif "failed" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Failed" in data['Oem']['Dell']['Message']:
                logging.error("- FAIL: Job failed, current message is: %s" % data["Messages"])
                return
            elif "scheduled" in data['Oem']['Dell']['Message']:
                logging.error("- PASS, job ID %s successfully marked as scheduled" % data["Id"])
                if reboot.lower() == "yes":
                    logging.info("- INFO, user selected to reboot the server now to apply the update")
                    loop_job_status_final()
                    return
                elif reboot.lower() == "no":
                    logging.info("- INFO, user selected to NOT reboot the server now. Update job is still scheduled and will be applied on next manual server reboot")
                    return
                else:
                    logging.warning("- WARNING, missing reboot argument for rebooting the server. Update job is still scheduled and will be applied on next manual server reboot")
                    return
            elif "completed successfully" in data['Oem']['Dell']['Message']:
                logging.info("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data["Id"])
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0],i[1]))
                logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                break
            else:
                logging.info("- INFO, job status: %s" % message_string[0]["Message"].rstrip("."))
                time.sleep(1)
                continue
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
            
def set_next_onetime_boot_device(script_examples="", get_supported_devices="", set_onetime_boot="", uefi_device_path="", get_uefi_device_paths="", reboot=""):
    """Function to either get supported onetime boot devices or set next onetime boot device. Supported function arguments: get_supported_devices (supported value: True), set_onetime_boot (pass in device string name and make sure to use exact case as returned from get_supported_devices), uefi_device_path (pass in uefi device target string), get_uefi_device_paths (supported value: True) and reboot (supported values: yes and no). If you do not reboot the now, onetime boot flag is still set and will boot to this device on next manual server reboot."""
    if script_examples:
        print("""\n- IdracRedfishSupport.set_next_onetime_boot_device(get_supported_devices=True), this example will return supported devices for setting next onetime boot device along with current onetime boot setting.
        \n- IdracRedfishSupport.set_next_onetime_boot_device(set_onetime_boot="Cd", reboot="yes"), this example will set next onetime boot device to Cd and reboot the server now.
        \n- IdracRedfishSupport.set_next_onetime_boot_device(set_onetime_boot="UefiTarget", uefi_device_path="3A191845-5F86-4E78-8FCE-C4CFF59F9DAA", reboot="no"), this example will set next onetime boot to UEFI device target path. Server will not reboot now but flag is still set, onetime boot will occur on next server manual reboot.""")
    elif get_supported_devices:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("- INFO, GET command passed to get system information")
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        logging.info("\n-Supported values for next server reboot, one time boot:\n")
        for i in data['Boot']['BootSourceOverrideTarget@Redfish.AllowableValues']:
          print(i)
        logging.info("\n- INFO, next server reboot onetime boot setting currently set to \"%s\"" % data['Boot']['BootSourceOverrideTarget'])
        return
    elif get_uefi_device_paths:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
            return
        else:
            pass
        data = response.json()
        if data["Members"] == []:
            logging.warning("- WARNING, no boot devices detected in the boot order")
            return
        print("\n")
        for i in data["Members"]:
            for ii in i.items():
                if ii[0] == "DisplayName" or ii[0] == "Id" or ii[0] == "UefiDevicePath":
                    print("%s: %s" % (ii[0], ii[1]))
            print("\n")
    elif set_onetime_boot:
        url = "https://%s/redfish/v1/Systems/System.Embedded.1" % creds["idrac_ip"]
        if set_onetime_boot == "UefiTarget" and uefi_device_path:
          payload = {"Boot":{"BootSourceOverrideTarget":set_onetime_boot,"UefiTargetBootSourceOverride":uefi_device_path}}
        else:
          payload = {"Boot":{"BootSourceOverrideTarget":set_onetime_boot}}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        time.sleep(5)
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            if set_onetime_boot == "UefiTarget" and uefi_device_path:
                logging.info("\n- PASS: PATCH command passed to set UEFI target path to \"%s\" and next boot onetime boot device to \"%s\"" % (uefi_device_path, set_onetime_boot))
            else:
                logging.info("\n- PASS, PATCH command passed to set next boot onetime boot device to \"%s\"" % set_onetime_boot)
            if reboot == "yes":
                logging.info("- INFO, user selected to reboot the server now to onetime boot to device %s" % set_onetime_boot)
                reboot_server()
            elif reboot == "no":
                logging.info("- INFO, user selected to not reboot the server now. Set onetime boot is still set to %s and will boot to this device on next manual server reboot." % set_onetime_boot)
            else:
                logging.info("- INFO, reboot argument not detected. Set onetime boot is still set to %s and will boot to this device on next manual server reboot." % set_onetime_boot)
        else:
          logging.error("\n- FAIL, Command failed, errror code is %s" % response.status_code)
          detail_message = str(response.__dict__)
          logging.error(detail_message)
          return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    
def export_import_iDRAC_license(script_examples="", get_license_info="", get_network_share_types="", license_id="", export_license="", import_license="", delete_license="", share_ip="", share_type="", share_name="", share_username="", share_password="", license_filename="", ignore_certwarning=""):
    """Function to manage iDRAC licenses, either get license info, export/import license using local/network share or delete license. Supported function arguments: get_license_info (supported value: True), get_network_share_types (supported value: True), export_license (supported value: True). Note: Export locally, license will be in base64 string format. Export to network share, license will be in XML format., import_license (supported value: True). Note: If you import license locally, the license file must be either in base64 string format or XML extension. If you import from network share license must be in XML format, delete_license (supportd value: True), license_id (pass in license ID string which is needed for export and delete), share_ip, share_type, share_name, share_username (only required for CIFS and HTTP/HTTPS using auth), share_password (only required for CIFS and HTTP/HTTPS using auth), ignore_certwarning (only optional for HTTPS) and license_filename (required for import local, export to network share pass in an unique string name for the license file)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_import_iDRAC_license(get_license_info=True), this example will return installed iDRAC license details. Id details for each license will be returned which this Id will be needed for export or delete operations.
        \n- IdracRedfishSupport.export_import_iDRAC_license(get_network_share_types=True), this example will return supported network share types for export/import licenses.
        \n- IdracRedfishSupport.export_import_iDRAC_license(license_id="FD00000021942269", share_type="local", export_license=True), this example will export iDRAC license locally. 
        \n- IdracRedfishSupport.export_import_iDRAC_license(license_id="5548PA_admin", export_license=True, share_type="NFS", share_ip="192.168.0.121", share_name="/nfs",license_filename="iDRAC_Enterprise_license.xml"), this example will export iDRAC license to NFS share.
        \n- IdracRedfishSupport.export_import_iDRAC_license(import_license=True, share_type="NFS", share_ip="192.168.0.121", share_name="/nfs",license_filename="iDRAC_Enterprise_license.xml"), this example will import iDRAC license from NFS share.
        \n- IdracRedfishSupport.export_import_iDRAC_license(license_id="FD00000021942269", delete_license=True), this example will delete iDRAC license with Id FD00000021942269.""")
    elif get_license_info:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.info("\n- FAIL, GET command failed to find iDRAC license data, error is: %s" % response)
            return
        data = response.json()
        if data['Members'] == []:
            logging.warning("\n- WARNING, no licenses detected for iDRAC %s" % creds["idrac_ip"])
        else:
            print("\n- License(s) detected for iDRAC %s -\n" % creds["idrac_ip"])
            for i in (data['Members']):
                pprint(i)
                print("\n")
    elif get_network_share_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to get supported network share types, error is: %s" % response)
            return
        data = response.json()
        logging.info("\n- Supported network share types for Export / Import license from network share -\n")
        for i in data['Actions']['#DellLicenseManagementService.ExportLicenseToNetworkShare']['ShareType@Redfish.AllowableValues']:
            print(i)
        print("LOCAL")
    elif share_type.lower() == "local" and export_license and license_id:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicense' % (creds["idrac_ip"])
        method = "ExportLicense"
        payload={"EntitlementID":license_id}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        print("- iDRAC license for \"%s\" ID:\n" % license_id)
        print(data['LicenseFile'])
        with open("%s_iDRAC_license.txt" % license_id, "w") as x:
            x.writelines(data['LicenseFile'])
        logging.info("\n- License also copied to \"%s_iDRAC_license.txt\" file" % license_id)
    elif share_type.lower() == "local" and import_license and license_filename:
        try:
            filename_open = open(license_filename, "r")
        except:
            logging.error("\n- FAIL, unable to locate filename \"%s\"" % license_filename)
            return
        name, extension = os.path.splitext(license_filename)
        if extension.lower() == ".xml":
            with open(license_filename, 'rb') as cert:
                cert_content = cert.read()
                read_file = base64.encodebytes(cert_content).decode('ascii')
        else:
            read_file = filename_open.read()
        filename_open.close()
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ImportLicense' % (creds["idrac_ip"])
        payload = {"FQDD":"iDRAC.Embedded.1","ImportOptions":"Force","LicenseFile":read_file}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS, license filename \"%s\" successfully imported" % license_filename)
        else:
            data = response.json()
            logging.error("\n- FAIL, unable to import license filename \"%s\", status code %s, error results: \n%s" % (license_filename, response.status_code, data))
            return
    elif delete_license and license_id:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.DeleteLicense' % (creds["idrac_ip"])
        method = "DeleteLicense"
        payload={"EntitlementID":license_id,"DeleteOptions":"Force"}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return 
    else:
        if export_license:
            method = "ExportLicenseToNetworkShare"
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicenseToNetworkShare' % (creds["idrac_ip"])
            payload = {"EntitlementID":license_id}
        elif import_license:
            method = "ImportLicenseFromNetworkShare"
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ImportLicenseFromNetworkShare' % (creds["idrac_ip"])
            payload = {"FQDD":"iDRAC.Embedded.1","ImportOptions":"Force"}
        if license_filename:
            payload["LicenseName"] = license_filename
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if ignore_certwarning:
            payload["IgnoreCertificateWarning"] = ignore_certwarning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            return
        logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
        start_time = datetime.now()
        time.sleep(3)
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id),verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            current_time=(datetime.now()-start_time)
            if response.status_code == 200:
                logging.info("- PASS, GET command passed to get job status details")
            else:
                logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(req.json()))
                return
            data = response.json()
            if str(current_time)[0:7] >= "0:05:00":
                logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                return
            elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
                logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
                return
            elif data['JobState'] == "Completed":
                if data['Message'] == "The command was successful":
                    logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                else:
                    logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                logging.info("- INFO, job status not completed, current job status execution time: \"%s\"" % (str(current_time)[0:7]))
                
def generate_replace_iDRAC_CSR(script_examples="", get_current_certs="", generate_CSR="", city="", state="", country="", common_name="", org="", orgunit="", email="", replace_CSR="", CSR_filename=""):
    """Function to either get current iDRAC certs or generate new CSR. Supported function arguments: get_current_certs (possible value: True), generate_CSR (possible value: True), city, state, country, common_name, org, orgunit, email (optional), replace_CSR (pass in the cert ID of the cert you want to replace. If needed, execute IdracRedfishSupport.generate_iDRAC_CSR(get_current_certs=True) to get the cert ID. Example: SecurityCertificate.1), CSR_filename (pass in name of signed CSR filename)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.generate_replace_iDRAC_CSR(get_current_certs=True), this example will return current iDRAC certificates.
        \n- IdracRedfishSupport.generate_replace_iDRAC_CSR(generate_CSR=True, city="Austin", state="Texas", country="US", email="tester@dell.com", org="PG", orgunit="test", common_name="product test"), this example shows generating new iDRAC CSR.
        \n- IdracRedfishSupport.generate_replace_iDRAC_CSR(replace_CSR="SecurityCertificate.1", CSR_filename="signed_CSR_cert.cer"), this example will replace cert Id SecurityCertificate.1 with new signed CSR cert file.""")
    elif get_current_certs:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("- PASS, GET command passed to check iDRAC cert details")
        else:
            logging.error("\n- INFO, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
            return
        if data["Members"] == []:
            logging.info("- INFO, no current certs detected for iDRAC %s" % idrac_ip)
        else:
            for i in data["Members"]:
                for ii in i.items():
                    print("\n- Details for cert \"%s\"\n" % ii[1].split("/")[-1])
                    if x_auth_token == "yes":
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], ii[1]), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], ii[1]), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
                    for i in data.items():
                        pprint(i)
                    print("\n")
    elif generate_CSR:
        logging.info("\n- INFO, generating CSR for iDRAC %s, this may take a few seconds to complete\n" % creds["idrac_ip"])
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.warning("\n- WARNING, unable to get iDRAC version, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
            return
        url = 'https://%s/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR' % creds["idrac_ip"]
        if int(data["FirmwareVersion"].replace(".","")) >= 5000000:
            payload = {"CertificateCollection":{"@odata.id":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates"},"City":city,"CommonName":common_name,"Country":country,"Organization":org,"OrganizationalUnit":orgunit,"State":state}
        else:
            payload = {"CertificateCollection":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates","City":city,"CommonName":common_name,"Country":country,"Organization":org,"OrganizationalUnit":orgunit,"State":state}   
        if email:
            payload["Email"] = email
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data_post = response.json()
        if response.status_code != 200:
            logging.error("- FAIL, generate CSR failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data_post))
            return
        logging.info("\n- INFO, CSR generated for iDRAC %s\n" % creds["idrac_ip"])
        logging.info(data_post["CSRString"])
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data_get = response.json()
        if response.status_code == 200:
            model_name = data_get["Model"].replace(" ","")
            service_tag = data_get["SKU"]
            filename = model_name+"_"+service_tag+".csr"
        else:
            logging.info("-INFO, unable to get model and service tag information, using iDRAC IP for filename")
            filename = "%s.csr" % creds["idrac_ip"]
        try:
            os.remove(filename)
        except:
            pass
        with open(filename, "a") as x:
            x.writelines(data_post["CSRString"])
        logging.info("\n- Generated CSR also copied to file \"%s\"" % filename)
    elif replace_CSR:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.warning("\n- WARNING, unable to get iDRAC version, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
            return
        url = 'https://%s/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate' % (creds["idrac_ip"])
        try:
            open_filename = open(CSR_filename,"r")
        except:
            logging.error("- FAIL, unable to locate file \"%s\"" % CSR_filename)
            return
        read_file = open_filename.read()
        open_filename.close()
        if int(data["FirmwareVersion"].replace(".","")) >= 5000000:
            payload = {"CertificateType": "PEM","CertificateUri":{"@odata.id":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates/%s" % replace_CSR},"CertificateString":read_file}
        else:
            payload = {"CertificateType": "PEM","CertificateUri":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates/%s" % replace_CSR,"CertificateString":read_file}   
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS, replace CSR cert passed. iDRAC reset is needed for new cert to get applied.")
        else:
            logging.error("- FAIL, replace CSR failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
            return
        user_response = str(input("- Reboot iDRAC now to apply new CSR cert, pass in \"y\" or \"n\": " ))
        if user_response.lower() == "n":
            logging.warning("- WARNING, iDRAC will not reboot now to replace CSR. Next iDRAC manual reboot CSR will be replaced")
            return
        else:   
            url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % creds["idrac_ip"]
            payload={"ResetType":"GracefulRestart"}
            if x_auth_token == "yes":
                headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
            if response.status_code == 204:
                logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC\n" % response.status_code)
            else:
                data = response.json()
                logging.error("\n- FAIL, status code %s returned, detailed error is: \n%s" % (response.status_code, data))
                return
            time.sleep(15)
            logging.info("- INFO, iDRAC will now reset and be back online within a few minutes.")
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def export_import_iDRAC_certs(script_examples="", get_current_certs="", get_cert_types="", export_cert="", import_cert="", cert_filename="", cert_passphrase=""):
    """Function to either get current iDRAC certificates or export/import certificates. Supported function arguments: export_cert (get possible values from get_cert_types argument), import_cert (get possible values from get_cert_types argument), cert_filename (pass in the name of the cert file to import which must be in base64 string format) and cert_passphrase (pass in passphrase if cert is protected for import)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_import_iDRAC_certs(get_current_certs=True), this example will return current iDRAC certs installed.
        \n- IdracRedfishSupport.export_import_iDRAC_certs(get_cert_types=True), this example will return current supported cert type values for export/import cert operations. 
        \n- IdracRedfishSupport.export_import_iDRAC_certs(export_cert="Server"), this example will export iDRAC server cert.
        \n- IdracRedfishSupport.export_import_iDRAC_certs(import_cert="ClientTrustCertificate", cert_filename="signed_cert.pem"), this example will import client trust cert signed pem file.""")
    elif get_current_certs:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("- PASS, GET command passed to check iDRAC cert details")
        else:
            logging.info("\n- INFO, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
            return
        if data["Members"] == []:
            logging.info("- INFO, no current certs detected for iDRAC %s" % idrac_ip)
        else:
            for i in data["Members"]:
                for ii in i.items():
                    print("\n- Details for cert \"%s\"\n" % ii[1].split("/")[-1])
                    if x_auth_token == "yes":
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], ii[1]), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s%s' % (creds["idrac_ip"], ii[1]), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
                    for i in data.items():
                        pprint(i)
    elif get_cert_types:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- ERROR, GET commmand failed to get cert types supported for export/import cert operations, status code %s returned" % response.status_code)
            logging.error("- Detailed error results: %s" % data)
            return
        for i in data["Actions"].items():
            if i[0] == "#DelliDRACCardService.ExportSSLCertificate":
                logging.info("\n- Support cert type values for ExportSSLCertificate -\n")
                for ii in i[1].items():
                    if ii[0] == "SSLCertType@Redfish.AllowableValues":
                        print(ii[1])
            if i[0] == "#DelliDRACCardService.ImportSSLCertificate":
                logging.info("\n- Support cert type values for ImportSSLCertificate -\n")
                for ii in i[1].items():
                    if ii[0] == "CertificateType@Redfish.AllowableValues":
                        print(ii[1])
    elif export_cert:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (creds["idrac_ip"])
        method = "ExportSSLCertificate"
        payload={"SSLCertType":export_cert}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            logging.error("\n- POST command failure results:\n %s" % data)
            return
        logging.info("\n- Detailed SSL certificate information for certificate type \"%s\"\n" % export_cert)
        logging.info(data['CertificateFile'])
        try:
            os.remove("%s_certificate.txt" % export_cert)
        except:
            pass
        with open("%s_certificate.txt" % export_cert,"w") as x:
            x.writelines(data['CertificateFile'])
        logging.info("\n - SSL certificate information also copied to \"%s\%s_certificate.txt\" file" % (os.getcwd(), export_cert))
    elif import_cert:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ImportSSLCertificate' % (creds["idrac_ip"])
        method = "ImportSSLCertificate"
        if "p12" in cert_filename:
            with open(cert_filename, 'rb') as cert:
                cert_content = cert.read()
                read_file = base64.encodebytes(cert_content).decode('ascii')
        else:
            open_cert_file = open(cert_filename,"r")
            read_file = open_cert_file.read()
            open_cert_file.close()
        payload={"CertificateType":import_cert,"SSLCertificateFile":read_file}
        if cert_passphrase:
            payload["Passphrase"] = cert_passphrase
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS: POST command passed for %s method, status code 202 returned\n" % method)
            user_response = input(str("- INFO, iDRAC reboot is needed to apply the new certificate, pass in \"y\" to reboot iDRAC now or \"n\" to not reboot: "))
            if user_response.lower() == "n":
                return
            elif user_response.lower() == "y":
                url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % creds["idrac_ip"]
                payload={"ResetType":"GracefulRestart"}
                headers = {'content-type': 'application/json'}
                if x_auth_token == "yes":
                    headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
                if response.status_code == 204:
                    logging.info("\n- PASS, status code %s returned for POST command to reboot iDRAC\n" % response.status_code)
                else:
                    data = response.json()
                    logging.error("\n- FAIL, status code %s returned, detailed error: \n%s" % (response.status_code, data))
                    return
                time.sleep(15)
                logging.info("- INFO, iDRAC will now reboot and be back online within a few minutes.")
            else:
                logging.error("- ERROR, invalid value entered for user response")
                                  
        else:
            logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def create_delete_iDRAC_subscriptions(script_examples="", get_subscriptions="", create_subscription="", destination_uri="", event_format_type="", event_type="", submit_test_event="", delete_subscription_uri="", message_id=""):
    """Function to either get current iDRAC subscriptions, create new subscription, submit test event to a location or delete subscription. Supported function arguments: get_subscriptions(supported value: True), create_subscription(supported value: True), destination_uri (pass in complete HTTPS URI path), event_format_type(supported values: Event, MetricReport or None), event_type(supported values: StatusChange, ResourceUpdated, ResourceAdded, ResourceRemoved, Alert, MetricReport), submit_test_event(possible value: True), message_id (pass in the message ID to submit test event, example: PDR1101) and delete_subscription_uri (pass in complete subscription URI. If needed execute IdracRedfishSupport.create_delete_iDRAC_subscriptions(get_subscriptions=True) to get subscription URIs). """
    if script_examples:
        print("""\n- IdracRedfishSupport.create_delete_iDRAC_subscriptions(get_subscriptions=True), this example will return current iDRAC subscription details.
        \n- IdracRedfishSupport.create_delete_iDRAC_subscriptions(create_subscription=True, destination_uri="https://192.168.0.140", event_format_type="Event", event_type="Alert"), this example shows creating a subscription.
        \n- IdracRedfishSupport.create_delete_iDRAC_subscriptions(submit_test_event=True, destination_uri="https://192.168.0.140", event_type="Alert", message_id="TMP0118"), this example shows submitting a test event to subscription destination https://192.168.0.140.
        \n- IdracRedfishSupport.create_delete_iDRAC_subscriptions(delete_subscription_uri="/redfish/v1/EventService/Subscriptions/e507a4bc-ac8a-11ec-ad0d-b07b25d2e318"), this example shows deleting subscription.""")
    elif get_subscriptions:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/EventService/Subscriptions?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/EventService/Subscriptions?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS, status code %s returned for GET command to get subscription details." % response.status_code)
        else:
            data = response.json()
            logging.info("\n- FAIL, status code %s returned for GET command, detailed error: \n%s" % (response.status_code, data))
            return
        data = response.json()
        if data["Members"] == []:
            loggin.warning("\n- WARNING, no subscriptions detected for iDRAC %s" % creds["idrac_ip"])
            return
        else:
            logging.info("\n- INFO, subscriptions detected for iDRAC ip %s\n" % creds["idrac_ip"])
        for i in data["Members"]:
            pprint(i)
            print("\n")

    elif create_subscription:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200:
            logging.info("\n- PASS, status code %s returned for GET command to get iDRAC attributes" % response.status_code)
        else:
            data = response.json()
            logging.error("\n- FAIL, status code %s returned for GET command, detailed error: \n%s" % (response.status_code, data))
            return
        data = response.json()
        while True:
            try:
                attributes_dict = data['Attributes']
            except:
                logging.info("\n- INFO, iDRAC version detected does not support PATCH to set iDRAC attributes, executing Server Configuration Profile feature set iDRAC attribute \"IPMILan.1#AlertEnable\" locally\n")
                url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
                payload = {"ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"IPMILan.1#AlertEnable\">Enabled</Attribute></Component></SystemConfiguration>","ShareParameters":{"Target":"All"}}
                if x_auth_token == "yes":
                    headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
                create_dict = str(response.__dict__)
                try:
                    job_id_search = re.search("JID_.+?,",create_dict).group()
                except:
                    logging.error("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
                    return

                job_id = re.sub("[,']","",job_id_search)
                if response.status_code != 202:
                    logging.error("\n- FAIL, status code not 202\n, status code: %s" % response.status_code)  
                    return
                else:
                    logging.info("- INFO, job ID %s successfully created for ImportSystemConfiguration method\n" % (job_id))
                response_output = response.__dict__
                job_id = response_output["headers"]["Location"]
                job_id = re.search("JID_.+",job_id).group()
                while True:
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = req.json()
                    message_string = data["Messages"]
                    final_message_string = str(message_string)
                    if statusCode == 202 or statusCode == 200:
                        logging.info("- INFO, GET command passed to get job ID details")
                        time.sleep(1)
                    else:
                        logging.error("- FAIL, GET job ID command failed, status code %s returned" % response.status_code)
                        return
                    if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string:
                        logging.error("\n- FAIL, detailed job message: %s" % data["Messages"])
                        return
                    elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully imported" in final_message_string:
                        logging.info("- Job ID = "+data["Id"])
                        logging.info("- Name = "+data["Name"])
                        try:
                            logging.info("- Message = \n"+message_string[0]["Message"])
                        except:
                            logging.info("- Message = %s\n" % message_string[len(message_string)-1]["Message"])
                        break
                    elif "No changes" in final_message_string:
                        logging.info("- Job ID = "+data["Id"])
                        logging.info("- Name = "+data["Name"])
                        try:
                            logging.info("- Message = " + message_string[0]["Message"])
                        except:
                            logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
                            return
                        break
                    else:
                        logging.info("- Job not marked completed, current status is: %s" % data["TaskState"])
                        logging.info("- Message: %s\n" % message_string[0]["Message"])
                        time.sleep(1)
                        continue
            logging.info("- INFO, checking current value for iDRAC attribute \"IPMILan.1.AlertEnable\"")
            if attributes_dict["IPMILan.1.AlertEnable"] == "Disabled":
                logging.info("- INFO, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" is set to Disabled, setting value to Enabled")
                payload = {"Attributes":{"IPMILan.1.AlertEnable":"Enabled"}}
                url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % creds["idrac_ip"]
                if x_auth_token == "yes":
                    headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
                    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
                if response.status_code == 200:
                    logging.error("- PASS, PATCH command passed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                else:
                    logging.error("- FAIL, PATCH command failed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                    return
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
                data = response.json()
                attributes_dict=data['Attributes']
                if attributes_dict["IPMILan.1.AlertEnable"] == "Enabled":
                    logging.info("- PASS, iDRAC attribute \"IPMILan.1.AlertEnable\" successfully set to Enabled")
                    break
                else:
                    logging.error("- FAIL, iDRAC attribute \"IPMILan.1.AlertEnable\" not set to Enabled")
                    return
            else:
                logging.info("- INFO, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" already set to Enabled, ignore PATCH command")
                break
        url = "https://%s/redfish/v1/EventService/Subscriptions" % creds["idrac_ip"]
        payload = {"Destination": destination_uri,"EventTypes": [event_type],"Context": "root","Protocol": "Redfish", "EventFormatType":event_format_type}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.__dict__["status_code"] == 201:
            logging.info("- PASS, POST command passed to create iDRAC subscription")
        else:
            logging.error("- FAIL, POST command failed, status code %s returned, error: %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
            return
    elif submit_test_event:
        payload = {"Destination": destination_uri,"EventTypes": event_type,"Context": "Root","Protocol": "Redfish","MessageId":message_id}
        url = "https://%s/redfish/v1/EventService/Actions/EventService.SubmitTestEvent" % creds["idrac_ip"]
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.__dict__["status_code"] == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.__dict__["status_code"] == 200 or response.__dict__["status_code"] == 202 or response.__dict__["status_code"] == 204:
            logging.info("\n- PASS, POST command passed to submit subscription test event")
        else:
            logging.error("\n- FAIL, POST command failed to submit subscription test event, status code %s returned, error: %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
            return
    elif delete_subscription_uri:
        url = "https://%s%s" % (creds["idrac_ip"], delete_subscription_uri)
        headers = {'content-type': 'application/json'}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.delete(url, headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.__dict__["status_code"] == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.__dict__["status_code"] == 200:
            logging.info("\n- PASS, DELETE command passed to delete subscription")
        else:
            logging.error("\n- FAIL, DELETE command failed and returned status code %s, error: %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
            return
        

def export_import_server_configuration_profile_local(script_examples="", export_profile="", export_format="", targets="", export_use="", include_in_export="", import_profile="", import_filename="", shutdown_type="", end_host_powerstate=""):
    """Function to export or import server configuration profile (SCP) locally. Supported function arguments: export_profile (supported value: True), export_format (supported values: XML or JSON), targets (supported values: ALL, IDRAC, BIOS, NIC, FC, RAID, System, LifecycleController, EventFilters) Note, you can pass in one or multiple values. If passing in multiple values, use comma separator with no whitespace. export_use (supported value: Clone) Note: Argument is optional, if not used iDRAC will export as default. include_in_export (supported_values: IncludeReadOnly or IncludePasswordHashValues) Note: If you pass in multiple values, use comma separator with no whitespace. Argument is optional, if not used iDRAC will export as default. import_profile (supported value: True), import_filename (pass in SCP filename), shutdown_type (supported values: Forced, Graceful and NoReboot). Note: optional, if not passed in server will perform graceful. end_host_powerstate (possible values: On and Off). Note: optional, if not used default value is On."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_import_server_configuration_profile_local(export_profile=True, export_format=\"JSON\", targets=\"IDRAC\"), this example will export normal SCP file in JSON format which only includes iDRAC attributes.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_local(export_profile=True, export_format=\"XML\", targets=\"LifecycleController,System\", export_use=\"Clone\"), this example will export clone SCP file in XML format which only includes LifecycleController and Syatem attributes.  
        \n- IdracRedfishSupport.export_import_server_configuration_profile_local(export_profile=True, export_format=\"XML\", targets=\"BIOS\", include_in_export=\"IncludeReadOnly\"), this example will export normal SCP file in XML format which includes only BIOS attributes and also read only attributes for BIOS.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_local(import_profile=True, targets=\"IDRAC\", import_filename=\"2022-2-18_162941_export.xml\"), this example will import SCP file which will only configure iDRAC attributes if changes detected.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_local(import_profile=True, targets=\"ALL\", import_filename=\"2022-2-18_162941_export.xml\", shutdown_type=\"Forced\"), this example will import SCP file which will configure all component attributes if changes detected. Server will also perform a forced reboot to apply the changes.\n""")
        return
    if export_profile and export_format and targets:
        targets = targets.replace(" ","")
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % creds["idrac_ip"]
        payload = {"ExportFormat":export_format.upper(),"ShareParameters":{"Target":targets}}
        if export_use:
            payload["ExportUse"] = export_use
        if include_in_export:
            payload["IncludeInExport"] = include_in_export
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 202:
            logging.info("- PASS, POST command passed for ExportSystemConfiguration action")
        else:
            logging.error("- FAIL, status code not 202, status code %s returned" % response.status_code)
            logging.error("- Error details: %s" % response.__dict__)
            return
        response_output = response.__dict__
        try:
            job_id = response_output["headers"]["Location"].split("/")[-1]
        except:
            logging.error("\n- FAIL: detailed error message: %s" % response_output)
            return
        logging.info("- PASS, job ID %s successfully created" % job_id)
        start_time = datetime.now()
        while True:
            current_time = (datetime.now()-start_time)
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            dict_output = response.__dict__
            if export_format.upper() == "XML":
                if "<SystemConfiguration Model" in str(dict_output):
                    print("\n- Export locally job ID %s successfully completed. Attributes exported:\n" % job_id)
                    regex_search = re.search("<SystemConfiguration.+</SystemConfiguration>",str(dict_output)).group()
                    try:
                        security_string = re.search('<Attribute Name="GUI.1#SecurityPolicyMessage">.+?>', regex_search).group()
                    except:
                        pass
                    #Below code is needed to parse the string to set up in pretty XML format
                    replace_variable = regex_search.replace("\\n"," ")
                    replace_variable = replace_variable.replace("<!--  ","<!--")
                    replace_variable = replace_variable.replace(" -->","-->")
                    del_attribute = '<Attribute Name="SerialRedirection.1#QuitKey">^\\\\</Attribute>'
                    try:
                        replace_variable = replace_variable.replace(del_attribute,"")
                    except:
                        pass
                    try:
                        replace_variable = replace_variable.replace(security_string,"")
                    except:
                        pass
                    create_list = replace_variable.split("> ")
                    export_xml = []
                    for i in create_list:
                        create_string = i+">"
                        export_xml.append(create_string)
                    export_xml[-1] = "</SystemConfiguration>"
                    get_date_info = datetime.now()
                    filename = "%s-%s-%s_%s%s%s_export.xml"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                    open_file = open(filename,"w")
                    for i in export_xml:
                        open_file.writelines("%s \n" % i)
                    open_file.close()
                    for i in export_xml:
                        print(i)
                    print("\n")
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
                    logging.info("\n- PASS, final detailed job status results for job ID %s -\n" % job_id)
                    for i in data.items():
                        print("%s: %s" % (i[0],i[1]))
                    logging.info("\n- Exported attributes also saved in file: %s" % filename)
                    return
                else:
                    pass
            elif export_format.upper() == "JSON":
                if "SystemConfiguration" in str(dict_output):
                    data = response.json()
                    json_format = json.dumps(data)
                    get_date_info = datetime.now()
                    filename = "%s-%s-%s_%s%s%s_export.json"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                    open_file = open(filename,"w")
                    open_file.write(json.dumps(json.loads(json_format), indent=4))
                    open_file.close()
                    if x_auth_token == "yes":
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                    else:
                        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
                    logging.info("\n- PASS, final detailed job status results for job ID %s -\n" % job_id)
                    for i in data.items():
                        print("%s: %s" % (i[0],i[1]))
                    logging.info("\n- Exported attributes saved to file: %s" % filename)
                    return
                else:
                    pass
            data = response.json()
            try:
                message_string = data["Messages"]
            except:
                logging.info(response.status_code)
                logging.info(data)
                return
            current_time = (datetime.now()-start_time)

            if response.status_code == 202 or response.status_code == 200:
                logging.info("- PASS, GET command passed to get job ID details")
            else:
                logging.error("Execute job ID command failed, status code %s returned" % response.status_code)
                return
            if str(current_time)[0:7] >= "0:10:00":
                logging.error("\n-FAIL, Timeout of 10 minutes has been reached before marking the job completed.")
                return

            else:
                try:
                    logging.info("- INFO, job ID not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                    time.sleep(1)
                except:
                    logging.info("- INFO, unable to print job status message, trying again")
                    time.sleep(1)
                continue
    elif import_profile and import_filename:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        get_version = data['FirmwareVersion'].split(".")[:2]
        get_version = int("".join(get_version))
        try:
            open_file = open(import_filename,"r")
        except:
            print("\n-FAIL, \"%s\" file doesn't exist" % import_filename)
            return    
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % creds["idrac_ip"]
        # Code needed to modify the SCP file to one string to pass in for POST command
        modify_file = open_file.read()
        modify_file = re.sub(" \n ","",modify_file)
        modify_file = re.sub(" \n","",modify_file)
        file_string = re.sub("   ","",modify_file)
        open_file.close()
        targets = targets.replace(" ","")
        payload = {"ImportBuffer":"","ShareParameters":{"Target":targets}}
        if shutdown_type:
            payload["ShutdownType"] = shutdown_type
        if end_host_powerstate:
            payload["HostPowerState"] = end_host_powerstate
        payload["ImportBuffer"] = file_string
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        response_output = response.__dict__
        if response.status_code == 202:
            logging.info("- PASS, POST command passed for ImportSystemConfiguration action")
        else:
            logging.error("- FAIL, status code not 202, status code %s returned" % response.status_code)
            logging.error("- Error details: %s" % response.__dict__)
            return
        try:
            job_id = response_output["headers"]["Location"].split("/")[-1]
        except:
            logging.error("\n- FAIL: detailed error message: %s" % response_output)
            return
        logging.info("- PASS, job ID %s successfully created" % job_id)
        start_job_message = ""
        start_time = datetime.now()
        count = 1
        get_job_status_count = 1
        while True:
            if count == 10:
                logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
                return
            if get_job_status_count == 10:
                logging.info("- INFO, retry count of 10 has been hit for retry job status GET request, script will exit")
                return
            try:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
            except requests.ConnectionError as error_message:
                logging.error("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
                time.sleep(10)
                logging.info("- INFO, script will now attempt to get job status again")
                count += 1
                continue
            if response.status_code == 401:
                logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
                return
            data = response.json()
            try:
                current_job_message = data['Oem']['Dell']['Message']
            except:
                logging.info("- INFO, unable to get job ID message string from JSON output, retry")
                count +=1
                continue
            current_time = (datetime.now()-start_time)
            if response.status_code == 202 or response.status_code == 200:
                logging.info("- INFO, GET command passed to get job ID details")
                time.sleep(1)
            else:
                logging.error("- ERROR, query job ID command failed, error code: %s, retry" % statusCode)
                count += 1
                time.sleep(5)
                continue
            if "Oem" not in data:
                logging.info("- INFO, unable to locate OEM data in JSON response, retry")
                get_job_status_count += 1
                time.sleep(5)
                continue
            if data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
                logging.info("\n- INFO, job ID %s status marked as \"%s\"" % (job_id, data['Oem']['Dell']['JobState']))
                logging.info("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
                try:
                    for i in data["Messages"]:
                        for ii in i.items():
                            if ii[0] == "Oem":
                                for iii in ii[1]["Dell"].items():
                                    print("%s: %s" % (iii[0], iii[1]))
                            else:
                                if ii[0] == "Severity":
                                    pass
                                if get_version < 440:
                                    if ii[1] == "Critical":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Failure")
                                    elif ii[1] == "OK":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Success")
                                    else:
                                        print("%s: %s" % (ii[0], ii[1]))
                                        
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                        print("\n")
                except:
                    logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                        
                logging.info("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                return
            elif data['Oem']['Dell']['JobState'] == "Completed":
                if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                    print("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
                elif "success" in data['Oem']['Dell']['Message'].lower():
                    print("- PASS, job ID %s successfully marked completed\n" % job_id)
                elif "no changes" in data['Oem']['Dell']['Message'].lower():
                    print("\n- PASS, job ID %s marked completed\n" % job_id)
                    print("- Detailed job results for job ID %s\n" % job_id)
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                    return
                logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
                try:
                    for i in data["Messages"]:
                        for ii in i.items():
                            if ii[0] == "Oem":
                                for iii in ii[1]["Dell"].items():
                                    print("%s: %s" % (iii[0], iii[1]))
                            else:
                                if ii[0] == "Severity":
                                    pass
                                if get_version < 440:
                                    if ii[1] == "Critical":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Failure")
                                    elif ii[1] == "OK":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Success")
                                    else:
                                        print("%s: %s" % (ii[0], ii[1]))
                                        
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                        print("\n")
                except:
                    logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                        
                logging.info("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                return
            elif "No reboot Server" in data['Oem']['Dell']['Message']:
                logging.info("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
                logging.info("\n- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                return
            else:
                logging.info("- INFO, job not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                time.sleep(1)
                continue   
    else:
        logging.error("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return

def export_import_server_configuration_profile_network_share(script_examples="", export_profile="", export_format="", targets="", export_use="", include_in_export="", share_type="", share_ip="", share_name="", share_username="", share_password="", ignore_certwarning="", import_profile="", filename="", shutdown_type="", end_host_powerstate=""):
    """Function to export or import server configuration profile (SCP) using a network share. Supported function arguments: export_profile (supported value: True), export_format (supported values: XML or JSON), targets (supported values: ALL, IDRAC, BIOS, NIC, FC, RAID, System, LifecycleController, EventFilters) Note, you can pass in one or multiple values. If passing in multiple values, use comma separator with no whitespace. export_use (supported value: Clone) Note: Argument is optional, if not used iDRAC will export as default. include_in_export (supported_values: IncludeReadOnly or IncludePasswordHashValues) Note: If you pass in multiple values, use comma separator with no whitespace. Argument is optional, if not used iDRAC will export as default. share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_ip, share_name, share_username, share_password, ignore_certwarning (only valid for HTTPS and is optional, supported values On and Off), import_profile (supported value: True), filename (pass in unique SCP filename), shutdown_type (supported values: Forced, Graceful and NoReboot). Note: optional, if not passed in server will perform graceful. end_host_powerstate (possible values: On and Off). Note: optional, if not used default value is On."""
    if script_examples:
        print("""\n- IdracRedfishSupport.export_import_server_configuration_profile_network_share(export_profile=True, filename="R640_scp.json", export_format=\"JSON\", targets=\"IDRAC\", share_ip="192.168.0.130", share_name="/nfs", share_type="NFS"), this examples shows export normal SCP file in JSON format which only includes iDRAC attributes to NFS share.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_network_share(export_profile=True, filename="R640_scp.xml", export_format=\"XML\", targets=\"LifecycleController,System\", export_use=\"Clone\", share_ip="192.168.0.130", share_name="cifs_share", share_type="CIFS", share_username="admin", share_password="password"), this example shows export clone SCP file in XML format which only includes LifecycleController and Syatem attributes to CIFS share.  
        \n- IdracRedfishSupport.export_import_server_configuration_profile_network_share(export_profile=True, filename="R640_scp.xml", export_format=\"XML\", targets=\"BIOS\", include_in_export=\"IncludeReadOnly\", share_ip="192.168.0.130", share_name="https_share", share_type="HTTPS", ignore_certwarning="On"), this example shows export normal SCP file in XML format which includes only BIOS attributes and also read only attributes to HTTP share and ignore cert warning.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_network_share(import_profile=True, filename="R640_scp.xml", targets=\"IDRAC\", filename=\"R740_export.xml\", share_ip="192.168.0.130", share_name="http_share", share_type="HTTP"), this example shows import SCP file which will only configure iDRAC attributes if changes detected from HTTP share.
        \n- IdracRedfishSupport.export_import_server_configuration_profile_network_share(import_profile=True, filename="R640_scp.xml", targets=\"ALL\", filename=\"R740_export.xml\", shutdown_type=\"Forced\", share_ip="192.168.0.130", share_name="/nfs", share_type="NFS"), this example shows import SCP file which will configure all component attributes if changes detected from NFS share. Server will also perform a forced reboot to apply the changes.\n""")
        return
    if export_profile and export_format and targets and share_name and share_ip and share_type and filename:
        targets = targets.replace(" ","")
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % creds["idrac_ip"]
        payload = {"ExportFormat":export_format.upper(),"ShareParameters":{"Target":targets}}
        if export_use:
            payload["ExportUse"] = export_use
        if include_in_export:
            payload["IncludeInExport"] = include_in_export
        if share_ip:
            payload["ShareParameters"]["IPAddress"] = share_ip
        if share_type:
            payload["ShareParameters"]["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareParameters"]["ShareName"] = share_name
        if filename:
            payload["ShareParameters"]["FileName"] = filename
        if share_username:
            payload["ShareParameters"]["Username"] = share_username
        if share_password:
            payload["ShareParameters"]["Password"] = share_password
        if ignore_certwarning:
            payload["ShareParameters"]["IgnoreCertificateWarning"] = ignore_certwarning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
                logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
                return
        elif response.status_code == 202:
            logging.info("- PASS, POST command passed for ExportSystemConfiguration action")
        else:
            logging.error("- FAIL, status code not 202, status code %s returned" % response.status_code)
            logging.error("- Error details: %s" % response.__dict__)
            return
        response_output = response.__dict__
        try:
            job_id = response_output["headers"]["Location"].split("/")[-1]
        except:
            logging.error("\n- FAIL: detailed error message: %s" % response_output)
            return
        logging.info("- PASS, job ID %s successfully created" % job_id)
        start_time = datetime.now()
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                data = response.json()
            current_time = (datetime.now()-start_time)
            if response.status_code != 200:
                logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(req.json()))
                return
            data = response.json()
            if str(current_time)[0:7] >= "0:05:00":
                logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
                return
            elif "fail" in data['Message'].lower() or "unable" in data['Message'].lower() or "not" in data['Message'].lower():
                logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                return
            elif data['JobState'] == "Completed":
                if data['Message'] == "Successfully exported Server Configuration Profile":
                    logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                else:
                    logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                logging.info("- INFO, job not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Message'],data['PercentComplete']))
                time.sleep(1)
    elif import_profile and filename and share_name and share_ip and share_type:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        get_version = data['FirmwareVersion'].split(".")[:2]
        get_version = int("".join(get_version)) 
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % creds["idrac_ip"]
        payload = {"ShareParameters":{"Target":targets}}
        if shutdown_type:
            payload["ShutdownType"] = shutdown_type
        if filename:
            payload["FileName"] = filename
        if end_host_powerstate:
            payload["HostPowerState"] = end_host_powerstate
        if share_ip:
            payload["ShareParameters"]["IPAddress"] = share_ip
        if share_type:
            payload["ShareParameters"]["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareParameters"]["ShareName"] = share_name
        if filename:
            payload["ShareParameters"]["FileName"] = filename
        if share_username:
            payload["ShareParameters"]["Username"] = share_username
        if share_password:
            payload["ShareParameters"]["Password"] = share_password
        if ignore_certwarning:
            payload["ShareParameters"]["IgnoreCertificateWarning"] = ignore_certwarning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        response_output = response.__dict__
        if response.status_code == 401:
                logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
                return
        elif response.status_code == 202:
            logging.info("- PASS, POST command passed for ImportSystemConfiguration action")
        else:
            logging.error("- FAIL, status code not 202, status code %s returned" % response.status_code)
            logging.error("- Error details: %s" % response.__dict__)
            return
        try:
            job_id = response_output["headers"]["Location"].split("/")[-1]
        except:
            logging.error("\n- FAIL: detailed error message: %s" % response_output)
            return
        logging.info("- PASS, job ID %s successfully created" % job_id)
        start_job_message = ""
        start_time = datetime.now()
        count = 1
        get_job_status_count = 1
        while True:
            if count == 10:
                logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
                return
            if get_job_status_count == 10:
                logging.info("- INFO, retry count of 10 has been hit for retry job status GET request, script will exit")
                return
            try:
                if x_auth_token == "yes":
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                else:
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                    data = response.json()
            except requests.ConnectionError as error_message:
                logging.error("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
                time.sleep(10)
                logging.info("- INFO, script will now attempt to get job status again")
                count += 1
                continue
            if response.status_code == 401:
                logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
                return
            data = response.json()
            try:
                current_job_message = data['Oem']['Dell']['Message']
            except:
                logging.info("- INFO, unable to get job ID message string from JSON output, retry")
                count += 1
                continue
            current_time = (datetime.now()-start_time)
            if response.status_code == 202 or response.status_code == 200:
                logging.info("- INFO, GET command passed to get job status details")
            else:
                logging.error("- ERROR, query job ID command failed, error code: %s, retry" % response.status_code)
                count += 1
                time.sleep(5)
                continue
            if "Oem" not in data:
                logging.info("- INFO, unable to locate OEM data in JSON response, retry")
                get_job_status_count += 1
                time.sleep(5)
                continue
            if data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
                logging.info("\n- INFO, job ID %s status marked as \"%s\"" % (job_id, data['Oem']['Dell']['JobState']))
                logging.info("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
                try:
                    for i in data["Messages"]:
                        for ii in i.items():
                            if ii[0] == "Oem":
                                for iii in ii[1]["Dell"].items():
                                    print("%s: %s" % (iii[0], iii[1]))
                            else:
                                if ii[0] == "Severity":
                                    pass
                                if get_version < 440:
                                    if ii[1] == "Critical":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Failure")
                                    elif ii[1] == "OK":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Success")
                                    else:
                                        print("%s: %s" % (ii[0], ii[1]))
                                        
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                        print("\n")
                except:
                    logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                        
                logging.info("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                return
            elif data['Oem']['Dell']['JobState'] == "Completed":
                if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                    logging.error("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
                elif "success" in data['Oem']['Dell']['Message'].lower():
                    logging.error("- PASS, job ID %s successfully marked completed\n" % job_id)
                elif "no changes" in data['Oem']['Dell']['Message'].lower():
                    logging.info("\n- PASS, job ID %s marked completed\n" % job_id)
                    logging.info("- Detailed job results for job ID %s\n" % job_id)
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                    return
                logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
                try:
                    for i in data["Messages"]:
                        for ii in i.items():
                            if ii[0] == "Oem":
                                for iii in ii[1]["Dell"].items():
                                    print("%s: %s" % (iii[0], iii[1]))
                            else:
                                if ii[0] == "Severity":
                                    pass
                                if get_version < 440:
                                    if ii[1] == "Critical":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Failure")
                                    elif ii[1] == "OK":
                                        print("%s: %s" % (ii[0], ii[1]))
                                        print("Status: Success")
                                    else:
                                        print("%s: %s" % (ii[0], ii[1]))
                                        
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                        print("\n")
                except:
                    logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0], i[1]))
                        
                logging.info("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                return        
            elif "No reboot Server" in data['Oem']['Dell']['Message']:
                logging.info("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
                logging.info("\n- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                return
            else:
                logging.info("- INFO, job not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                time.sleep(2)
                continue
    else:
        logging.error("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return

def preview_server_configuration_profile_local(script_examples="", profile_name=""):
    """Function to preview server configuration profile locally. Supported function parameters: script_examples (supported value: True) and profile_name (pass in the string name of your profile)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.preview_server_configuration_profile_local(profile_name="R640_SCP_export.xml"), this example will preview server configuration profile.\n""")
        return
    # Code to preview server configuration profile locally
    elif profile_name:
        try:
            file_open = open(profile_name,"r")
        except:
            logging.error("\n-FAIL, \"%s\" file doesn't exist" % profile_name)
            return
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfigurationPreview' % creds["idrac_ip"]
    
    # Code needed to modify XML or JSON to one string to pass in for POST command
    modify_file = file_open.read()
    modify_file = re.sub(" \n ","",modify_file)
    modify_file = re.sub(" \n","",modify_file)
    scp_file_string=re.sub("   ","",modify_file)
    file_open.close()
    
    payload = {"ImportBuffer":"","ShareParameters":{"Target":"ALL"}}
    payload["ImportBuffer"] = scp_file_string
    if x_auth_token == "yes":
        headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
    if response.status_code == 401:
        logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
        return
    elif response.status_code != 202:
        logging.error("\n- FAIL, status code %s returned" % response.status_code)
        logging.error(response.__dict__)
        return
    try:
        job_id = response.__dict__["headers"]["Location"].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in headers output. Check iDRAC job queue for job ID")
        return
    logging.info("\n- %s successfully created for ImportSystemConfigurationPreview method\n" % (job_id) )
    start_time = datetime.now()
    while True:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        message_string = data["Messages"]
        final_message_string = str(message_string)
        current_time = (datetime.now()-start_time)
        if response.status_code == 200:
            print("- PASS, job ID %s state marked completed\n" % job_id)
            print("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            logging.info("\n- Config results for job ID %s\n" % job_id)
            for i in data['Messages']:
                for ii in i.items():
                    print("%s: %s" % (ii[0], ii[1]))
            return
        elif response.status_code != 202:
            logging.error("- ERROR, query job ID command failed, error code: %s, error results: \n%s" % (response.status_code, data))
            return
        elif "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string or "not compliant" in final_message_string or "Unable to complete" in final_message_string or "The system could not be shut down" in final_message_string or "timed out" in final_message_string:
            logging.error("\n- FAIL, detailed job message: %s" % data["Messages"])
            return
        elif "No reboot Server" in final_message_string:
            try:
                logging.info("- Message = "+message_string[0]["Message"])
            except:
                logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
            return
        elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully previewed" in final_message_string or data["TaskState"] == "Completed":
            logging.info("- PASS, job ID %s state marked completed\n" % job_id)
            logging.info("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            logging.info("\n- Config results for job ID %s\n" % job_id)
            for i in data['Messages']:
                for ii in i.items():
                    print("%s: %s" % (ii[0], ii[1]))
            return
        elif "No changes" in final_message_string or "No configuration changes" in final_message_string:
            logging.info("- Job ID = "+data["Id"])
            logging.info("- Name = "+data["Name"])
            try:
                logging.info("- Message = "+message_string[0]["Message"])
            except:
                logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
            logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            return
        else:
            logging.info("- INFO, job not marked completed, current status: %s" % data["TaskState"])
            time.sleep(3)
            continue
    else:
        logging.error("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return

def preview_server_configuration_profile_network_share(script_examples="", profile_name="", share_ip="", share_name="", share_type="", share_username="", share_password="", ignore_certwarning=""):
    """Function to preview server configuration profile (SCP) from a network share. Supported function arguments: profile_name (pass in name of profile), share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_ip, share_name, share_username, share_password, ignore_certwarning (only valid for HTTPS and is optional, supported values On and Off)"""
    if script_examples:
        print("""\n- IdracRedfishSupport.preview_server_configuration_profile_network_share(profile_name="R640_scp_file.xml", share_ip="192.168.0.130", share_name="/nfs", share_type="NFS"), this example will preview SCP profile on NFS share.
        \n- IdracRedfishSupport.preview_server_configuration_profile_network_share(profile_name="R750_scp_file.json", share_ip="192.168.0.140", share_name="cifs_share", share_type="CIFS, share_username="admin", share_password="password"), this example will preview SCP profile on a CIFS share.""")
        return
    elif profile_name:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfigurationPreview' % creds["idrac_ip"]
        payload = {"ShareParameters":{"Target":"ALL"}}
        if share_ip:
            payload["ShareParameters"]["IPAddress"] = share_ip
        if share_type:
            payload["ShareParameters"]["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareParameters"]["ShareName"] = share_name
        if profile_name:
            payload["ShareParameters"]["FileName"] = profile_name
        if share_username:
            payload["ShareParameters"]["Username"] = share_username
        if share_password:
            payload["ShareParameters"]["Password"] = share_password
        if ignore_certwarning:
            payload["ShareParameters"]["IgnoreCertificateWarning"] = ignore_certwarning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 401:
            logging.info("- INFO, status code 401 detected, iDRAC username password changed while applying configuration changes. Access the iDRAC using new password to check job status")
            return
        elif response.status_code != 202:
            logging.error("\n- FAIL, status code %s returned" % response.status_code )  
            return
        try:
            job_id = response.__dict__["headers"]["Location"].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in headers output. Check iDRAC job queue for job ID")
            return
        logging.info("\n- %s successfully created for ImportSystemConfigurationPreview method\n" % (job_id) )
        start_time = datetime.now()
        while True:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (creds["idrac_ip"], job_id), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            data = response.json()
            message_string = data["Messages"]
            final_message_string = str(message_string)
            current_time = (datetime.now()-start_time)
            if response.status_code == 200:
                logging.info("- PASS, job ID %s state marked completed\n" % job_id)
                logging.info("\n- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                logging.info("\n- Config results for job ID %s\n" % job_id)
                for i in data['Messages']:
                    for ii in i.items():
                        print("%s: %s" % (ii[0], ii[1]))
                return
            elif response.status_code != 202:
                logging.error("- ERROR, query job ID command failed, error code: %s, error results: \n%s" % (response.status_code, data))
                return
            elif "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string or "not compliant" in final_message_string or "Unable to complete" in final_message_string or "The system could not be shut down" in final_message_string or "timed out" in final_message_string:
                logging.error("\n- FAIL, detailed job message: %s" % data["Messages"])
                return
            elif "No reboot Server" in final_message_string:
                try:
                    logging.info("- Message = "+message_string[0]["Message"])
                except:
                    logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
                return
            elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully previewed" in final_message_string or data["TaskState"] == "Completed":
                logging.info("- PASS, job ID %s state marked completed\n" % job_id)
                logging.info("\n- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                logging.info("\n- Config results for job ID %s\n" % job_id)
                for i in data['Messages']:
                    for ii in i.items():
                        print("%s: %s" % (ii[0], ii[1]))
                return
            elif "No changes" in final_message_string or "No configuration changes" in final_message_string:
                logging.info("- Job ID = "+data["Id"])
                logging.info("- Name = "+data["Name"])
                try:
                    logging.info("- Message = "+message_string[0]["Message"])
                except:
                    logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
                logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
                return
            else:
                logging.info("- INFO, job not marked completed, current status: %s" % data["TaskState"])
                time.sleep(3)
                continue
    else:
        logging.error("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return


def get_set_chassis_indicator_LED(script_examples="", get_LED_status="", set_LED=""):
    """Function to either get current chassis LED status or blink chassis LED. Supported function arguments: script_examples (supported value: True), get_LED_status (supported value: True) and set_LED (supported values: Blinking and Lit)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.get_set_chassis_indicator_LED(get_LED_status=True), this example will get current chassis LED status.
        \n- IdracRedfishSupport.get_set_chassis_indicator_LED(set_LED="Blinking"), this example will blink chassis LED.""")    
    elif get_LED_status:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.warning("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
            return
        elif response.status_code != 200:
            logging.error("- ERROR, status code %s returned, error results: %s" % (response.status_code, data))
            return
        logging.info("\n- INFO, current chassis indicator LED state: %s" % data['IndicatorLED'])
    elif set_LED:
        url = 'https://%s/redfish/v1/Chassis/System.Embedded.1' % creds["idrac_ip"]
        payload = {'IndicatorLED': set_LED}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command successfully completed \"%s\" request for chassis indicator LED" % set_LED)
        else:
            logging.error("\n- ERROR, status code %s returned, detailed failure results:\n%s" % (response.status_code, response.__dict__))
            return
    else:
        logging.error("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return

def supportassist_schedule_auto_collection(script_examples="", get_supportassist_auto_collection_details="", clear_supportassist_auto_collection="", set_supportassist_auto_collection="", recurrence="", time="", dayofweek="", dayofmonth=""):
    """Function to either get, clear or set SupportAssist scheduled collection. Supported function arguments: script_examples (supported value: True), get_supportassist_auto_collection_details (supported value: True), clear_supportassist_auto_collection (supported value: True), set_supportassist_auto_collection_details (supported value: True), recurrence (supported values: Weekly, Monthly and Quarterly), time (supported time format: HH:MMAM/PM, example: \"06:00PM\"), dayofweek (supported values: Mon, Tue, Wed, Thu, Fri, Sat, Sun or * for all days of the week) and dayofmonth (supported values: 1 through 32 or L for last day or * for all days of the month)."""
    if script_examples:
        print("""\n- IdracRedfishSupport.supportassist_schedule_auto_collection(get_supportassist_auto_collection_details=True), this example will get current SupportAssist scheduled collection details.
        \n- IdracRedfishSupport.supportassist_schedule_auto_collection(clear_supportassist_auto_collection=True), this example will clear current SupportAssist scheduled collection.
        \n- IdracRedfishSupport.supportassist_schedule_auto_collection(set_supportassist_auto_collection=True, recurrence="Monthly", time="06:00PM", dayofweek="Sat", dayofmonth="L"), this example shows setting SupportAssist auto collection schedule which will run monthly at 6PM on the last Saturday of the month. NOTE: Once you create scheduled SA collection, you can also check the job queue to see this scheduled task.""")
    
    elif get_supportassist_auto_collection_details:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetAutoCollectSchedule' % creds["idrac_ip"]
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, POST command passed to get SupportAssist auto collection details\n")
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
        for i in data.items():
            if "ExtendedInfo" not in i[0]:
                print("%s: %s" % (i[0], i[1]))

    elif clear_supportassist_auto_collection:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistClearAutoCollectSchedule' % creds["idrac_ip"]
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, POST command passed to clear SupportAssist auto collection details\n")
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return

    elif set_supportassist_auto_collection:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistSetAutoCollectSchedule' % creds["idrac_ip"]
        payload = {}
        if recurrence:
            payload["Recurrence"] = recurrence
        if time:
            payload["Time"] = time
        if dayofweek:
            payload["DayOfWeek"] = dayofweek
        if dayofmonth:
            payload["DayOfMonth"] = dayofmonth       
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, POST command passed to set SupportAssist auto collection details\n")
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
    else:
        print("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return


def create_modify_delete_iDRAC_users(script_examples="", get_current_users="", create_user="", new_username="", user_id="", role_id="", enable_user="", disable_user="", modify_user="", delete_user="", change_password=""):
    """Function to create, modify or delete iDRAC user accounts. Supported function arguments: script_examples (supported value: True), get_current_users (supported value: True), create_user (supported value: True), new_username, user_id (possible values: 2 thru 16), role_id (supported values: Administrator, Operator, ReadOnly and None), enable_user (supported value: True), disable_user (supported_value: True), modify_user (supported value: pass in user ID you want to modify, 2 thru 16), delete_user (supported value: pass in the user ID you want to delete, 2 thru 16) and change_password."""
    if script_examples:
        print("""\n-IdracRedfishSupport.create_modify_delete_iDRAC_users(get_current_users=True), this example will get current iDRAC user account details.
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(create_user=True, new_username=\"tester\", user_id=\"16\", role_id=\"Administrator\", enable_user=True), this example will create new user for ID 16 with administrator privileges and enabled. You will be prompted to enter password which will not be echoed to the screen.
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(modify_user=\"16\", change_password=True), this example will change user ID 16 password. You will be prompted to enter password which will not be echoed to the screen.
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(modify_user=\"16\", role_id=\"Operator\"), this example will change user ID 16 privilege to Operator. 
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(modify_user=\"16\", new_username=\"user_16\"), this example shows changing user ID 16 username.
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(modify_user=\"16\", disable_user=True), this example shows disabling user ID 16. Note, user account still exists but unable to use.
        \n- IdracRedfishSupport.create_modify_delete_iDRAC_users(delete_user=\"16\"), this example shows deleting user ID 16""")
    
    elif get_current_users:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code != 200:
            logging.error("- ERROR, GET command failed, status code %s returned, error results: %s" % (response.status_code, data))
            return
        for i in data["Members"]:
            for ii in i.items():
                if ii[0] != "@odata.type" or ii[0] != "Links" or ii[0] != "@odata.context":
                    print("%s: %s" % (ii[0], ii[1]))
            print("\n")
        
    elif create_user:
        new_iDRAC_username_password = getpass.getpass("\n- Pass in new password to create new iDRAC user %s: " % new_username)
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (creds["idrac_ip"], user_id)
        payload = {"UserName":new_username, "Password":new_iDRAC_username_password, "RoleId":str(role_id), "Enabled":enable_user}        
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to create new iDRAC user %s\n" % new_username)
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
       
    elif modify_user:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (creds["idrac_ip"], str(modify_user))
        payload = {}
        if disable_user:
            payload["Enabled"] = False
        if enable_user:
            payload["Enabled"] = True
        if change_password:
            new_iDRAC_username_password = getpass.getpass("\n- Pass in new password: ")
            payload["Password"] = new_iDRAC_username_password
            logging.info("\n- INFO, if you changed iDRAC user password used to execute this Redfish command, rerun \"IdracRedfishSupport.get_iDRAC_creds()\" to set the new password")
        if new_username:
            payload["UserName"] = new_username
        if role_id:
            payload["RoleId"] = role_id
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to modify iDRAC user ID %s" % str(modify_user))
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
    
    elif delete_user:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (creds["idrac_ip"], str(delete_user))
        payload = {"Enabled":False,"RoleId":"None"}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data=response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, PATCH command passed to delete iDRAC user ID %s\n" % str(delete_user))
        else:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
        payload = {"UserName":""}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data=response.json()
        if response.status_code != 200:
            logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
    else:
        print("- ERROR, either incorrect or missing function arguments detected. Check doc help for more details or execute examples")
        return


def install_from_repository(script_examples="", get_fw_inventory="", get_repo_update_list="", get_device_name_criticality_info= "", repository_update="", share_ip="", share_type="", share_name="", share_username="", share_password="", apply_update="", reboot_needed="", catalog_file="", ignore_certwarning=""):
    """Function to either get current firmware inventory, get repository update list details, criticality repository details or perform install from repository. Supported arguments and possible values: get_fw_inventory (supported value: True), get_repo_update_list (supported value: True), get_device_name_criticality_info (supported_value: True), repository_update (supported value: True), share_ip, share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_name, share_username (only required if using CIFS or secure HTTP/HTTPS), share_password (only required if using CIFS or secured HTTP/HTTPS), apply_update (supported values: yes and no), reboot_needed (supported values: yes and no), catalog_file (only required if default catalog name is not used (Catalog.xml)), ignore_certwarning (supported values: On and Off, only valid to use with HTTPS. If not passed in, default value is On)""" 
    if script_examples:
        print("""\n- IdracRedfishSupport.install_from_repository(get_fw_inventory=True), this example will get current firmware inventory for all supported devices
        \n- IdracRedfishSupport.install_from_repository(get_repo_update_list=True), this example will get current repository list details, versions that are listed on the repository that can be updated. Before running this command, you need to perform install from repository first with reboot_needed = no and apply_update = no.
        \n- IdracRedfishSupport.install_from_repository(get_device_name_criticality_info=True), this example will get criticality details for updatable devices. Before running this command, you need to perform install from repository first with reboot_needed = no and apply_update = no.
        \n- IdracRedfishSupport.install_from_repository(repository_update=True, share_ip="downloads.dell.com", share_type="HTTPS", apply_update="no", reboot_needed="no"), this example shows using HTTPS share "downloads.dell.com" to perform repository update. No updates will get applied and no auto reboot will occur.
        \n- IdracRedfishSupport.install_from_repository(repository_update=True, share_ip="downloads.dell.com", share_type="HTTPS", apply_update="yes", reboot_needed="yes"). this example shows using HTTPS share "downloads.dell.com" to perform repository update. Any updates which do not require a server reboot will get installed first, then reboot the server to apply any updates which require a server reboot. Note: If iDRAC update is detected, this will always get updated last due to iDRAC reboots after the update is complete.""")   
    
    elif get_fw_inventory:
        logging.info("\n- INFO, getting current firmware inventory for iDRAC %s -\n" % creds["idrac_ip"])
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % creds["idrac_ip"],verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if response.status_code == 200:
            logging.info("- INFO, GET command passed to get firmware inventory")
        else:
            logging.error("\n- ERROR, command failed to check job status, return code %s" % response.status_code)
            logging.info("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        for i in data['Members']:
            for ii in i.items():
                if ii[0] == "Oem":
                    for iii in ii[1]["Dell"]["DellSoftwareInventory"].items():
                        if "odata" not in iii[0]:
                            print("%s: %s" % (iii[0],iii[1]))   
                elif "odata" not in ii[0] or "Description" not in ii[0]:
                    print("%s: %s" % (ii[0],ii[1]))
            print("\n")

    elif get_repo_update_list:
        try:
            os.remove("repo_update_list.xml")
        except:
            pass
        open_file = open("repo_based_update_list.xml","a")
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (creds["idrac_ip"])
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS: POST command passed to get repo update list, status code 200 returned")
        else:
            logging.error("\n- ERROR, POST command failed to get repo update list, status code %s returned" % (response.status_code))
            data = response.json()
            logging.info("\n-POST command failure results:\n %s" % data)
            return
        logging.info("\n- Repo Based Update List in XML format\n")
        print(data['PackageList'])
        open_file.writelines(data['PackageList'])
        open_file.close()
        logging.info("\n- INFO, get repo based update list data is also copied to file \"repo_based_update_list.xml\"")

    elif get_device_name_criticality_info:
        logging.info("\n- Device Name and Criticality Details for Updatable Devices -\n")
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (creds["idrac_ip"])
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        try:
            get_all_devices = re.findall("Criticality.+BaseLocation",data["PackageList"])
        except:
            logging.error("- ERROR, regex was unable to parse the XML to get criticality data")
            return
        for i in get_all_devices:
            get_critical_value = re.search("Criticality.+?/",i).group()
            if "1" in get_critical_value:
                critical_string_value = "Criticality = (1)Recommended"
            elif "2" in get_critical_value:
                critical_string_value = "Criticality = (2)Urgent"
            elif "3" in get_critical_value:
                critical_string_value = "Criticality = (3)Optional"
            else:
                critical_string_value = "Criticality = NA"
            try:
                get_display_name = re.search("DisplayName.+?/VALUE",i).group()
                get_display_name = re.sub("DisplayName\" TYPE=\"string\"><VALUE>","",get_display_name)
                get_display_name = re.sub("</VALUE","",get_display_name)
            except:
                logging.error("- ERROR, regex was unable to parse the XML to get device name")
                return
            get_display_name = "DeviceName = " + get_display_name
            print(get_display_name)
            print(critical_string_value)
            print("\n")
      
    elif repository_update and reboot_needed == "yes" or reboot_needed == "no" and apply_update == "yes" or apply_update == "no":
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = str(response.json())
        if response.status_code != 200:
            logging.error("\n- ERROR, GET command failed to get job queue details, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
            return
        jobid_search = re.findall("JID_.+?'",data)
        current_jobstore_job_ids = []
        for i in jobid_search:
            i = i.strip("'")
            current_jobstore_job_ids.append(i)
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.InstallFromRepository' % (creds["idrac_ip"])
        method = "InstallFromRepository"
        payload={}
        if apply_update.lower() == "yes":
            payload["ApplyUpdate"] = "True"
        if apply_update.lower() == "no":
            payload["ApplyUpdate"] = "False"
        if reboot_needed.lower() == "yes":
            payload["RebootNeeded"] = True
        if reboot_needed.lower() == "no":
            payload["RebootNeeded"] = False   
        if catalog_file:
            payload["CatalogFile"] = catalog_file  
        if share_ip:
            payload["IPAddress"] = share_ip
        if share_type:
            payload["ShareType"] = share_type.upper()
        if share_name:
            payload["ShareName"] = share_name
        if share_username:
            payload["UserName"] = share_username
        if share_password:
            payload["Password"] = share_password
        if ignore_certwarning:
            payload["IgnoreCertWarning"] = ignore_certwarning
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 202:
            logging.info("\n- PASS: POST command passed for method \"%s\", status code %s returned" % (method, response.status_code))
        else:
            logging.error("\n- ERROR, POST command failed for method %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.info("\n- Failure results:\n %s" % data)
            return
        try:
            repo_job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- ERROR, unable to locate job ID in headers output")
            return
        logging.info("- PASS, repository job ID %s successfully created" % repo_job_id)
        # Function to loop job ID
        def loop_job_status(job_id_to_query):
            print_message_count = 1
            start_time = datetime.now()
            time.sleep(1)
            while True:
                count = 0
                while count != 5:
                    try:
                        if x_auth_token == "yes":
                            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id_to_query), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
                        else:
                            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], job_id_to_query), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
                        break
                    except requests.ConnectionError as error_message:
                        logging.error("- ERROR, requests command failed to GET job status, detailed error information: \n%s" % error_message)
                        count += 1
                        logging.info("- INFO, Script will wait 10 seconds and try to check job status again")
                        time.sleep(10)
                        continue
                if count == 5:
                    logging.error("- ERROR, unable to get job status after 5 attempts, script will exit")
                    return
                current_time = str((datetime.now()-start_time))[0:7]
                if response.status_code != 200:
                    logging.error("\n- ERROR, GET command failed to check job status, status code %s returned" % response.status_code)
                    logging.info("Extended Info Message: {0}".format(response.json()))
                    return
                data = response.json()
                if str(current_time)[0:7] >= "2:00:00":
                    logging.error("\n- ERROR: Timeout of 2 hours has been reached, script stopped\n")
                    return
                elif "Fail" in data['Message'] or "fail" in data['Message'] or "invalid" in data['Message'] or "unable" in data['Message'] or "Unable" in data['Message'] or "not" in data['Message'] or "cancel" in data['Message'] or "Cancel" in data['Message']:
                    logging.error("- ERROR: Job ID %s failed, detailed error message: %s" % (job_id_to_query, data['Message']))
                    break
                elif data['Message'] == "Job for this device is already present.":
                    break
                elif "Package successfully downloaded" in data['Message'] and reboot_needed.lower() == "no" and apply_update.lower() == "yes":
                    logging.info("\n- INFO, repository package successfully downloaded, \"RebootNeeded = no\" detected. Manually check the overall Job Queue for update jobs. For devices that do not require a reboot to get applied, these updates will execute. For devices that need a server reboot to apply, these jobs will execute on next server manual reboot.\n")
                    return
                elif "Package successfully downloaded" in data['Message'] and reboot_needed.lower() == "no" or not reboot_needed:
                    logging.info("\n- INFO, repository package successfully downloaded, \"RebootNeeded = no\" detected. Manually check the overall Job Queue for Update Jobs. Next server manual reboot, any scheduled update job(s) will execute.\n")
                    return
                elif "Package successfully downloaded" in data['Message'] and print_message_count == 1:
                    logging.info("\n- INFO, repository package successfully downloaded. If version changed detected for any device, update job ID(s) will get created\n")
                    time.sleep(5)
                    print_message_count = 2
                    
                elif "completed successfully" in data['Message']:
                    logging.info("\n- PASS, job ID %s successfully marked completed" % job_id_to_query)
                    logging.info("\n- Final detailed job results -\n")
                    for i in data.items():
                        print("%s: %s" % (i[0], i[1]))
                    print("\n")
                    if data['JobType'] == "RepositoryUpdate":
                        if apply_update == "no":
                            logging.info("\n- INFO, \"ApplyUpdate = no\" selected, execute script again to view the repo update list which will report devices detected for firmware updates")
                            return
                        else:
                            print("\n- INFO, repository update job marked completed. Script will now check to see if any update job(s) were created due to different firmware version change detected")
                            break
                    else:
                        break
                elif data['JobState'] == "Failed":
                    logging.WARNING("- WARNING, failed job state detected. Detailed results: %s" % data)
                    return
                else:
                    print("- INFO, job ID %s not marked completed, current job information:\n" % (job_id_to_query))
                    print("* Name: %s" % data['Name'])
                    print("* Job Status: %s" % data['Message'])
                    print("* Current job execution time: %s\n" % str(current_time)[0:7])
                    time.sleep(15)
                    continue
        # Call function to check repo update job ID status
        loop_job_status(repo_job_id)
        if apply_update == "no":
            return
        # Code to get newly created update job ids
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (creds["idrac_ip"])
        payload={}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 200:
            logging.info("- PASS, GET command passed to get repo update list details")
        else:
            if data['error']['@Message.ExtendedInfo'][0]['Message'] == 'Firmware versions on server match catalog, applicable updates are not present in the repository.' or "not found" in data['error']['@Message.ExtendedInfo'][0]['Message']:
                logging.info("\n- INFO, %s" % data['error']['@Message.ExtendedInfo'][0]['Message'])
                return
            else:
                logging.error("\n- ERROR, POST command failed to get repo update list, status code %s returned" % (response.status_code))
                data = response.json()
                logging.info("\n- Failure results:\n %s" % data)
                return
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = str(response.json())
        jobid_search = re.findall("JID_.+?'",data)
        if jobid_search == []:
            logging.info("\n- INFO, job queue empty, no current job IDs detected")
            return
        jobstore = []
        for i in jobid_search:
            i = i.strip("'")
            jobstore.append(i)
        new_job_ids = []
        for i in jobstore:
            for ii in current_jobstore_job_ids:
                 if i == ii:
                         break
            else:
                new_job_ids.append(i)
        new_job_ids.remove(repo_job_id)
        time.sleep(30)
        # Code to check for scheduled update jobs
        for i in new_job_ids:
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], i), verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (creds["idrac_ip"], i), verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
            if response.status_code != 200:
                logging.error("\n- ERROR, GET command failed to check job status, status code %s returned" % response.status_code)
                logging.error("Extended Info Message: {0}".format(req.json()))
                return
            data = response.json()
            if data['JobState'] == "Failed":
                    logging.warning("- WARNING, failed job state detected. Detailed results: %s" % data)
                    logging.info("\n- INFO, check overall Job Queue and Lifecycle Logs for more details")
                    return
            elif data['Message'] == "Task successfully scheduled." and reboot_needed.lower() == "yes":
                logging.info("\n- INFO, scheduled update job ID detected, server rebooting to apply the update(s)\n")
                time.sleep(5)
                break
            elif data['Message'] == "Task successfully scheduled." and reboot_needed.lower() == "no" or not reboot_needed:
                logging.info("\n- INFO, scheduled update job ID detected but \"RebootNeeded\" = no or RebootNeeded argument not passed in. Manually check the overall Job Queue for update jobs. Next server manual reboot, any scheduled update job(s) will execute.")
                return
                if new_job_ids == []:
                    logging.info("- INFO, no update job IDs detected, check iDRAC Lifecycle Logs for more details")
                    return
                logging.info("\n- Current update jobs created for repo update -\n")
        # Code to loop all update jobs until marked completed or failed
        logging.info("\n- INFO, script will now loop polling all new update jobs created until marked completed") 
        for i in new_job_ids:
            loop_job_status(i)        
    else:
        logging.error("\n- ERROR, either incorrect argument values or missing arguments detected. Check doc help for more details or script examples")
        return

def insert_eject_virtual_media(script_examples="", get_attach_status="", insert_virtual_media="", eject_virtual_media="", image_path=""):
    """Function to either get current virtual media attach status or insert/eject virtual media. With iDRAC 6.00.00 or newer you can now attach multiple virtual media devices at the same time based off index ID (see script examples for more help). Supported arguments and possible values: get_attach_status (supported value: True), insert_virtual_media (supported values: cd and removeabledisk (iDRAC 5.10.10 or older), 1 and 2 (iDRAC 6.00.00 or newer)), eject_virtual_media (supported values: cd and removeabledisk (iDRAC 5.10.10 or older), 1 and 2 (iDRAC 6.00.00 or newer)) and image_path (pass in image path location of the virtual device to insert. Supported network share types: HTTP, HTTPS, NFS and CIFS.""" 
    if script_examples:
        print("""\n- IdracRedfishSupport.insert_eject_virtual_media(get_attach_status=True), this example will return current attach status details all virtual media devices.)
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="cd", image_path="192.168.0.120:/nfs/ESXi7.iso"), this example using iDRAC 5.10.10 will insert(attach) virtual media ISO image using NFS share.
        \n- IdracRedfishSupport.insert_eject_virtual_media(eject_virtual_media="cd"), this example using iDRAC 5.10.10 will eject(detach) virtual media CD device attached.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="cd", image_path="//administrator:Passw0rd123@192.168.0.130/cifs_share_vm/ESXi7.iso"), this example using iDRAC 5.10.10 will insert(attach) virtual media ISO image using CIFS share.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="cd", image_path="https://https_user:Password123@192.168.0.130/https_share/VMware-ESXi-7.iso", this example using iDRAC 5.10.10 will insert(attach) virtual media ISO image using HTTPS share with auth.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="cd", image_path="https://3.137.219.52/centos/7/isos/x86_64/CentOS-7-live-GNOME-x86_64.iso"), this example using iDRAC 5.10.10 will insert(attach) virutl media ISO image using HTTPS share with no auth.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="removeabledisk", image_path="192.168.0.140:/nfs/idsdm.img"), this example using iDRAC 5.10.10 will insert(attach) virtual media IMG image using NFS share.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media=1, image_path="192.168.0.130:/nfs/boot.iso"), this example using iDRAC 6.00.00 shows attaching virtual media ISO for index 1 device.
        \n- IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media=2, image_path="192.168.0.130:/nfs/RHEL8.4.iso"), this example using iDRAC 6.00.00 shows attaching virtual media ISO for index 2 device.
        \n- IdracRedfishSupport.insert_eject_virtual_media(eject_virtual_media=1), this example using iDRAC 6.00.00 shows ejecting virtual media index 1 device.
        \n- IdracRedfishSupport.insert_eject_virtual_media(eject_virtual_media=2), this example using iDRAC 6.00.00 shows ejecting virtual media index 2 device.""")
    else:
        if x_auth_token == "yes":
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code != 200:
            logging.warning("\n- WARNING, unable to get current iDRAC version installed")
            return
        if int(data["FirmwareVersion"].replace(".","")) >= 6000000:
            iDRAC_version = "new"
        else:
            iDRAC_version = "old"

    if get_attach_status:
        virtual_media_uris = []
        if iDRAC_version == "old":
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))
        if iDRAC_version == "new":
            if x_auth_token == "yes":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/VirtualMedia?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],headers={'X-Auth-Token': creds["idrac_x_auth_token"]})    
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/VirtualMedia?$expand=*($levels=1)' % creds["idrac_ip"], verify=creds["verify_cert"],auth=(creds["idrac_username"], creds["idrac_password"]))   
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- ERROR, GET command failed to get virtual media attach status details, status code %s returned" % response.status_code)
            logging.error(data)
            return
        print("\n")
        for i in data["Members"]:
            pprint(i)
            print("\n")

    elif insert_virtual_media:
        if iDRAC_version == "old":
            if insert_virtual_media.lower() == "cd":
                url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia" % creds["idrac_ip"]
            elif insert_virtual_media.lower() == "removeabledisk":
                url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.InsertMedia" % creds["idrac_ip"]
            else:
                logging.error("- FAIL, invalid value passed in for argument insert_virtual_media.")
                return
        if iDRAC_version == "new":
            url = "https://%s/redfish/v1/Systems/System.Embedded.1/VirtualMedia/%s/Actions/VirtualMedia.InsertMedia" % (creds["idrac_ip"], insert_virtual_media)
        payload = {'Image': image_path, 'Inserted':True,'WriteProtected':True}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.__dict__
        if response.status_code != 204:
            logging.error("\n- FAIL, POST command failed to insert virtual media, detailed error message: %s" % response._content)
            return
        else:
            logging.info("\n- PASS, POST command passed to successfully insert(attached) virtual media, status code %s returned" % response.status_code)

    elif eject_virtual_media:
        if iDRAC_version == "old":
            if insert_virtual_media.lower() == "cd":
                url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia" % creds["idrac_ip"]
            elif insert_virtual_media.lower() == "removeabledisk":
                url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.EjectMedia" % creds["idrac_ip"]
            else:
                logging.error("- FAIL, invalid value passed in for argument insert_virtual_media.")
                return
        if iDRAC_version == "new":
            url = "https://%s/redfish/v1/Systems/System.Embedded.1/VirtualMedia/%s/Actions/VirtualMedia.EjectMedia" % (creds["idrac_ip"], eject_virtual_media)
        payload = {}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.__dict__
        if response.status_code != 204:
            logging.error("\n- FAIL, POST command failed to eject virtual media, detailed error message: %s" % response._content)
            return
        else:
            logging.info("\n- PASS, POST command passed to successfully eject(detach) virtual media, status code %s returned" % response.status_code)

def change_disk_state_virtualdisk(script_examples="", disk="", state=""):
    """Function to change the PD state of a disk part of a virtual disk, either set the disk to offline or bring back online. NOTE: Only RAID volumes which support parity are supported for this feature. Supported function arguments: disk (possible value: pass in disk FQDD) and state (possible values: offline and online)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.change_disk_state_virtualdisk(disk="Disk.Bay.0:Enclosure.Internal.0-1:RAID.SL.3-1",state="offline"), this example shows converting disk 0 to offline which is part of a RAID 5 volume.
        \n- IdracRedfishSupport.change_disk_state_virtualdisk(disk="Disk.Bay.1:Enclosure.Internal.0-1:RAID.SL.3-1",state="online"), this example shows converting disk 1 to online which is part of a RAID 5 volume.""")
        return
    elif disk and state:
        method = "ChangePDState"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ChangePDState' % (creds["idrac_ip"])
        payload = {"State":state.title(),"TargetFQDD":disk}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created" % job_id)
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def blink_unblink_storage_device(script_examples="", blink="", unblink=""):
    """Function to blink or unblink either hard drive or virtual disk. Possible function arguments: blink (pass in drive or virtual disk FQDD string) and unblink (pass in drive or virtual disk FQDD string)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.blink_unblink_storage_device(blink="Disk.Bay.3:Enclosure.Internal.0-1:RAID.SL.3-1"), this example shows blinking disk 3.
        \n- IdracRedfishSupport.blink_unblink_storage_device(unblink="Disk.Virtual.0:RAID.SL.3-1"), this example shows unblink virtual disk 0.""")
        return
    elif blink:
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.BlinkTarget' % (creds["idrac_ip"])
        method = "BlinkTarget"
        payload = {"TargetFQDD":blink}
    elif unblink:
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.UnBlinkTarget' % (creds["idrac_ip"])
        method = "UnBlinkTarget"
        payload = {"TargetFQDD":unblink}
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return
    if x_auth_token == "yes":
        headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        return

def cancel_check_consistency_virtual_disk(script_examples="", virtual_disk_fqdd=""):
    """Function to cancel check consistency operation running on a virtual disk. Supported function argument: virtual_disk_fqdd (pass in virtual disk FQDD)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.cancel_check_consistency_virtual_disk(virtual_disk_fqdd="Disk.Virtual.0:RAID.SL.3-1"), this example will cancel check consistency operation running on VD 0.""")
        return
    elif virtual_disk_fqdd:
        method = "CancelCheckConsistency"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.CancelCheckConsistency' % (creds["idrac_ip"])
        payload = {"TargetFQDD":virtual_disk_fqdd}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created" % job_id)
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def expand_virtualdisk(script_examples="", pdisks="", expand="", size=""):
    """Function to expand storage virtual disk, either add a disk or expand current size. Supported function arguments: expand (pass in virtual disk FQDD), pdisks (possible value: Pass in disk(s) you want to add to the virtual disk. If you pass in multiple disk FQDDs use a comma separator between FQDDs.) and size (possible value: Pass in new VD size you want to expand to in MB)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.expand_virtualdisk(expand="Disk.Virtual.0:RAID.SL.3-1", size="400000"), this example shows expanding VD 0 to 400GB in size. 
        \n- IdracRedfishSupport.expand_virtualdisk(expand="Disk.Virtual.2:RAID.SL.3-1", pdisks="Disk.Bay.3:Enclosure.Internal.0-1:RAID.SL.3-1"), this example shows expanding VD 2 by adding disk 3 to the VD.""")
        return
    elif expand:
        method = "OnlineCapacityExpansion"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.OnlineCapacityExpansion' % (creds["idrac_ip"])
        if pdisks:
            if "," in pdisks:
                disk_list = pdisks.split(",")
                payload = {"TargetFQDD": expand,  "PDArray": disk_list}
            else:
                payload = {"TargetFQDD": expand,  "PDArray": [pdisks]}   
        elif size:
            payload = {"TargetFQDD": expand,  "Size": int(size)}
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created" % job_id)
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return

def raidlevel_migration(script_examples="", pdisks="", migrate="", new_raid_level=""):
    """Function to add additional hard drive(s) to the existing RAID Level to migrate to a new RAID level. Supported function arguments: migrate (pass in virtual disk FQDD), pdisks (possible value: Pass in disk(s) you want to add to the virtual disk. If you pass in multiple disk FQDDs use a comma separator between FQDDs.) and new_raid_level (possible values: RAID0, RAID1, RAID5, RAID6, RAID10, RAID50 and RAID60)."""
    global job_id
    if script_examples:
        print("""\n- IdracRedfishSupport.raidlevel_migration(migrate="Disk.Virtual.0:RAID.SL.3-1", pdisks="Disk.Bay.3:Enclosure.Internal.0-1:RAID.SL.3-1", new_raid_level="RAID1"), this example shows adding disk 3 to VD 0 (RAID 0), migrate to create RAID 1 volume.""")
        return
    elif migrate:
        method = "RAIDLevelMigration"
        url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.RAIDLevelMigration' % (creds["idrac_ip"])
        if pdisks:
            if "," in pdisks:
                disk_list = pdisks.split(",")
                payload = {"TargetFQDD": migrate, "PDArray": disk_list, "NewRaidLevel":new_raid_level.upper()}
            else:
                payload = {"TargetFQDD": migrate, "PDArray": [pdisks], "NewRaidLevel":new_raid_level.upper()}   
        if x_auth_token == "yes":
            headers = {'content-type': 'application/json', 'X-Auth-Token': creds["idrac_x_auth_token"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"])
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=creds["verify_cert"],auth=(creds["idrac_username"],creds["idrac_password"]))
        data = response.json()
        if response.status_code == 401:
            logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
            return
        elif response.status_code == 200 or response.status_code == 202:
            logging.info("\n- PASS: POST command passed for %s, status code %s returned" % (method, response.status_code))
            try:
                job_id = response.headers['Location'].split("/")[-1]
            except:
                logging.error("- FAIL, unable to locate job ID in JSON headers output")
                return
            logging.info("- Job ID %s successfully created" % job_id)
            loop_job_status_final()
        else:
            logging.error("\n- FAIL, POST command failed for %s, status code %s returned" % (method, response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            return
    else:
        logging.warning("- WARNING, missing arguments or incorrect argument values passed in. Check help text and script examples for more details")
        return



        
    




    








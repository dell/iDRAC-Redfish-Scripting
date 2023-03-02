#!/usr/bin/python3
#
# GetSetOemNetworkPropertiesREDFISH. Python script using Redfish API DMTF to either get or set OEM network device properties. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
#
# Copyright (c) 2021, Dell, Inc.
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
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get or set OEM network device properties. This will configure properties which are not exposed as being supported from DMTF. Examples: virtual MAC address or virtualization mode.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-ids', help='Get network device IDs', action="store_true", dest="get_ids", required=False)
parser.add_argument('--get-all-attributes', help='Get attributes for network device, pass in network device ID. Example: NIC.Integrated.1-1-1.', dest="get_all_attributes", required=False)
parser.add_argument('--get-attribute', help='Get specific attribute, pass in the attribute name. You must also argument --get-all-attributes passing in the network device ID. NOTE: For the attribute name, make sure you pass in the exact case.', dest="get_attribute", required=False)
parser.add_argument('--get-all-registry', help='Get network attribute registry details. Attribute registry will return attribute information for possible values, if read only, if read write, regex.', action="store_true", dest="get_all_registry", required=False)
parser.add_argument('--set', help='Set attributes, pass in the network device ID (Example: NIC.Integrated.1-1-1). You must also use arguments --attribute-names, --attribute-values and --reboot-type for setting attributes.', required=False)
parser.add_argument('--attribute-names', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: VLanMode will work but vlanmode will fail. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: --reboot-type (reboot type) is required when setting attributes', dest="attribute_names", required=False)
parser.add_argument('--attribute-values', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value.', dest="attribute_values", required=False)
parser.add_argument('--reboot', help='Pass in this argument if you want to reboot the server immediately to execute the config job.', action="store_true", required=False)
parser.add_argument('--maintenance-reboot', help='Pass in the type of maintenance window job type you want to create. Supported values: autoreboot (server to automatically reboot and apply the changes once the maintenance windows has been hit) and noreboot (server will not automatically reboot once the maintenance window time has hit. If you select this option, user will have to manually reboot the server during the maintenance window timeframe to apply the configuration job.)', dest="maintenance_reboot", required=False)
parser.add_argument('--start-time', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', dest="start_time", required=False)
parser.add_argument('--duration-time', help='Maintenance window duration time, pass in a value in seconds', dest="duration_time", required=False)
parser.add_argument('--get-idrac-time', help='Get current iDRAC time. Excute this argument to get iDRAC current time which will help with setting maintenance window configuration job.', action="store_true", dest="get_idrac_time", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-ids, this example will return NIC device IDs.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all-attributes NIC.Embedded.1-1-1, this example will return all attributes for only NIC.Embedded.1-1-1.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all-attributes NIC.Embedded.1-1-1 --get-attribute IscsiInitiatorIpAddr, this example will only return attribute IscsiInitiatorIpAddr details for NIC.Embedded.1-1-1.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all-registry, this example will return network attribute registry details.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-idrac-time, this example will return current iDRAC time.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set NIC.Embedded.1-1-1 --attribute-names WakeOnLan --attribute-values Enabled --reboot, this example will reboot the server now to execute config job to set attribute WakeOnLan to Enabled.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set NIC.Embedded.1-1-1 --attribute-names WakeOnLan,LegacyBootProto --attribute-values Disabled,NONE, this example shows creating a config job to set multiple attributes but will not reboot the server now. Config job is still scheduled and will run on next manual reboot.
    \n- GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set NIC.Embedded.1-1-1 --attribute-names WakeOnLan,LegacyBootProto --attribute-values Enabled,PXE --maintenance-reboot autoreboot --start-time 2022-05-03T07:27:00-05:00 --duration-time 600, this example shows creating a maintenance window config job. Once start time has elapsed, server will auto reboot and execute the job.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Registries' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Registries' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_idrac_version():
    global idrac_fw_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET request failed to get iDRAC firmware version, error: \n%s" % data)
        sys.exit(0)
    idrac_fw_version = data["FirmwareVersion"].replace(".","")

def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    payload={"GetRequest":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- Current iDRAC time -\n")
    else:
        logging.error("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- Failure results:\n %s" % data)
        sys.exit(0)
    for i in data.items():
        if i[0] !="@Message.ExtendedInfo":
            print("%s: %s" % (i[0], i[1]))

def get_network_device_fqdds():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    network_device_list = []
    for i in data['Members']:
        for ii in i.items():
            network_device = ii[1].split("/")[-1]
            network_device_list.append(network_device)
    for i in network_device_list:
        port_list = []
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        logging.info("\n- Network device ID(s) detected for %s -\n" % i)
        for i in data['Members']:
            for ii in i.items():
                print(ii[1].split("/")[-1])

def get_network_device_attributes():
    network_id = args["get_all_attributes"].split("-")[0]
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["get_all_attributes"], args["get_all_attributes"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["get_all_attributes"], args["get_all_attributes"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- %s Attributes -\n" % args["get_all_attributes"])
    for i in data["Attributes"].items():
        print("Attribute Name: %s, Attribute Value: %s" % (i[0], i[1]))

def get_network_device_specific_attribute():
    network_id = args["get_all_attributes"].split("-")[0]
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["get_all_attributes"], args["get_all_attributes"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["get_all_attributes"], args["get_all_attributes"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data["Attributes"].items():
        if i[0] == args["get_attribute"]:
            print("\nAttribute Name: %s, Attribute value: %s" % (i[0], i[1]))
            sys.exit(0)
        else:
            pass
    print("\n - INFO, unable to locate attribute %s. Confirm you passed in correct case for attribute" % args["get_attribute"])
    
def network_registry():
    try:
        os.remove("nic_attribute_registry.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step to delete file" % "nic_attribute_registry.txt")
    open_file = open("nic_attribute_registry.txt","w")
    if idrac_fw_version >= "6000000":
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Registries' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Registries' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        network_uris = []
        for i in data["Members"]:
            for ii in i.items():
                if "NetworkAttributesRegistry" in ii[1]:
                    network_uris.append(ii[1])
        for i in network_uris:
            message = "\nRegistry attribute details for URI %s\n" % i
            open_file.writelines(message)
            print(message)
            message = "\n"
            open_file.writelines(message)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, data["Location"][0]["Uri"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, data["Location"][0]["Uri"]), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            for i in data['RegistryEntries']['Attributes']:
                for ii in i.items():
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    print(message)
                    message = "\n"
                    open_file.writelines(message)
                message = "\n"
                print(message)
                open_file.writelines(message)  
    else:       
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data['RegistryEntries']['Attributes']:
            for ii in i.items():
                message = "%s: %s" % (ii[0], ii[1])
                open_file.writelines(message)
                print(message)
                message = "\n"
                open_file.writelines(message)
            message = "\n"
            print(message)
            open_file.writelines(message)
    logging.info("\n- Attribute registry is also captured in \"nic_attribute_registry.txt\" file")
    open_file.close()

def create_network_attribute_dict():
    global network_attribute_payload
    network_attribute_payload = {"Attributes":{}}
    attribute_names = args["attribute_names"].split(",")
    attribute_values = args["attribute_values"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        network_attribute_payload["Attributes"][i] = ii
    if idrac_fw_version >= "6000000":
        network_registry_uri = "https://%s/redfish/v1/Registries/NetworkAttributesRegistry_%s/NetworkAttributesRegistry_%s.json" % (idrac_ip, args["set"], args["set"])
    else:
        network_registry_uri = "https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json" % idrac_ip
    if args["x"]:
        response = requests.get(network_registry_uri, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get(network_registry_uri, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in network_attribute_payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    network_attribute_payload['Attributes'][i[0]] = int(i[1])
    logging.info("\n- INFO, script will be setting network attribute(s) -\n")
    for i in network_attribute_payload["Attributes"].items():
        print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
    
def create_next_boot_config_job():
    global job_id
    global payload_patch
    network_id = args["set"].split("-")[0]
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s/Settings" % (idrac_ip, network_id, args["set"], args["set"])
    payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    payload_patch.update(network_attribute_payload)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: PATCH command passed to set network attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to set network attribute pending values and create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure is:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, NIC config job ID %s successfully created" % job_id)

def create_schedule_config_job():
    global job_id
    network_id = args["set"].split("-")[0]
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s/Settings" % (idrac_ip, network_id, args["set"], args["set"])
    if args["maintenance_reboot"] == "noreboot":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "InMaintenanceWindowOnReset","MaintenanceWindowStartTime":str(args["start_time"]),"MaintenanceWindowDurationInSeconds": int(args["duration_time"])}}
    elif args["maintenance_reboot"] == "autoreboot":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(args["start_time"]),"MaintenanceWindowDurationInSeconds": int(args["duration_time"])}}        
    else:
        logging.error("- FAIL, invalid value passed in for maintenance window job type")
        sys.exit(0)
    payload_patch.update(network_attribute_payload)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: PATCH command passed to set BIOS attribute pending values and create maintenance window config job, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create maintenance window config job, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, BIOS config job ID %s successfully created" % job_id)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    time.sleep(5)
    logging.info("\n--- PASS, Detailed Job Status Results ---\n")
    for i in data.items():
        pprint(i)
    if args["maintenance_reboot"] == "noreboot":                
        logging.info("\n- PASS, %s maintenance window config jid successfully created.\n\n- INFO, noreboot value detected, config job will go to scheduled state once start time has elapsed. You will need to either manually reboot the server or schedule a seperate server reboot during the maintenance window for the config job to execute.\n" % (job_id))
    elif args["maintenance_reboot"] == "autoreboot":
        logging.info("\n- PASS %s maintenance window config jid successfully created.\n\n- INFO, autoreboot value detected, config job will go to scheduled state once start time has elapsed and automatically reboot the server to apply the configuration job" % job_id)

def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
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
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, staged config job marked as scheduled")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 1
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if data['JobType'] == "RAIDConfiguration":
        logging.info("- PASS, staged jid \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
    elif data['JobType'] == "RealTimeNoRebootConfiguration":
        logging.info("- PASS, realtime jid \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(15)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % statusCode)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
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
    get_idrac_version()
    if args["get_ids"]:
        get_network_device_fqdds()
    elif args["get_idrac_time"]:
        get_idrac_time()
    elif args["get_all_attributes"] and args["get_attribute"]:
        get_network_device_specific_attribute()
    elif args["get_all_attributes"]:
              get_network_device_attributes()
    elif args["get_all_registry"]:
        network_registry()
    elif args["attribute_names"] and args["attribute_values"]:
        create_network_attribute_dict()
        if args["maintenance_reboot"] and args["start_time"] and args["duration_time"]:
            create_schedule_config_job()
        elif args["reboot"]:
            create_next_boot_config_job()
            get_job_status_scheduled()
            reboot_server()
            time.sleep(20)
            loop_job_status_final()
        else:
            create_next_boot_config_job()
            get_job_status_scheduled()
            logging.info("- INFO, argument --reboot not detected, server will not auto reboot. Config job is still scheduled and will execute on next server manual reboot.")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

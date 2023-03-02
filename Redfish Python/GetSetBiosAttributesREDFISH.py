#!/usr/bin/python3
#
# GetSetBiosAttributesREDFISH. Python script using Redfish API DMTF to either get or set BIOS attributes using Redfish SettingApplyTime.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 18.0
#
# Copyright (c) 2019, Dell, Inc.
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
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get or set BIOS attributes using Redfish SettingApplyTime. If needed, run a GET on URI \"redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry\" to see supported possible values for setting attributes.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get all BIOS attributes', action="store_true", required=False)
parser.add_argument('--get-attribute', help='If you want to get only a specific BIOS attribute, pass in the attribute name you want to get the current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail', dest="get_attribute", required=False)
parser.add_argument('--get-registry', help='Get complete BIOS attribute registry', dest="get_registry", action="store_true", required=False)
parser.add_argument('--get-registry-attribute', help='Get registry information for a specific attribute, pass in the attribute name', dest="get_registry_attribute", required=False)
parser.add_argument('--attribute-names', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: -r (reboot type) is required when setting attributes', dest="attribute_names", required=False)
parser.add_argument('--attribute-values', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value.', dest="attribute_values", required=False)
parser.add_argument('--reboot', help='Pass in argument to reboot the server now to execute config job. If argument is not passed in, next manual server reboot job will be execute.', action="store_true", required=False)
parser.add_argument('--maintenance-reboot', help='Pass in the type of maintenance window job type you want to create. Pass in \"autoreboot\" if you want the server to automatically reboot and apply the changes once the maintenance windows has been hit. Pass in \"noreboot\" if you don\'t want the server to automatically reboot once the maintenance window time has hit. If you select this option, user will have to reboot the server to apply the configuration job.', dest="maintenance_reboot", required=False)
parser.add_argument('--start-time', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', dest="start_time", required=False)
parser.add_argument('--duration-time', help='Maintenance window duration time(amount of time allowed to execute and complete the config job), pass in a value in seconds', dest="duration_time", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get all BIOS attributes.
    \n- GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root --get-attribute SetBootOrderEn, this example will first prompt to enter iDRAC user password, then return details for this specific attribute.
    \n- GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651aac --get-registry, this example using iDRAC X-auth token session will return attribute registry details. 
    \n- GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --attribute-names MemTest --attribute-values Disabled --maintenance-reboot autoreboot --start-time "2018-10-30T20:10:10-05:00" --duration-time 600, this example shows setting BIOS attribute using scheduled start time with maintenance window. Once the scheduled time has elapsed, server will auto reboot to execute config job.
    \n- GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --attribute-names EmbSata,NvmeMode --attribute-values RaidMode,Raid --reboot, this example shows setting multiple BIOS attributes with reboot now to apply.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_bios_attributes():
    try:
        os.remove("bios_attributes.txt")
    except:
        pass
    open_file = open("bios_attributes.txt","w")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    get_datetime = datetime.now()
    current_date_time = "- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (get_datetime.year, get_datetime.month, get_datetime.day, get_datetime.hour, get_datetime.minute, get_datetime.second)
    open_file.writelines(current_date_time)
    create_string = "\n--- BIOS Attributes ---\n"
    logging.info(create_string)
    open_file.writelines(create_string)
    for i in data['Attributes'].items():
        attribute_name = "Attribute Name: %s\t" % (i[0])
        open_file.writelines(attribute_name)
        attribute_value = "Attribute Value: %s\n" % (i[1])
        open_file.writelines(attribute_value)
        pprint(i)
    logging.info("\n- Attributes are also captured in \"bios_attributes.txt\" file")
    open_file.close()

def get_specific_bios_attribute():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data['Attributes'].items():
        if i[0] == args["get_attribute"]:
            logging.info("\n- Current value for attribute \"%s\": \"%s\"\n" % (args["get_attribute"], i[1]))
            return
    logging.error("\n- ERROR, unable to get attribute current value. Either attribute doesn't exist for this BIOS version, typo in attribute name or case incorrect")
    sys.exit(0)

def bios_registry():
    try:
        os.remove("bios_attribute_registry.txt")
    except:
        pass
    open_file = open("bios_attribute_registry.txt","a")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attribute registry, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data['RegistryEntries']['Attributes']:
        for ii in i.items():
            pprint(i)
            print("\n")
            message = "%s: %s" % (ii[0], ii[1])
            open_file.writelines(message)
            message = "\n"
            open_file.writelines(message)
        message = "\n"
        open_file.writelines(message)
    logging.info("\n- Attribute registry is also captured in \"bios_attribute_registry.txt\" file")
    open_file.close()

def bios_registry_get_specific_attribute():
    logging.info("\n- INFO, searching BIOS registry for attribute \"%s\"" % args["get_registry_attribute"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attribute registry, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data['RegistryEntries']['Attributes']:
        if args["get_registry_attribute"] in i.values():
            logging.info("\n- Attribute Registry information for attribute \"%s\" -\n" % args["get_registry_attribute"])
            for ii in i.items():
                pprint(i)
                return
    logging.error("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % args["get_registry_attribute"])
    
def create_bios_attribute_dict():
    global bios_attribute_payload
    global start_time
    start_time = datetime.now()
    bios_attribute_payload = {"Attributes":{}}
    attribute_names = args["attribute_names"].split(",")
    attribute_values = args["attribute_values"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        bios_attribute_payload["Attributes"][i] = ii
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attribute registry, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in bios_attribute_payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    bios_attribute_payload['Attributes'][i[0]] = int(i[1])
    logging.info("\n- INFO, script will be setting BIOS attribute(s) -\n")
    for i in bios_attribute_payload["Attributes"].items():
        logging.info("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
    
def create_next_boot_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    payload.update(bios_attribute_payload)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: PATCH command passed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, BIOS config job ID %s successfully created" % job_id)

def create_schedule_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    if args["maintenance_reboot"] == "noreboot":
        payload = {"@Redfish.SettingsApplyTime":{"ApplyTime": "InMaintenanceWindowOnReset","MaintenanceWindowStartTime":str(args["start_time"]),"MaintenanceWindowDurationInSeconds": int(args["duration_time"])}}
    elif args["maintenance_reboot"] == "autoreboot":
        payload = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(args["start_time"]),"MaintenanceWindowDurationInSeconds": int(args["duration_time"])}}        
    else:
        logging.error("- FAIL, invalid value passed in for maintenance window job type")
        sys.exit(0)
    payload.update(bios_attribute_payload)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
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
            if "powercyclerequest" in args["attribute_names"].lower():
                logging.info("- INFO, PowerCycleRequest attribute detected, virtual a/c cycle is running. Script will sleep for 180 seconds, retry")
                time.sleep(180)
            else:
                time.sleep(15)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % response.status_code)
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
    if args["get"]:
        get_bios_attributes()
    elif args["get_attribute"]:
        get_specific_bios_attribute()
    elif args["get_registry_attribute"]:
        bios_registry_get_specific_attribute()
    elif args["get_registry"]:
        bios_registry() 
    elif args["attribute_names"] and args["attribute_values"]:
        create_bios_attribute_dict()
        if args["maintenance_reboot"] and args["start_time"] and args["duration_time"]:
            create_schedule_config_job()
        elif args["reboot"]:
            create_next_boot_config_job()
            get_job_status_scheduled()
            reboot_server()
            loop_job_status_final()
        else:
            create_next_boot_config_job()
            get_job_status_scheduled()
            logging.info("- INFO, argument --reboot not detected, server will not auto reboot. Config job is still scheduled and will execute on next server manual reboot.")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

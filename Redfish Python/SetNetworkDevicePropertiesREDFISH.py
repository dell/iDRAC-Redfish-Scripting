#!/usr/bin/python3
#
# SetNetworkDevicePropertiesREDFISH. Python script using Redfish API to either get network devices/ports or set network properties.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 9.0
#
# Copyright (c) 2018, Dell, Inc.
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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to either get network devices/ports or set network properties")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--generate-ini', help='Pass in this argument to generate ini file with payload dictionary to set properties. If setting properties, make sure to generate this ini file first. This file is needed to pass in the properties you want to configure', action="store_true", dest="generate_ini", required=False)
parser.add_argument('--get-fqdds', help='Get server network FQDD devices', action="store_true", dest="get_fqdds", required=False)
parser.add_argument('--get-device-details', help='Get network device details, pass in network device ID, Example \"NIC.Integrated.1\"', dest="get_device_details", required=False)
parser.add_argument('--get-port-details', help='Get network device port details, pass in network port ID, Example \"NIC.Integrated.1-1-1\" ', dest="get_port_details", required=False)
parser.add_argument('--get-properties', help='Get properties (attributes) for network device, pass in network port ID . Example \"NIC.Integrated.1-1-1\"', dest="get_properties", required=False)
parser.add_argument('--set', help='To set network properties, pass in network port ID, Example \"NIC.Integrated.1-1-1\" ', required=False)
parser.add_argument('--reboot', help='Pass in value for reboot type. Pass in \"n\" for server to reboot now and apply changes immediately. Pass in \"l\" which will schedule the job but system will not reboot. Next manual server reboot, job will be applied. Pass in \"s\" to create a maintenance window config job. Job will go to schedule state once maintenance window has started', required=False)
parser.add_argument('--start-time', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', dest="start_time", required=False)
parser.add_argument('--duration-time', help='Maintenance window duration time, pass in a value in seconds', dest="duration_time", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-fqdds, this example will return network devices detected for your server.
    \n- SetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-properties NIC.Integrated.1-1-1, this example will return NIC properties for NIC.Integrated.1-1-1 port.
    \n- SetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --generate-ini, this example will generate the ini file needed to set NIC properties. It will also return an example of a modified dictionary for the ini file.
    \n- SetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin --set NIC.Integrated.1-1-1 --reboot n, this example is going to apply property changes immediately from the ini file to NIC.Integrated.1-1-1.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    
def generate_payload_dictionary_file():
    payload = {"iSCSIBoot":{},"FibreChannel":{}}
    with open("set_network_properties.ini","w") as x:
        json.dump(payload,x)
    logging.info("\n- INFO, \"set_network_properties.ini\" file created. This file contains payload dictionary which will be used to set network properties.\n")
    logging.info("Modify the payload dictionary passing in property names and values for the correct group.\n")
    logging.info("Example of modified dictionary: {\"iSCSIBoot\":{\"InitiatorIPAddress\":\"192.168.0.120\",\"InitiatorNetmask\":\"255.255.255.0\"},\"FibreChannel\":{\"FCoELocalVLANId\":100}}\n")
    
def get_network_devices():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    logging.info("\n- Network device ID(s) detected -\n")
    network_device_list = []
    for i in data['Members']:
        for ii in i.items():
            network_device = ii[1].split("/")[-1]
            network_device_list.append(network_device)
            print(network_device)
    for i in network_device_list:
        port_list = []
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
            logging.error(data)
            sys.exit(0)
        logging.info("\n- Network port ID(s) detected for %s -\n" % i)
        for i in data['Members']:
            for ii in i.items():
                print(ii[1].split("/")[-1])

def get_detail_network_device_info():   
    logging.info("\n - Detailed network device information for %s -\n" % args["get_device_details"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s' % (idrac_ip, args["get_device_details"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s' % (idrac_ip, args["get_device_details"]), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data.items():
        pprint(i)

def get_network_device_port_info():
    if "FC" in args["get_port_details"]:
        port_device = args["get_port_details"]
        id_device = args["get_port_details"][:-2]
    else:
        port_device = args["get_port_details"][:-2]
        id_device = args["get_port_details"][:-4]
    logging.info("\n - Detailed network port information for %s -\n" % args["get_port_details"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkPorts/%s' % (idrac_ip, id_device, port_device), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkPorts/%s' % (idrac_ip, id_device, port_device), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data.items():
        pprint(i)

def get_network_device_properties():
    logging.info("\n- Properties for network device %s -" % args["get_properties"])
    if "FC" in args["get_properties"]:
        id_device = args["get_properties"][:-2]
    else:
        id_device = args["get_properties"][:-4]
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, id_device, args["get_properties"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, id_device, args["get_properties"]), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data.items():
        if i[0] == 'iSCSIBoot':
            if i[1] != None:
                logging.info("\n - iSCSIBoot Attributes -\n")
                for i in data['iSCSIBoot'].items():
                    print("%s: %s" % (i[0],i[1]))
    for i in data.items():
        if i[0] == 'FibreChannel':
            if i[1] != None:
                logging.info("\n - FibreChannel Attributes -\n")
                for i in data['FibreChannel'].items():
                    print("%s: %s" % (i[0],i[1]))
            
def set_network_properties():
    global job_id
    global port_device
    global id_device
    try:
        with open("set_network_properties.ini","r") as x:
            payload = json.load(x)
    except:
        logging.error("\n- FAIL, \"set_network_properties.ini\" file does not exist. Execute the script with -g to generate the ini file which is needed to set attributes")
        sys.exit(0)
    if 'iSCSIBoot' in payload:
        if payload['iSCSIBoot'] == {}:
            del payload['iSCSIBoot']
    if 'FibreChannel' in payload:
        if payload['FibreChannel'] == {}:
            del payload['FibreChannel']
    if "FC" in args["set"]:
        port_device = args["set"]
        id_device = args["set"][:-2]
    else:
        port_device = args["set"]
        id_device = args["set"][:-4]
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    for i in payload.items():
        if type(i[1]) == dict:
            logging.info("\n- INFO, setting properties for %s group:\n" % i[0])
            for ii in i[1].items():
                logging.info("Property Name: %s, Pending New Value: %s" % (ii[0], ii[1]))
    time.sleep(3)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: PATCH command passed to set property pending value, status code 200 returned")
    else:
        logging.error("\n- FAIL, PATCH command failed to set properties, status code is %s, failure is:\n%s" % (response.status_code, data))
        sys.exit(0)
   
def create_reboot_now_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to create reboot now config job, status code 202 returned")
    else:
        logging.error("\n- FAIL, PATCH command failed to create reboot now config job, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure is:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("\n- PASS, %s reboot now config jid successfully created\n" % (job_id))

def create_next_boot_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to create next reboot config job, status code 202 returned")
    else:
        logging.error("\n- FAIL, PATCH command failed to create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure is:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("\n- PASS, %s next reboot config jid successfully created\n" % (job_id))

def create_schedule_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(start_time_input),"MaintenanceWindowDurationInSeconds": int(duration_time)}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to create maintenance window config job, status code 202 returned")
    else:
        logging.error("\n- FAIL, PATCH command failed to create maintenance window config job, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure is:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    time.sleep(5)
    logging.info("\n--- PASS, Detailed Job Status Results ---\n")
    for i in data.items():
        if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
            print("%s: %s" % (i[0],i[1]))                  
    logging.info("\n- PASS, %s maintenance window config jid successfully created.\n\nJob will go to scheduled state once job start time has elapsed. You will need to schedule a seperate server reboot during the maintenance windows for the config job to execute. NOTE: If using iDRAC version 4.20 or newer, a reboot job will now get created and scheduled at the same time of the configuration job. Server will automatically reboot once scheduled time has been hit.\n" % (job_id))
    
def loop_job_status():
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            logging.error("- FAIL: %s failed" % job_id)
            sys.exit(0)
        elif data['Message'] == "Job completed successfully.":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                    print("%s: %s" % (i[0],i[1]))
            logging.info("\n- %s job execution time: %s" % (job_id,str(current_time)[0:7]))
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
            time.sleep(10)

def get_job_status():
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            if args["reboot"] == "n":
                logging.info("\n- INFO, config job marked as scheduled, system will now reboot to apply configuration changes")
            elif args["reboot"] == "l":
                logging.info("\n- INFO, staged config job marked as scheduled, next manual reboot of system will apply configuration changes\n")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

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
            logging.info("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % response.status_code)
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
                    logging.info("- PASS, POST command passed to perform forced shutdown, status code return is %s" % response.status_code)
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
            logging.info("- PASS, Command passed to power ON server, status code return is %s" % response.status_code)
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
    if args["get_fqdds"]:
        get_network_devices()
    elif args["generate_ini"]:
        generate_payload_dictionary_file()
    elif args["get_device_details"]:
        get_detail_network_device_info()
    elif args["get_port_details"]:
        get_network_device_port_info()
    elif args["get_properties"]:
        get_network_device_properties()
    elif args["set"]:
        set_network_properties()
        time.sleep(5)
        if args["reboot"] == "n":
            create_next_boot_config_job()
            get_job_status()
            reboot_server()
            loop_job_status()
        elif args["reboot"] == "l":
            create_next_boot_config_job()
            get_job_status()
        elif args["reboot"] == "s" and args["start_time"] and args["duration_time"]:
            create_schedule_config_job()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
            
        


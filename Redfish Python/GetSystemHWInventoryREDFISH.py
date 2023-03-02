#!/usr/bin/python3
#
# GetSystemHWInventoryREDFISH. Python script using Redfish API to get system hardware inventory
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 8.0
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
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to get system hardware inventory(output will be printed to the screen and also copied to a text file). This includes information for storage controllers, memory, network devices, general system details, power supplies, hard drives, fans, backplanes, processors")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--system', help='Get system information', action="store_true", required=False)
parser.add_argument('--memory', help='Get memory information', action="store_true", required=False)
parser.add_argument('--processor', help='Get processor information', action="store_true", required=False)
parser.add_argument('--fan', help='Get fan information', action="store_true", required=False)
parser.add_argument('--powersupply', help='Get power supply information', action="store_true", required=False)
parser.add_argument('--storage', help='Get storage information', action="store_true", required=False)
parser.add_argument('--network', help='Get network device information', action="store_true", required=False)
parser.add_argument('--all', help='Get all system/device information', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --memory, this example will get only memory information.
    \n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --processor --memory, this example will get only processor and memory information.
    \n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --all, this example will get all system information: general system information, processor, memory, fans, power supplies, hard drives, storage controllers, network devices""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_system_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        message = "\n---- System Information ----\n"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
    for i in data.items():
        if i[0] == "Oem":
            for ii in i[1]['Dell']['DellSystem'].items():
                if ii[0] != '@odata.context' or ii[0] != '@odata.type':
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)       
        elif i[0] == "Model" or i[0] == "AssetTag" or i[0] == "BiosVersion" or i[0] == "HostName" or i[0] == "Manufacturer" or i[0] == "System" or i[0] == "SKU" or i[0] == "SerialNumber" or i[0] == "Status":
                message = "%s: %s" % (i[0], i[1])
                open_file.writelines(message)
                open_file.writelines("\n")
                print(message)
    
def get_memory_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        message = "\n---- Memory Information ----"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
    for i in data['Members']:
        dimm = i['@odata.id'].split("/")[-1]
        try:
            dimm_slot = re.search("DIMM.+",dimm).group()
        except:
            logging.error("\n- FAIL, unable to get dimm slot info")
            sys.exit(0)
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, get command failed, error: %s" % sub_data)
            sys.exit(0)
        else:
            message = "\n- Memory details for %s -\n" % dimm_slot
            open_file.writelines(message)
            open_file.writelines("\n")
            print(message)
            for ii in sub_data.items():
                if ii[0] == 'Oem':
                    for iii in ii[1]['Dell']['DellMemory'].items():
                        if iii[0] != '@odata.context' or iii[0] != '@odata.type':
                            message = "%s: %s" % (iii[0], iii[1])
                            open_file.writelines(message)
                            open_file.writelines("\n")
                            print(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)
    
def get_cpu_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        message = "\n---- Processor Information ----"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
    for i in data['Members']:
        cpu = i['@odata.id'].split("/")[-1]
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error: %s" % sub_data)
            sys.exit(0)
        else:
            message = "\n- Processor details for %s -\n" % cpu
            open_file.writelines(message)
            open_file.writelines("\n")
            print(message)
            for ii in sub_data.items():
                if ii[0] == 'Oem':
                    for iii in ii[1]['Dell']['DellProcessor'].items():
                        if iii[0] != '@odata.context' or iii[0] != '@odata.type':
                            message = "%s: %s" % (iii[0], iii[1])
                            open_file.writelines(message)
                            open_file.writelines("\n")
                            print(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)

def get_fan_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        message = "\n---- Fan Information ----\n"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
    fan_list = []
    if data['Links']['CooledBy'] == []:
        logging.warning("\n- WARNING, no fans detected for system")
    else:
        for i in data['Links']['CooledBy']:
            for ii in i.items():
                fan_list.append(ii[1])
        for i in fan_list:
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logging.error("\n- FAIL, get command failed, error: %s" % data)
                sys.exit(0)
            else:
                data_get = response.json()
                if "Fans" not in data_get.keys():
                    for ii in data_get.items():
                        message = "%s: %s" %  (ii[0], ii[1])
                        open_file.writelines(message)
                        print(message)
                        message = "\n"
                        open_file.writelines(message)
                    message = "\n"
                    open_file.writelines(message)
                    print(message)
                else:
                    count = 0
                    while True:
                        if count == len(fan_list):
                            return
                        for i in data_get["Fans"]:
                            message = "\n- Details for %s -\n" % i["FanName"]
                            count += 1
                            open_file.writelines(message)
                            print(message)
                            message = "\n"
                            open_file.writelines(message)
                            for ii in i.items():
                                message = "%s: %s" %  (ii[0], ii[1])
                                open_file.writelines(message)
                                print(message)
                                message = "\n"
                                open_file.writelines(message)
                                
def get_ps_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        message = "\n---- Power Supply Information ----\n"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
    if data['Links']['PoweredBy'] == []:
        logging.error("- WARNING, no power supplies detected for system")       
    else:
        for i in data['Links']['PoweredBy']:
            for ii in i.items():
                if args["x"]:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                else:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, auth=(idrac_username, idrac_password))
                if response.status_code != 200:
                    logging.error("\n- FAIL, get command failed, error: %s" % data)
                    sys.exit(0)
                else:
                    data_get = response.json()
                    if "PowerSupplies" not in data_get.keys():
                        message = "\n- Details for %s -\n" % data_get["Name"]
                        open_file.writelines(message)
                        open_file.writelines("\n")
                        print(message)
                        for i in data_get.items():
                            if i[0] == "Oem":
                                try:
                                    for ii in i[1]["Dell"]["DellPowerSupply"].items():
                                        message = "%s: %s" % (ii[0],ii[1])
                                        open_file.writelines(message)
                                        open_file.writelines("\n")
                                        print(message)
                                except:
                                    logging.error("- FAIL, unable to find Dell PowerSupply OEM information")
                                    sys.exit(0)
                            else:
                                message = "%s: %s" % (i[0],i[1])
                                open_file.writelines(message)
                                open_file.writelines("\n")
                                print(message)             
                    else:
                        if len(data['Links']['PoweredBy']) == 1:
                            message = "\n- Details for %s -\n" % data_get["PowerSupplies"][0]["Name"]
                            open_file.writelines(message)
                            open_file.writelines("\n")
                            print(message)
                            for i in data_get.items():
                                if i[0] == "PowerSupplies":
                                    for ii in i[1]:
                                        for iii in ii.items():
                                            if iii[0] == "Oem":
                                                try:
                                                    for iiii in iii[1]["Dell"]["DellPowerSupply"].items():
                                                        message = "%s: %s" % (iiii[0],iiii[1])
                                                        open_file.writelines(message)
                                                        open_file.writelines("\n")
                                                        print(message)
                                                except:
                                                    logging.error("- FAIL, unable to find Dell PowerSupply OEM information")
                                                    sys.exit(0)
                                                
                                            else:
                                                message = "%s: %s" % (iii[0],iii[1])
                                                open_file.writelines(message)
                                                open_file.writelines("\n")
                                                print(message)
                                elif i[0] == "PowerControl" and i[0] != "Voltages":
                                    for ii in i[1]:
                                        for iii in ii.items():
                                            message = "%s: %s" % (iii[0],iii[1])
                                            open_file.writelines(message)
                                            open_file.writelines("\n")
                                            print(message)
                                else:
                                    message = "%s: %s" % (i[0],i[1])
                                    open_file.writelines(message)
                                    open_file.writelines("\n")
                                    print(message)
                            print("\n")
                            open_file.writelines("\n")
                        else:
                            for i in data_get.items():
                                if i[0] == "PowerSupplies":
                                    psu_ids = i[1]
                            count = 0
                            while True:
                                if len(psu_ids) == count:
                                    return
                                else:
                                    for i in psu_ids:
                                        message = "\n- Details for %s -\n" % i["Name"]
                                        open_file.writelines(message)
                                        open_file.writelines("\n")
                                        print(message)
                                        for ii in i.items():
                                            if ii[0] == "Oem":
                                                try:
                                                    for iii in ii[1]["Dell"]["DellPowerSupply"].items():
                                                        message = "%s: %s" % (iii[0],iii[1])
                                                        open_file.writelines(message)
                                                        open_file.writelines("\n")
                                                        print(message)
                                                except:
                                                    logging.error("- FAIL, unable to find Dell PowerSupply OEM information")
                                                    sys.exit(0)
                                            else:
                                                message = "%s: %s" % (ii[0],ii[1])
                                                open_file.writelines(message)
                                                open_file.writelines("\n")
                                                print(message)
                                        print("\n")
                                        count += 1

def get_storage_controller_information():
    global controller_list
    message = "\n---- Controller Information ----"
    open_file.writelines(message)
    open_file.writelines("\n")
    print(message)
    controller_list = []
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    data = response.json()
    for i in data["Members"]:
        for ii in i.items():
            controller_list.append(ii[1])
    for i in controller_list:
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        message = "\n - Detailed controller information for %s -\n" % i.split("/")[-1]
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
        for i in data.items():
            if i[0] == 'StorageControllers':
                for ii in i[1]:
                    for iii in ii.items():
                        if iii[0] == 'Status':
                            for iiii in iii[1].items():
                                message = "%s: %s" % (iiii[0],iiii[1])
                                open_file.writelines(message)
                                open_file.writelines("\n")
                                print(message)
                        else:
                            message = "%s: %s" % (iii[0],iii[1])
                            open_file.writelines(message)
                            open_file.writelines("\n")
                            print(message)
            elif i[0] == 'Oem':
                try:
                    for ii in i[1]['Dell']['DellController'].items():
                        message = "%s: %s" % (ii[0],ii[1])
                        open_file.writelines(message)
                        open_file.writelines("\n")
                        print(message)
                except:
                    for ii in i[1]['Dell'].items():
                        message = "%s: %s" % (ii[0],ii[1])
                        open_file.writelines(message)
                        open_file.writelines("\n")
                        print(message)        
            else:
                message = "%s: %s" % (i[0], i[1])
                open_file.writelines(message)
                open_file.writelines("\n")
                print(message)

def get_storage_disks_information():
    message = "\n---- Disk Information ----"
    open_file.writelines(message)
    open_file.writelines("\n")
    print(message)
    for i in controller_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i.split("/")[-1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i.split("/")[-1]), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("- FAIL, GET command failed, detailed error information: %s" % data)
            sys.exit(0)
        if data['Drives'] == []:
            message = "\n- WARNING, no drives detected for %s" % i.split("/")[-1]
            open_file.writelines(message)
            open_file.writelines("\n")
            print(message)
        else:
            for i in data['Drives']:
                for ii in i.items():
                    if args["x"]:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                    else:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, auth=(idrac_username, idrac_password))
                    data = response.json()
                    message = "\n - Detailed drive information for %s -\n" % ii[1].split("/")[-1]
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)
                    for ii in data.items():
                        if ii[0] == 'Oem':
                            for iii in ii[1]['Dell']['DellPhysicalDisk'].items():
                                message = "%s: %s" % (iii[0],iii[1])
                                open_file.writelines(message)
                                open_file.writelines("\n")
                                print(message)
                        elif ii[0] == 'Status':
                            for iii in ii[1].items():
                                message = "%s: %s" % (iii[0],iii[1])
                                open_file.writelines(message)
                                open_file.writelines("\n")
                                print(message)
                        else:
                            message = "%s: %s" % (ii[0],ii[1])
                            open_file.writelines(message)
                            open_file.writelines("\n")
                            print(message)
                
def get_backplane_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit(0)
    message = "\n---- Backplane Information ----"
    open_file.writelines(message)
    open_file.writelines("\n")
    print(message)
    backplane_URI_list = []
    for i in data['Members']:
        backplane = i['@odata.id']
        if "Enclosure" in backplane:
            backplane_URI_list.append(backplane)
    if backplane_URI_list == []:
        message = "- WARNING, no backplane information detected for system\n"
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
        sys.exit()
    for i in backplane_URI_list:
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        message = "\n- Detailed backplane information for %s -\n" % i.split("/")[-1]
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
        for iii in data.items():
            if iii[0] == "Oem":
                for iiii in iii[1]['Dell']['DellEnclosure'].items():
                    message = "%s: %s" % (iiii[0],iiii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)       
            else:
                message = "%s: %s" % (iii[0], iii[1])
                open_file.writelines(message)
                open_file.writelines("\n")
                print(message)   

def get_network_information():
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
        for i in data['Members']:
            for ii in i.items():
                port_list.append(ii[1].split("/")[-1])
    for i in network_device_list:
        device_id = re.search("\w+.\w+.\w", i).group()
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, get command failed, error is: %s" % data)
            sys.exit(0)
        message = "\n---- Network Device Information for %s ----\n" % i
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
        for i in data.items():
            if i[0] == "Controllers":
                for ii in i[1][0]["ControllerCapabilities"].items():
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)
            else:
                message = "%s: %s" % (i[0], i[1])
                open_file.writelines(message)
                open_file.writelines("\n")
                print(message)
    for i in port_list:
        device_id = re.search("\w+.\w+.\w", i).group()
        # redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/NIC.Embedded.1/NetworkDeviceFunctions/NIC.Embedded.1-1-1
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, device_id, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, device_id, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, get command failed, error is: %s" % data)
            sys.exit(0)
        message = "\n---- Network Port Information for %s ----\n" % i
        open_file.writelines(message)
        open_file.writelines("\n")
        print(message)
        for i in data.items():
            if i[0] == "Oem":
                for ii in i[1]['Dell']['DellNIC'].items():
                    message = "%s: %s" % (ii[0],ii[1])
                    open_file.writelines(message)
                    open_file.writelines("\n")
                    print(message)  
            else:
                message = "%s: %s" % (i[0], i[1])
                open_file.writelines(message)
                open_file.writelines("\n")
                print(message)

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
    try:
        os.remove("hw_inventory.txt")
    except:
        logging.debug("- INFO, file %s not detected, skipping step to delete file" % "hw_inventory.txt")
    open_file = open("hw_inventory.txt","a")
    date_timestamp = datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (date_timestamp.month, date_timestamp.day, date_timestamp.year, date_timestamp.hour, date_timestamp.minute, date_timestamp.second)
    open_file.writelines(current_date_time)
    if args["system"]:
        get_system_information()
    if args["memory"]:
        get_memory_information()
    if args["processor"]:
        get_cpu_information()
    if args["fan"]:
        get_fan_information()
    if args["powersupply"]:
        get_ps_information()
    if args["storage"]:
        get_storage_controller_information()
        get_storage_disks_information()
        get_backplane_information()
    if args["network"]:
        get_network_information()
    if args["all"]:
        get_system_information()
        get_memory_information()
        get_cpu_information()
        get_fan_information()
        get_ps_information()
        get_storage_controller_information()
        get_storage_disks_information()
        get_backplane_information()
        get_network_information()
    open_file.close()

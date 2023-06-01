# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
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
# Python script using Redfish API to get network properties for a specific network device FQDD for multiple attributes which will copy the contents to a CSV file.
# Script will get parameter details using INI file. 
#
# Pseudo code workflow
#
# 1. Confirm IP address can be pinged.
# 2. Check remote API status, confirm LC status report ready.
# 3. Get network device properties for the network device fQDD passed in the INI file.
# 4. Write network property headers to CSV file.
# 5. Write property values to CSV file.
# 6. All output will be echoed to the screen and also captured in a log file (log file name: "network_device_script_logfile.txt")
#
# INI file examples("network_device_config.ini" INI file name):
#
# [Parameters]
# idrac_ips=192.168.0.130,192.168.0.140,192.168.0.150
# idrac_username=root
# idrac_password=calvin
# network_device_fqdd=FC.Slot.3-1
# network_device_properties=wwnn,wwpn
# csv_filename=network_device_property_details.csv
# get_network_device_fqdds=no
# get_network_device_properties_only=no
#
# This example shows passing in multiple iDRAC IPs using a comma separator
#
# NOTE: Pass in any unique name for the CSV file getting generated.
#
# NOTE: For network_device_fqdd, pass in the FQDD string that will be common across all servers. If the FQDD string is invalid or does not exist on the server, script will skip this iDRAC.
#
# NOTE: To get only network device FQDDs returned for all iDRACs, pass in a value of yes for parameter get_network_device_fqdds.
#
# NOTE: To get only network device properties using FQDD from the INI file for all iDRACs, pass in a value of yes for parameter get_network_device_fqdds.
#
# NOTE: For network_device_properties, use a comma separator if passing in multiple values.
#
# [Parameters]
# idrac_ips=192.168.0.130-140
# idrac_username=root
# idrac_password=calvin
# network_device_fqdd=NIC.Integrated.1-1-1
# network_device_properties=macaddress
# csv_filename=network_device_property_details.csv
# get_network_device_fqdds=no
# get_network_device_properties_only=no
#
# This example shows passing in range of iDRAC IPs. Script will loop through IPs starting at 192.168.0.130 up to 192.168.0.140.
#
# NOTES: All iDRAC IPs passed in the INI file must have the same username and password
#        INI file name used to run this script must be "network_device_config.ini" and located in the same directory you're running the script from. 

import configparser
import csv
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

if os.path.exists("network_device_script_logfile.txt"):
    os.remove("network_device_script_logfile.txt")
    
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logStreamFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s", datefmt="%H:%M:%S")
consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logStreamFormatter)
consoleHandler.setLevel(level=logging.INFO)
logger.addHandler(consoleHandler)
logFileFormatter = logging.Formatter(fmt=f"%(levelname)s %(asctime)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S",)
fileHandler = logging.FileHandler(filename="network_device_script_logfile.txt")
fileHandler.setFormatter(logFileFormatter)
fileHandler.setLevel(level=logging.INFO)
logger.addHandler(fileHandler)

config = configparser.ConfigParser()
config.read("network_device_config.ini")
config_ini_settings = config.items("Parameters")
idrac_ips = config.get("Parameters","idrac_ips")
idrac_username = config.get("Parameters","idrac_username")
idrac_password = config.get("Parameters","idrac_password")
network_device_fqdd = config.get("Parameters","network_device_fqdd")
network_device_properties = config.get("Parameters","network_device_properties")
csv_filename = config.get("Parameters","csv_filename")
get_network_device_fqdd_flag = config.get("Parameters","get_network_device_fqdds")
get_network_device_properties_flag = config.get("Parameters","get_network_device_properties_only")

if os.path.exists(csv_filename):
    os.remove(csv_filename)

if "," in network_device_properties:
    network_device_properties = network_device_properties.split(",")
else:
    network_device_properties = [network_device_properties]    

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

def get_network_device_fqdds(idrac_ip):
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    network_device_list = []
    for i in data['Members']:
        for ii in i.items():
            network_device = ii[1].split("/")[-1]
            network_device_list.append(network_device)
    logger.info("Network device FQDD(s) detected for iDRAC %s " % idrac_ip)
    for i in network_device_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i), verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data['Members']:
            for ii in i.items():
                logger.info(ii[1].split("/")[-1])

def get_remote_services(idrac_ip):
    # Function to get remote api status, lifecycle controller status
    global get_remote_service_failure
    get_remote_service_failure = "no"
    start_time = datetime.now()
    current_time = str(datetime.now()-start_time)[0:7]
    while True:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % idrac_ip
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
    
def get_network_device_properties(idrac_ip):
    # Function to get network device properties
    global supported_properties_dict
    global get_command_failure
    global print_properties_only
    get_command_failure = "no"
    print_properties_only = "no"
    device_id = network_device_fqdd.split("-")[0]
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, device_id, network_device_fqdd), verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        if "entered is not found" in data["error"]["@Message.ExtendedInfo"][0]["Message"].lower():
            logger.warning("Invalid FQDD passed in INI file or device not found, skipping iDRAC %s" % idrac_ip)
        else:    
            logger.error("GET command failed to get network device properties, status code %s returned" % response.status_code)
            logging.error(data)
        get_command_failure = "yes"
        return
    logger.info("Getting supported properties and values for FQDD \"%s\"" % network_device_fqdd)
    supported_properties_dict = {}
    if data["FibreChannel"] != {}:
        supported_properties_dict.update(data["FibreChannel"])
    if data["Ethernet"] != {}:
        supported_properties_dict.update(data["Ethernet"])
    if data["Status"] != {}:
        supported_properties_dict.update(data["Status"])
    for i in data["Oem"]["Dell"].items():
        if type(i[1]) == dict:
            supported_properties_dict.update(i[1])
    new_dict = {}
    for letter in supported_properties_dict:
        number = supported_properties_dict[letter]
        new_dict.update({letter.lower():number})
    supported_properties_dict = new_dict
    if get_network_device_properties_flag == "yes":
        print_properties_only = "yes"
        for i in supported_properties_dict.items():
            if "@" not in i[0]:
                logger.info(i[0])

def create_write_headers_csv_file():
    # Function to write headers only once to CSV file
    global write_headers_csv_file
    write_headers_csv_file = False
    headers = ["iDRAC", "Port FQDD"]
    for i in network_device_properties:
        if i.lower() in supported_properties_dict:
            headers.append(i.upper())
    with open(csv_filename, 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)    
    
def write_csv_file(idrac_ip):
    # Function to write property values to CSV file
    logger.info("Copying data to CSV file \"%s\"" % csv_filename)
    property_values = [idrac_ip, network_device_fqdd]
    for i in network_device_properties:
        for ii in supported_properties_dict.items():
            if i.lower() == ii[0].lower():
                if ii[1] == "" or ii[1] == None or ii[1] == "null":
                    property_values.append("None")
                else:
                    property_values.append(ii[1])
    with open(csv_filename, 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(property_values)
                                                                            
if __name__ == "__main__":
    write_headers_csv_file = True
    for idrac_address in idrac_ips:
        ping_confirm_valid_ip(idrac_address)
        if ping_success == "no":
            continue
        if platform.python_version()[0] == "3":
            logger.debug("Correct version of Python detected to run this script")
        else:
            logger.error("Incorrect Python version detected. Python 3 version is required to execute this script")
            sys.exit(0)
        logger.info("Executing script to return network device property values into CSV file format for iDRAC %s" % idrac_address)
        get_remote_services(idrac_address)
        if get_remote_service_failure == "yes":
           continue
        if get_network_device_fqdd_flag.lower() == "yes":
            get_network_device_fqdds(idrac_address)
            continue
        get_network_device_properties(idrac_address)
        if get_command_failure == "yes" or print_properties_only == "yes":
            continue
        else:
            if write_headers_csv_file == True:
                create_write_headers_csv_file()
            write_csv_file(idrac_address)
    logger.info("Script complete, script logs also captured in \"network_device_script_logfile.txt\" file")

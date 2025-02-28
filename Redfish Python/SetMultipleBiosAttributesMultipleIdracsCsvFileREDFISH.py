#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2025, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
#
# Edited CSV file example:
#
#iDRAC IP	iDRAC Username	iDRAC Password	IscsiDev1Con2EnDis  IscsiDev1Con2Ip	IscsiDev1Con2Mask   IscsiDev1Con2Gateway
#10.10.1.10	root	        calvin	        Enabled	            192.168.0.150	255.255.255.0	    192.168.0.1
#11.11.1.11	root	        calvin	        Enabled	            192.168.0.130	255.255.255.0	    192.168.0.1
#
# Note: The first 3 columns do not change the name, they need to be iDRAC IP, iDRAC Username and iDRAC Password.
# For the other columns pass in attribute names you want to configure. In the CSV file example i pass in these BIOS attributes
# to set but you can pass in as many BIOS attributes as you want in the CSV file,
# just make sure the value you want to apply is listed under that attribute.
#
# Script pseudo code workflow:
#
# 1. Read the CSV file and get attribute names and values or each iDRAC listed.
# 2. Create a BIOS config job to set attributes, confirm job is scheduled and reboot the server.
# 3. Script will repeat step 2 for each iDRAC until all iDRACs have jobs created (this is done so all jobs can run in parallel on all iDRACs).
# 4. Loop each job until marked completed for all iDRACs.



import argparse
import csv
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

parser = argparse.ArgumentParser(description="Python script using Redfish API to set multiple BIOS attributes for multiple iDRACs using a CSV file.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--csv-filename', help='Pass in CSV filename', dest="csv_filename", required=False)
parser.add_argument('-ip',help='iDRAC IP address, this is only supported to get BIOS attributes for one iDRAC.', required=False)
parser.add_argument('-u', help='iDRAC username, this is only supported to get BIOS attributes for one iDRAC.', required=False)
parser.add_argument('-p', help='iDRAC password, this is only supported to get BIOS attributes for one iDRAC.', required=False)
parser.add_argument('--get', help='Get all BIOS attributes', action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- python SetMultipleBiosAttributesMultipleIdracsCsvFileREDFISH.py --csv-filename idrac_details.csv, this example will configure multiple attributes for multiple iDRACs using CSV file.
    \n- python SetMultipleBiosAttributesMultipleIdracsCsvFileREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return BIOS attributes for one iDRAC.""")
    return

def get_bios_attributes():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Attributes' % args["ip"], verify=verify_cert,auth=(args["u"], args["p"]))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    pprint(data)


def set_bios_attributes():
    global job_id
    global idrac_ip
    global idrac_username
    global idrac_password
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"},"Attributes":{}}
    for i in attribute_dict.items():
        if "idrac ip" in i[0].lower():
            idrac_ip = i[1]
        elif "idrac username" in i[0].lower():
            idrac_username = i[1]
        elif "idrac password" in i[0].lower():
            idrac_password = i[1]
        else:
            payload["Attributes"][i[0]] = i[1]
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.debug("\n- PASS: PATCH command passed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
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
    logging.info("- PASS, BIOS config job ID %s successfully created for iDRAC %s" % (job_id, idrac_ip))

def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
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
            return
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, job ID %s successfully marked as scheduled for iDRAC %s" % (job_id, idrac_ip))
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

def reboot_server():
    response = requests.get("https://%s/redfish/v1/Systems/System.Embedded.1" % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, Current server power state: %s" % data["PowerState"])
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" % idrac_ip
    headers = {"content-type": "application/json"}
    if data["PowerState"] == "On":
        payload = {"ResetType": "ForceRestart"}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to reboot the server for iDRAC %s" % idrac_ip)
        else:
            logging.error("\n- FAIL, POST command failed to reboot the server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)    
    elif data["PowerState"] == "Off":
        payload = {"ResetType": "On"}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to power ON server for iDRAC %s" % idrac_ip)
        else:
            logging.error("\n- FAIL, POST command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(0)
    

def loop_job_status_final(idrac_ip, idrac_username, idrac_password, job_id):
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            if "powercyclerequest" in args["attribute_names"].lower():
                logging.info("- INFO, PowerCycleRequest attribute detected, virtual a/c cycle is running. Script will sleep for 180 seconds, retry")
                time.sleep(180)
            else:
                time.sleep(60)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            logging.info("\n- PASS, Job %s successfully marked completed for iDRAC %s" % (job_id, idrac_ip))
            break
        else:
            logging.info("- INFO, job %s not completed for iDRAC %s, current status: \"%s\"" % (job_id, idrac_ip, data['Message'].rstrip(".")))
            time.sleep(10)


            
if __name__ == "__main__":
    verify_cert = False
    if args["script_examples"]:
        script_examples()
    elif args["get"]:
        get_bios_attributes()
    elif args["csv_filename"]:
        file_path = args["csv_filename"]
        count = 1
        idrac_config_jobs = {}
        # Get contents from CSV file 
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            idrac_dict = {}
            for line_number, line_data in enumerate(csv_reader, start=1):
                try:
                    if "idrac ip" in line_data[0].lower():
                        csv_row_names = line_data
                        csv_row_names[0] = "iDRAC IP"
                        continue
                    else:
                        idrac_details_attribute_values = line_data
                except:
                    break
                attribute_dict = {}
                for i,ii in zip(csv_row_names, idrac_details_attribute_values):
                    attribute_dict[i] = ii
                idrac_name ="idrac%s" % count
                idrac_dict[idrac_name]= {"iDRAC IP": attribute_dict["iDRAC IP"], "iDRAC Username": attribute_dict["iDRAC Username"], "iDRAC Password": attribute_dict["iDRAC Password"], "Job ID" : ""}
                set_bios_attributes()
                idrac_dict[idrac_name]["Job ID"] = job_id
                get_job_status_scheduled()
                reboot_server()
                count += 1
            logging.info("- INFO, script will now loop polling the job ID status for each iDRAC until the job is marked completed")
            for i in idrac_dict.items():
                idrac_ip = i[1]["iDRAC IP"]
                loop_job_status_final(i[1]["iDRAC IP"], i[1]["iDRAC Username"], i[1]["iDRAC Password"], i[1]["Job ID"])     
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

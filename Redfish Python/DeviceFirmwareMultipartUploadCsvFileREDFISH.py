#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2024, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Edited CSV file example (make sure to name your column headers the same as listed in this example):
#
# iDRAC IP	        iDRAC Username	iDRAC Password  
# 192.168.0.120	        root            calvin		
# 192.168.0.130	        root            calvin  

import argparse
import csv
import getpass
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

parser = argparse.ArgumentParser(description="Python script using Redfish API to install the same firmware package to multiple iDRACs using CSV file.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get', help='Get current supported devices for firmware updates and their current firmware versions', action="store_true", required=False)
parser.add_argument('--location', help='Pass in the full directory path location of the firmware image. Make sure to also pass in the name of the Dell Update package (DUP) executable, example: C:\\Users\\admin\\Downloads\\Diagnostics_Application_CH7FG_WN64_4301A42_4301.43.EXE', required=False)
parser.add_argument('--csv-filename', help='Pass in directory path and name of csv file which contains details for all iDRACs, see script comments for CSV content example', dest="csv_filename", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DeviceFirmwareMultipartUploadCsvFileREDFISH.py -ip 192.168.0.120 -u root --location C:\\Users\\administrator\\Downloads\\BIOS_8MRPC_C6420_WN64_2.11.2.EXE --csv-filename C:\\Users\\administrator\\Downloads\\idrac_details.csv, this example will update BIOS firmware for all iDRACs listed in the CSV file.""")
    sys.exit(0)
    
def download_image_create_update_job(idrac_ip, idrac_username, idrac_password, idrac_count):
    global start_time
    start_time = datetime.now()
    logging.info("- INFO, extracting payload from update package for iDRAC %s to create update job" % idrac_ip)
    url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
    payload = {"Targets": [], "@Redfish.OperationApplyTime": "Immediate", "Oem": {}}
    files = {
         'UpdateParameters': (None, json.dumps(payload), 'application/json'),
         'UpdateFile': (os.path.basename(args["location"]), open(args["location"], 'rb'), 'application/octet-stream')
    }
    response = requests.post(url, files=files, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        data = response.json()
        logging.error("- FAIL, status code %s returned, detailed error: %s" % (response.status_code,data))
        return
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in header for iDRAC %s" % idrac_ip)
        return
    logging.info("- PASS, update job ID %s successfully created for iDRAC %s" % (job_id, idrac_ip))
    idrac_details_dict["idrac%s" % str(idrac_count)].append(job_id)

def loop_check_final_job_status(idrac_ip, idrac_username, idrac_password, job_id):
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        check_idrac_connection(idrac_ip)
        try:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            time.sleep(10)
            retry_count += 1
            continue 
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, script stopped\n")
            return
        elif "fail" in data['Message'].lower() or "fail" in data['JobState'].lower():
            logging.error("\n- FAIL: job ID %s failed" % job_id)
            return
        elif "completed successfully" in data['Message']:
            logging.info("- PASS, job ID %s successfully marked completed for iDRAC %s" % (job_id, idrac_ip))
            return
        else:
            logging.info("- INFO, %s not marked completed, current status: \"%s\"" % (job_id, data['Message'].rstrip(".")))
            time.sleep(5)

def check_idrac_connection(idrac_ip):
    run_network_connection_function = ""
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        logging.error("- FAIL, unable to determine OS type, check iDRAC connection function will not execute")
        run_network_connection_function = "fail"
    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
    if execute_command != 0:
        ping_status = "lost"
    else:
        ping_status = "good"
        pass
    if ping_status == "lost":
            logging.info("- INFO, iDRAC network connection lost due to slow network response, waiting 30 seconds to access iDRAC again")
            time.sleep(30)
            while True:
                if run_network_connection_function == "fail":
                    break
                execute_command=subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
                if execute_command != 0:
                    ping_status = "lost"
                else:
                    ping_status = "good"
                if ping_status == "lost":
                    logging.info("- INFO, unable to ping iDRAC IP, script will wait 30 seconds and try again")
                    time.sleep(30)
                    continue
                else:
                    break
            while True:
                try:
                    response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
                except requests.ConnectionError as error_message:
                    logging.info("- INFO, GET request failed due to connection error, retry")
                    time.sleep(10)
                    continue
                break

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    elif args["location"] and args["csv_filename"]:
        idrac_details_dict = {}
        file_path = args["csv_filename"]
        count = 1
        # Get contents from CSV file 
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if "iDRAC IP" in row[0]:
                    continue
                else:
                    idrac_dict_name = "idrac%s" % count
                    idrac_details_dict[idrac_dict_name]= row
                    count += 1
        idrac_count = 1
        for i in idrac_details_dict.items():
            download_image_create_update_job(i[1][0], i[1][1], i[1][2], idrac_count)
            idrac_count += 1
        logging.info("- INFO, script will now loop polling job ID created for each iDRAC")
        for i in idrac_details_dict.items():
            loop_check_final_job_status(i[1][0], i[1][1], i[1][2], i[1][3])
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

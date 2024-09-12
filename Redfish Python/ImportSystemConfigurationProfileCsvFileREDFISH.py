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
# Edited CSV file example (make sure to name your column headers the same as listed in this example:
#
# iDRAC IP	        iDRAC Username	iDRAC Password
# 192.168.0.120	        root		calvin1		
# 192.168.0.130	        root            calvin2
#
# Script pseudo code workflow:
#
# 1. Import SCP job will get created for each iDRAC detected in CSV file
# 2. Once SCP import jobs are created for all iDRACs script will then loop polling the job status for the first iDRAC import job created.  
# 3. If BIOS, storage or network changes are detected in the SCP file, server will now reboot to apply those changes. 
# 4. Once that job ID is marked completed script will loop checking the next job ID created and continue running this part of the code until all job IDs have been validated.
# 5. Final SCP import job results will also report all the configuration changes applied to each iDRAC.
#

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

parser = argparse.ArgumentParser(description="Python script using Redfish API to apply same configuration changes using Server Configuration Profile (SCP) feature to multiple iDRACs using CSV file. See script comments for CSV file content example along with pseudo workflow details.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--target', help='Pass in target value to either export or import component attributes. You can pass in \"ALL" to set all component attributes or pass in a specific component to set only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=False)
parser.add_argument('--shutdown-type', help='Pass in server shutdown type value. Supported values are Graceful and Forced. If you don\'t use this optional argument default value is Graceful.', dest="shutdown_type", required=False)
parser.add_argument('--scp-filename', help='Pass in Server Configuration Profile filename for import', dest="scp_filename", required=False)
parser.add_argument('--csv-filename', help='Pass in CSV filename which contains iDRAC username, password and network details', dest="csv_filename", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ImportSystemConfigurationProfileCsvFileREDFISH.py --target ALL --scp-filename 2024-1-3_144317_export.xml --csv-filename iDRAC_details.csv, this example will first read the CSV file to get iDRAC IP/credentials and then apply SCP file config changes for all iDRACs.""")
    sys.exit(0)

def check_supported_idrac_version(idrac_ip, idrac_username, idrac_password):
    global failure
    failure = "no"
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=False, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        failure = "yes"
        return

def get_server_generation():
    global idrac_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if "12" in data["Model"] or "13" in data["Model"]:
        idrac_version = 8
    elif "14" in data["Model"] or "15" in data["Model"] or "16" in data["Model"]:
        idrac_version = 9
    else:
        idrac_version = 10

def import_SCP_local_filename(idrac_ip, idrac_username, idrac_password):
    global job_id
    global failure
    failure = "no"
    try:
        open_file = open(args["scp_filename"],"r")
    except:
        logging.error("\n- FAIL, \"%s\" file doesn't exist" % args["scp_filename"])
        sys.exit(0)   
    if idrac_version >= 10:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/OemManager.ImportSystemConfiguration' % idrac_ip
    else:    
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    # Code needed to modify the SCP file to one string to pass in for POST command
    modify_file = open_file.read()
    modify_file = re.sub(" \n ","",modify_file)
    modify_file = re.sub(" \n","",modify_file)
    file_string = re.sub("   ","",modify_file)
    open_file.close()
    payload = {"ImportBuffer":"","ShareParameters":{"Target":args["target"]}}
    if args["shutdown_type"]:
        payload["ShutdownType"] = args["shutdown_type"].title()
    payload["ImportBuffer"] = file_string
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))
    if response.status_code != 202:
        logging.error("\n- FAIL, POST command failed for import system configuration, status code %s returned" % response.status_code)
        logging.error(response.json())
        failure = "yes"   
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        failure = "yes"
    logging.info("\n- PASS, ImportSystemConfiguration job ID %s successfully created for iDRAC %s" % (job_id, idrac_ip))
    time.sleep(1)

def loop_job_id(idrac_ip, idrac_username, idrac_password, job_id):
    logging.info("\n- INFO, loop checking iDRAC %s job ID %s until marked completed" % (idrac_ip, job_id))
    start_job_message = ""
    start_time = datetime.now()
    count = 1
    get_job_status_count = 1
    new_password_set = "no"
    while True:
        if count == 10:
            logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
            return 
        if get_job_status_count == 10:
            logging.warning("- WARNING, retry count of 10 has been hit for retry job status GET request, script will exit")
            return
        try:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.warning("- WARNING, requests command failed to GET job status, detailed error information: \n%s" % error_message)
            logging.info("- INFO, script will attempt to get job status again")
            time.sleep(10)
            count += 1
            continue
        data = response.json()
        try:
            current_job_message = data['Oem']['Dell']['Message']
        except:
            logging.info("- INFO, unable to get job ID message string from JSON output, retry")
            count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code == 202 or response.status_code == 200:
            time.sleep(1)
        else:
            logging.info("- INFO, GET command failed to get job ID details, error code: %s, retry" % response.status_code)
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
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
            return
        elif data['Oem']['Dell']['JobState'] == "Completed":
            if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                logging.error("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
            elif "success" in data['Oem']['Dell']['Message'].lower():
                logging.info("- PASS, job ID %s successfully marked completed\n" % job_id)
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- PASS, job ID %s marked completed\n" % job_id)
                logging.info("- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    pprint(i)
                return
            logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    pprint(i)
            return
        else:
            if start_job_message != current_job_message:
                logging.info("- INFO, \"%s\", percent complete: %s" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                start_job_message = current_job_message
                time.sleep(1)
                continue
            
if __name__ == "__main__":
    if __name__ == "__main__":
        if args["script_examples"]:
            script_examples()
            sys.exit(0)
        if args["csv_filename"]:
            get_server_generation()
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
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["scp_filename"] and args["csv_filename"] and args["target"]:
        for i in idrac_details_dict.items():
            check_supported_idrac_version(i[1][0], i[1][1], i[1][2])
            if failure == "yes":
                logging.error("- WARNING, failure detected to check supported iDRAC version for iDRAC %s, script will skip SCP import for this iDRAC" % i[1][0])
                idrac_details_dict[i[0]].append("fail")
                continue
            import_SCP_local_filename(i[1][0], i[1][1], i[1][2])
            if failure == "yes":
                logging.error("- WARNING, failure detected to run SCP import action for iDRAC %s, script will skip SCP import for this iDRAC" % i[1][0])
                idrac_details_dict[i[0]].append("fail")
                continue
            idrac_details_dict[i[0]].append(job_id)
        for i in idrac_details_dict.items():
            if i[1][3] == "fail":
                continue
            loop_job_id(i[1][0], i[1][1], i[1][2], i[1][3])
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

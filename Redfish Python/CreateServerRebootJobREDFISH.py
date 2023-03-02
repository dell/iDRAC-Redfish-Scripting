#!/usr/bin/python3
#
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to create server reboot job which the job can run now or at a future scheduled time.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current reboot jobs from iDRAC job queue', action="store_true", required=False)
parser.add_argument('--reboot-job-type', help='Pass in reboot job type, either 1 for PowerCycle, 2 for GracefulRebootWithForcedShutdown or 3 for GracefulRebootWithoutForcedShutdown. Note: If 2 is selected, forced shutdown will occur if the graceful shutdown is unable to complete after 10 minutes.', dest="reboot_job_type", required=False)
parser.add_argument('--start-time', help='Start time to run the reboot job. Pass in TIME_NOW to run the reboot job immediately. To schedule the reboot job for a future time pass in the value in this format: YYYYMMDDHHMMSS, example: 20231010123000', dest="start_time", required=False)
parser.add_argument('--delete', help='Delete reboot job ID, pass in job ID', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- CreateServerRebootJobREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current reboot job ID(s) from iDRAC job queue.
    \n- CreateServerRebootJobREDFISH.py -ip 192.168.0.120 -u root -p calvin --reboot-job-type 1 --start-time TIME_NOW, this example shows creating a powercycle reboot job ID and execute it now to reboot the server.
    \n- CreateServerRebootJobREDFISH.py -ip 192.168.0.120 -u root -p calvin --reboot-job-type 2 --start-time 20231010120000, this example shows creating a graceful reboot with forced shutdown job ID which will run at a future time.
    \n- CreateServerRebootJobREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete RID_771072800201, this example shows deleting reboot job ID.""")
    sys.exit(0)

def check_supported_idrac_version():
    # Validate if iDRAC version is supported and successful communication to the iDRAC.
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_reboot_jobs():
    # Get current reboot job IDs in the iDRAC job queue
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if data["Members"] == []:
        logging.warning("\n- WARNING, no reboot IDs detected in the job queue")
        sys.exit(0)
    reboot_job_detected = "no"
    print("\n")
    for i in data["Members"]:
        for ii in i.items():
            if "RID" in ii[1]:
                reboot_job_detected = "yes"
                if args["x"]:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
                pprint(response.json())
                print("\n")
    if reboot_job_detected == "no":
        logging.warning("\n- WARNING, no reboot IDs detected in the job queue")
        sys.exit(0)     

def delete_jobID():
    # Delete reboot job ID
    url = "https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % idrac_ip
    payload = {"JobID":args["delete"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS: DeleteJobQueue action passed to clear reboot job ID \"%s\", status code 200 returned" % args["delete"])     
    else:
        logging.error("\n- FAIL, DeleteJobQueue action failed, status code %s returned" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)

def create_reboot_jobID():
    # Create reboot job ID
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellJobService/Actions/DellJobService.CreateRebootJob" % idrac_ip
    if args["reboot_job_type"] == "1":
        payload = {"RebootJobType":"PowerCycle"}
    elif args["reboot_job_type"] == "2":
        payload = {"RebootJobType":"GracefulRebootWithForcedShutdown"}
    elif args["reboot_job_type"] == "3":
        payload = {"RebootJobType":"GracefulRebootWithoutForcedShutdown"}
    else:
        logging.error("- WARNING, invalid argument value passed in for --reboot-job-type")
        sys.exit(0)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.debug("\n- PASS: POST command passed to create reboot job ID")  
    else:
        logging.error("\n- FAIL, CreateRebootJob action failed, status code %s returned" % (response.status_code))
        data = response.json()
        sys.exit(0)
        logging.error("\n- POST command failure:\n %s" % data)
    try:
        reboot_job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    # Schedule the reboot job ID
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellJobService/Actions/DellJobService.SetupJobQueue" % idrac_ip
    payload = {"JobArray":[reboot_job_id], "StartTimeInterval":args["start_time"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed to create and schedule reboot job ID \"%s\"" % reboot_job_id)  
    else:
        logging.error("\n- FAIL, SetupJobQueue action failed, status code %s returned" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip=args["ip"]
        idrac_username=args["u"]
        if args["p"]:
            idrac_password=args["p"]
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
        get_reboot_jobs()
    elif args["delete"]:
        delete_jobID()
    elif args["reboot_job_type"] and args["start_time"]:
        create_reboot_jobID()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

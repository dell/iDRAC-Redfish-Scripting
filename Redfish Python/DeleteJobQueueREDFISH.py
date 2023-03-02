#!/usr/bin/python3
#
# DeleteJobQueueREDFISH.py  Python script using Redfish API with OEM extension to get either delete single job ID, delete complete job queue or delete job queue and restart Lifecycle Controller services.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
#
# Copyright (c) 2020, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get either delete single job ID, delete complete job queue or delete job queue and restart Lifecycle Controller services.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--single-job', help='Delete single job id, pass in the job ID', dest="single_job", required=False)
parser.add_argument('--clear', help='Clear the job queue to delete all job IDs.', action="store_true", required=False)
parser.add_argument('--clear-restart', help='Clear the job queue and restart iDRAC Lifecycle Controller services. By selecting this option, it will take a few minutes for the Lifecycle Controller to be back in Ready state. Note: Use this option as a last resort for debugging iDRAC failures or to delete a job stuck in running state. If iDRAC still does not recover after running this operation, reboot iDRAC.', dest="clear_restart", action="store_true", required=False)
parser.add_argument('--get', help='Get current job ids in the job queue', action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current job queue.
    \n- DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin --single-job JID_852366388723, this example will delete a specific job ID.
    \n- DeleteJobQueueREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651aac --clear, this example using iDRAC x-auth token session will delete the job queue.""")
    sys.exit(0)

def check_supported_idrac_version():
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

def get_job_queue_job_ids():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if data["Members"] == []:
        logging.warning("\n- WARNING, no job IDs or reboot IDs detected in the job queue")
        sys.exit(0)
    logging.info("\n- INFO, current job IDs in the job queue for iDRAC %s:\n" % idrac_ip)
    time.sleep(2)
    for i in data["Members"]:
        pprint(i)
        print("\n")

def delete_jobID():
    url = "https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % idrac_ip
    if args["single_job"]:
        payload = {"JobID":args["single_job"]}
    elif args["clear"]:
        payload = {"JobID":"JID_CLEARALL"}
    elif args["clear_restart"]:
        payload = {"JobID":"JID_CLEARALL_FORCE"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        if args["single_job"]:
            logging.info("\n- PASS: DeleteJobQueue action passed to clear job ID \"%s\", status code 200 returned" % args["single_job"])
        elif args["clear"]:
            logging.info("\n- PASS: DeleteJobQueue action passed to clear the job queue, status code 200 returned")
        elif args["clear_restart"]:
            logging.info("\n- PASS: DeleteJobQueue action passed to clear the job queue and restart Lifecycle Controller services, status code 200 returned")
            time.sleep(10)         
    else:
        logging.error("\n- FAIL, DeleteJobQueue action failed, status code is %s" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    if args["clear_restart"]:
        logging.info("\n- INFO, Lifecycle Controller services restarted. Script will loop checking the status of Lifecycle Controller until Ready state")
        time.sleep(60)
        while True:
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
            method = "GetRemoteServicesAPIStatus"
            payload={}
            if args["x"]:
                headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
            data=response.json()
            if response.status_code != 200:
                logging.error("\n- FAIL, POST command failed for %s method, status code %s returned." % (method, response.status_code))
                data = response.json()
                logging.error("\n- POST command failure results:\n %s" % data)
                sys.exit(0)
            lc_status = data["LCStatus"]
            server_status = data["Status"]
            if lc_status == "Ready" and server_status == "Ready":
                logging.info("\n- PASS, Lifecycle Controller services are in ready state")
                sys.exit(0)
            else:
                print("- INFO, Lifecycle Controller services not in ready state, polling again")
                time.sleep(20)
    
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
    if args["single_job"] or args["clear"] or args["clear_restart"]:
        delete_jobID()
    elif args["get"]:
        get_job_queue_job_ids()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

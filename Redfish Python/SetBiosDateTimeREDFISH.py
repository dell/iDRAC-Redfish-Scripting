#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2026, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import configparser
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to set BIOS date and time. Latest platform BIOS version along with supported iDRAC version is required to support this feature. Note iDRAC introduced feature support starting in iDRAC9 7.20.80.50 and iDRAC10 1.30.10.50.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-idrac-time', help='Get current iDRAC time. Note iDRAC time syncs with BIOS time, currently there is no iDRAC support to get BIOS time directly so this method must be used as a workaround.', action="store_true", dest="get_idrac_time", required=False)
parser.add_argument('--set-bios-datetime', help='Set BIOS date and time, pass in the string value in this format: YYYY-MM-DDTHH:MM:SS+-HH:MM', dest="set_bios_datetime", required=False)
parser.add_argument('--dst', help='Specifies whether Daylight Saving Time (DST) is enabled or not, pass in a value of True or False', dest="dst", required=False)
parser.add_argument('--reboot', help='Pass in argument to reboot the server now to execute config job. If argument is not passed in, next manual server reboot job will be execute.', action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO) 

def script_examples():
    print("""\n- SetBiosDateTimeREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-idrac-time, this example will return iDRAC current time which syncs with BIOS time.
    \n- SetBiosDateTimeREDFISH.py -ip 192.168.0.120 -u root -p calvin --set-bios-datetime 2026-01-13T15:10:00-05:00 --dst True --reboot, this example will reboot the server now to set BIOS date and time.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Actions' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios?$select=Actions' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    if "SetBiosTime" not in str(data):
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")    
    

def get_idrac_time():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=DateTime' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=DateTime' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    print("\n- Current iDRAC time: %s" % (data["DateTime"]))
    
def set_bios_date_time():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Oem/DellBios.SetBiosTime' % (idrac_ip)
    if args["reboot"]:
        payload = {"@Redfish.OperationApplyTime":"Immediate"}
    else:
        payload = {"@Redfish.OperationApplyTime":"OnReset"}  
    payload["BiosDateTime"] = args["set_bios_datetime"]
    if args["dst"].lower() == "false":
        payload["DaylightSavingsEnabled"] = False
    else:
        payload["DaylightSavingsEnabled"] = True
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: POST action passed to set BIOS date and time pending value, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, POST action failed to set BIOS date and time pending value, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, BIOS config job ID %s successfully created" % job_id)

def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
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
            logging.info("- PASS, config job successfully marked as scheduled")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])
    if not args["reboot"]:
        logging.info("- INFO, argument --reboot not detected, job ID is still scheduled and will run on next manual server reboot")
        sys.exit(0)
    else:
        logging.info("- INFO, server will now automatically reboot to run config job")
        

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
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
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "1:00:00":
            logging.error("\n- FAIL: Timeout of 1 hour has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            time.sleep(10)
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            logging.info("\n- INFO, job completed in %s" % str(current_time)[0:7])
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'])
            time.sleep(5)



if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    elif args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    if args["get_idrac_time"]:
        get_idrac_time()
    elif args["set_bios_datetime"] and args["dst"]:
        set_bios_date_time()
        get_job_status_scheduled()
        loop_job_status_final()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

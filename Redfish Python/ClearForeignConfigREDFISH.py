#!/usr/bin/python3
#
# ClearForeignConfigREDFISH. Python script using Redfish API with OEM extension to clear a storage controller foreign configuration
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 9.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to clear a storage controller foreign configuration")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('--ssl', help='Verify SSL certificate for all Redfish calls, pass in \"true\". This argument is optional, if you do not pass in this argument, all Redfish calls will ignore SSL cert checks.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID to execute all Redfish calls instead of passing in username/password', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', dest="get_controllers", action="store_true", required=False)
parser.add_argument('--get-disks', help='Get server storage controller disk FQDDs and their raid status only (check for foreign disks), pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disks", required=False)
parser.add_argument('--clear', help='Clear foreign configuration for storage controller, pass in the controller FQDD, Example \"RAID.Slot.6-1\"', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ClearForeignConfigREDFISH.py -ip 192.168.0.120 -u root --get-controllers, this example will first prompt to enter iDRAC user password, then return controller FQDDs detected. 
    \n- ClearForeignConfigREDFISH.py -ip 192.168.0.120 -x 82a57f88c4c7f339c1fb2ce105798aec --get-disks RAID.Mezzanine.1-1 --ssl true, this example using X-auth token session will return current drives and check if any foreign configs are detected for controller RAID.Mezzanine.1-1. All Redfish calls will also perform SSL cert verification.
    \n- ClearForeignConfigREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear RAID.Slot.6-1, this example will clear foreign configuration for RAID controller RAID.Slot.6-1.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_storage_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])
    
def get_pdisks_check_foreign_status():
    test_valid_controller_FQDD_string(args["get_disks"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET request failed to get disk information, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    drive_list = []
    if data['Drives'] == []:
        logging.warning("\n- WARNING, no drives detected for %s" % args["get_disks"])
        sys.exit(0)
    else:
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
    print("\n- Drives detected for controller \"%s\" and RaidStatus\n" % args["get_disks"])
    foreign_disks_detected = []
    for i in drive_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, GET request failed to get disk information, status code %s returned" % response.status_code)
            logging.error(data)
            sys.exit(0)
        logging.info(" - Disk %s, Raidstatus %s" % (i, data['Oem']['Dell']['DellPhysicalDisk']['RaidStatus']))
        if data['Oem']['Dell']['DellPhysicalDisk']['RaidStatus'] == "Foreign":
            foreign_disks_detected.append(i)
    if foreign_disks_detected != []:
        logging.info("\n- INFO, foreign configurations detected for controller %s" % args["get_disks"])
        sys.exit(0)
    else:
        logging.info("\n- INFO, no foreign configurations detected for controller %s" % args["get_disks"])
        sys.exit(0)
          
def clear_foreign_config():
    global job_id
    method = "ClearForeignConfig"
    test_valid_controller_FQDD_string(args["clear"])
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ClearForeignConfig' % (idrac_ip)
    payload={"TargetFQDD": args["clear"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed to clear foreign configuration for controller %s, status code %s returned" % (args["clear"], response.status_code))
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit(0)
        logging.info("- Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
    else:
        logging.error("\n- FAIL, POST command failed for controller %s, status code is %s" % (args["clear"], response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    
def test_valid_controller_FQDD_string(x):
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string value is case sensitive)")
        sys.exit(0)

def loop_job_status():
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % statusCode)
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
                if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'])
            time.sleep(3)

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
    if args["get_controllers"]:
        get_storage_controllers()
    elif args["clear"]:
        clear_foreign_config()
        loop_job_status()
    elif args["get_disks"]:
        get_pdisks_check_foreign_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)

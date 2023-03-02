#!/usr/bin/python3
#
# ChangeVirtualDiskAttributesREDFISH. Python script using Redfish API to either get controllers, get virtual disks or change virtual disk read, write or disk cache policy settings.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2022, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers, get virtual disks or change virtual disk read, write or disk cache policy settings")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--get-virtualdisk-details', help='Get complete details for all virtual disks behind storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisk_details", required=False)
parser.add_argument('--change', help='Pass in virtual disk FQDD to change cache policy settings.', required=False)
parser.add_argument('--diskcachepolicy', help='Pass in disk cache policy setting for VD creation, supported values: Enabled and Disabled. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--readcachepolicy', help='Pass in read cache policy setting for VD creation, supported values: Off, ReadAhead and AdaptiveReadAhead. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--writecachepolicy', help='Pass in write cache policy setting for VD creation, supported values: ProtectedWriteBack, UnprotectedWriteBack and WriteThrough. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--encrypted', help='Secure a Virtual Disk by encrypting it. Make sure a valid key has been set before trying to enable encryption. This is OPTIONAL, if you don\'t pass in this argument for VD change, nothing changes on encryption', action="store_true", dest="encrypted", required=False)
parser.add_argument('--job-type', help='Pass in job type to create. Pass in \"r\" to create realtime config job which gets applied immediately, no server reboot. Pass in \"l\" to schedule the config job which will get applied on next server manual reboot.', dest="job_type", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ChangeVirtualDiskAttributesREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651bbf --get-controllers, this example using iDRAC X-auth token session will return controller FQDDs.
    \n- ChangeVirtualDiskAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-virtualdisks RAID.Integrated.1-1, this example will return virtual disks for controller RAID.Integrated.1-1.
    \n- ChangeVirtualDiskAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --change Disk.Virtual.1:RAID.SL.3-1 --readcachepolicy Off --job-type r, this example shows creating a realtime config job to change VD read cache policy now.
    \n- ChangeVirtualDiskAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin --change Disk.Virtual.1:RAID.SL.3-1 --diskcachepolicy Enabled --writecachepolicy WriteThrough --job-type r, this example shows creating a realtime config job to change VD disk and write cache policies.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
        
def test_valid_controller_FQDD_string(x):
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string value is case sensitive)")
        sys.exit(0)

def get_storage_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Server controller(s) detected -\n")
    controller_list = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_virtual_disks():
    test_valid_controller_FQDD_string(args["get_virtualdisks"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        logging.warning("\n- WARNING, no volume(s) detected for %s" % args["get_virtualdisks"])
        sys.exit(0)
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    logging.info("\n- Volume(s) detected for %s controller -\n" % args["get_virtualdisks"])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))

def get_virtual_disks_details():
    test_valid_controller_FQDD_string(args["get_virtualdisk_details"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisk_details"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisk_details"]),verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list = []
    if data['Members'] == []:
        logging.error("\n- WARNING, no volume(s) detected for %s" % args["get_virtualdisk_details"])
        sys.exit(0)
    else:
        logging.info("\n- Volume(s) detected for %s controller -\n" % args["get_virtualdisk_details"])
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
            print(i['@odata.id'].split("/")[-1])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        logging.info("\n----- Detailed Volume information for %s -----\n" % ii)
        for i in data.items():
            pprint(i)
        print("\n")

def change_vd_attributes():
    global job_id
    global job_type
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get iDRAC firmware version.")
        sys.exit(0)
    data = response.json()
    if args["job_type"] == "r":
        payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
    elif args["job_type"] == "l":
        payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    else:
        logging.error("- FAIL, either missing argument --job-type or incorrect value passed in")
        sys.exit(0)
    if args["diskcachepolicy"]:
        payload["Oem"]={"Dell":{"DellVolume":{"DiskCachePolicy": args["diskcachepolicy"]}}}
    if args["readcachepolicy"]:
        payload["ReadCachePolicy"] = args["readcachepolicy"]
    if args["writecachepolicy"]:
        payload["WriteCachePolicy"] = args["writecachepolicy"]
    if args["encrypted"]:
        payload["Encrypted"] = True
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes/%s/Settings" % (idrac_ip, args["change"].split(":")[-1], args["change"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to change virtual disk\"%s\" settings, status code 202 returned" % args["change"])
    else:
        logging.error("\n- FAIL, PATCH command failed, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- PATCH command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, config job ID %s successfully created" % job_id)
    
def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(5)
            count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, config job ID marked as scheduled, job will execute on next server manual reboot")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s\n" % data['Message'].strip("."))

def loop_job_status_final():
    start_time = datetime.now()
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if data['JobType'] == "RAIDConfiguration":
        logging.info("- PASS, staged jid \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
    elif data['JobType'] == "RealTimeNoRebootConfiguration":
        logging.info("- PASS, realtime jid \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
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
        elif "fail" in data['Message'].lower() or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

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
    if args["get_controllers"]:
        get_storage_controllers()
    elif args["get_virtualdisks"]:
        get_virtual_disks()
    elif args["get_virtualdisk_details"]:
        get_virtual_disks_details()
    elif args["change"] and args["job_type"]:
        change_vd_attributes()
        if args["job_type"] == "r":
            loop_job_status_final()
        elif args["job_type"] == "l":
            get_job_status_scheduled()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

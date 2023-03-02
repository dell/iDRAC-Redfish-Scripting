#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2021, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to change the PD state of a disk part of a virtual disk, either set the disk to offline or bring back online. NOTE: Only RAID volumes which support parity are supported for this feature.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-disks', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disks", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--get-virtualdisk-details', help='Get complete details for all virtual disks behind storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisk_details", required=False)
parser.add_argument('--disk-fqdd', help='Convert drive to offline or online, pass in the disk FQDD, Example \"Disk Disk.Bay.4:Enclosure.Internal.0-1:RAID.Slot.6-1\"', dest="disk_fqdd", required=False)
parser.add_argument('--convert', help='Convert drive to offline, pass in value \"offline\". Convert drive to online, pass in value \"online\"', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-controllers, this example shows getting storage controller FQDDs.
    \n- ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-disks RAID.Mezzanine.1-1, this example will return all disks detected behind storage controller RAID.Mezzanine.1-1 and their current RAID status.
    \n- ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin --disk-fqdd Disk.Bay.10:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 --convert offline, this example shows setting disk in bay 10 to offline.
    \n- ChangePdStateREDFISH.py -ip 192.168.0.120 -x 983d154b4a125c7ae3838b8e32256a34 --disk-fqdd Disk.Bay.0:Enclosure.Internal.0-1:RAID.SL.3-1 --convert online, this example using X-auth token session will convert disk 0 to online.""")
    sys.exit(0)

def check_supported_idrac_version():
    supported = "no"
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version status code %s returned" % response.status_code)
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
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_pdisks():
    disk_used_created_vds=[]
    available_disks=[]
    test_valid_controller_FQDD_string(args["get_disks"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]),verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if data['Drives'] == []:
        logging.warning("\n- WARNING, no drives detected for %s" % args["get_disks"])
        sys.exit(0)
    else:
        logging.info("\n- Drive(s) detected for %s -\n" % args["get_disks"])
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
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

def change_pd_state():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ChangePDState' % (idrac_ip)
    payload={"State":"","TargetFQDD":args["disk_fqdd"]}
    if args["convert"].lower() == "offline":
        payload["State"] = "Offline"
    elif args["convert"].lower() == "online":
        payload["State"] = "Online"
    else:
        logging.error("- FAIL, invalid value passed in for argument --convert")
        sys.exit(0)   
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("- PASS, POST command passed for ChangePDState action")
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit(0)
        logging.info("- INFO, Job ID %s successfully created to change disk \"%s\" to \"%s\"" % (job_id, args["disk_fqdd"], args["convert"]))
    else:
        logging.error("\n- FAIL, POST command failed to change disk %s to %s, status code %s returned" % (args["disk_fqdd"], args["convert"], response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
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
    elif args["get_disks"]:
        get_pdisks()
    elif args["get_virtualdisks"]:
        get_virtual_disks()
    elif args["get_virtualdisk_details"]:
        get_virtual_disks_details()
    elif args["disk_fqdd"] and args["convert"]:
        change_pd_state()
        loop_job_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

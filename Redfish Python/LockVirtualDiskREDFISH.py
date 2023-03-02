#!/usr/bin/python3
#
# LockVirtualDiskREDFISH. Python script using Redfish API with OEM extension to lock a virtual disk.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
#
# Copyright (c) 2018, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to lock a virtual disk. Encryption or controller key must already be set on the controller and virtual disk created with SED(self encrypting drive) drives")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-disks', help='Get server storage controller disk FQDDs and their raid status, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disks", required=False)
parser.add_argument('--get-disk-encryption', help='Get drive encryption capability, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disk_encryption", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--get-virtualdisk-details', help='Get complete details for all virtual disks behind storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisk_details", required=False)
parser.add_argument('--check-locked-vds', help='Check for current locked virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="check_locked_vds", required=False)
parser.add_argument('--lock', help='Lock virtual disk, pass in the virtual disk FQDD, Example \"Disk.Virtual.0:RAID.Integrated.1-1\"', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-controllers, this example will return storage controller FQDDs.
    \n- LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-disk-encryption RAID.Mezzanine.1-1, this example will return encryption capcable status for each drive behind this storage controller.
    \n- LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-virtualdisks RAID.Integrated.1-1, this example will return virtual disks for this storage controller.
    \n- LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --check-locked-vds RAID.Mezzanine.1-1, this example will return current virtual disks detected and their lock status for controller RAID.Mezzanine.1-1.
    \n- LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --lock Disk.Virtual.0:RAID.Mezzanine.1-1, this example will lock VD 0 on controller RAID.Mezzanine.1-1""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
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

def get_pdisks():
    test_valid_controller_FQDD_string(args["get_disks"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disks"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, return code %s" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    drive_list = []
    if data['Drives'] == []:
        logging.warning("\n- WARNING, no drives detected for %s" % args["get_disks"])
        sys.exit(0)
    else:
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
    logging.info("\n- Drives detected for controller \"%s\" and RaidStatus\n" % args["get_disks"])
    for i in drive_list:
      if args["x"]:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
      else:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
      data = response.json()
      logging.info(" - Disk: %s, Raidstatus: %s" % (i, data['Oem']['Dell']['DellPhysicalDisk']['RaidStatus']))

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
                 
def check_drive_capabiity():
    test_valid_controller_FQDD_string(args["get_disk_encryption"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disk_encryption"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disk_encryption"]),verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list = []
    if data['Drives'] == []:
        logging.warning("\n- WARNING, no drives detected for %s" % args["get_disk_encryption"])
        sys.exit(0)
    else:
        for i in data['Drives']:
            for ii in i.items():
                disk = ii[1].split("/")[-1]
                drive_list.append(disk)
    logging.info("\n - INFO, Disk FQDD/encryption ability status for controller %s disk(s)\n" % args["get_disk_encryption"])
    for i in drive_list:
      if args["x"]:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
      else:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=verify_cert, auth=(idrac_username, idrac_password))
      data = response.json()
      for ii in data.items():
          if ii[0] == "EncryptionAbility":
              print("%s: EncryptionAbility: %s" % (i,ii[1]))
             
def check_lock_VDs():
    test_valid_controller_FQDD_string(args["check_locked_vds"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["check_locked_vds"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["check_locked_vds"]),verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list = []
    if data['Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["check_locked_vds"])
        sys.exit()
    else:
        for i in data['Members']:
            for ii in i.items():
                vd = ii[1].split("/")[-1]
                vd_list.append(vd)
    logging.info("\n- Volume(s) detected for %s controller -\n" % args["check_locked_vds"])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "Encrypted":
                print("%s, Encrypted(Lock) Status: %s" % (ii, i[1]))
    sys.exit(0)

def lock_VD():
    global job_id
    method = "LockVirtualDisk"
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.LockVirtualDisk' % (idrac_ip)
    payload={"TargetFQDD": args["lock"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed to lock virtual disk \"%s\"" % args["lock"])
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit(0)
        logging.info("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
    else:
        logging.error("\n- FAIL, POST command failed to lock virtual disk \"%s\"" % args["lock"])
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
            logging.info("- INFO, job not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(3)
    
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
        get_virtual_disk_details()
    elif args["get_disks"]:
        get_pdisks()
    elif args["get_disk_encryption"]:
        check_drive_capabiity()
    elif args["check_locked_vds"]:
        check_lock_VDs()
    elif args["lock"]:
        lock_VD()
        loop_job_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

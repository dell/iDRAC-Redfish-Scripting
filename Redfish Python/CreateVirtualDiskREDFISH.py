#!/usr/bin/python3
#
# CreateVirtualDiskREDFISH. Python script using Redfish API to either get controllers / disks / virtual disks / supported RAID levels or create virtual disk.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 22.0
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
import itertools
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / disks / virtual disks / supported RAID levels or create virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-disks', help='Get server storage controller disk FQDDs and their raid status, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disks", required=False)
parser.add_argument('--get-disk-details', help='Get detailed disk information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disk_details", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--get-virtualdisk-details', help='Get complete details for all virtual disks behind storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisk_details", required=False)
parser.add_argument('--supported-raid-levels', help='Get current supported volume types (RAID levels) for your controller, pass in controller FQDD', dest="supported_raid_levels", required=False)
parser.add_argument('--create', help='Pass in controller FQDD to create virtual disk, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('--disks', help='Pass in disk FQDD to create virtual disk, pass in storage disk FQDD, Example \"Disk.Bay.2:Enclosure.Internal.0-1:RAID.Mezzanine.1-1\". You can pass in multiple drives, just use a comma seperator between each disk FQDD string', required=False)
parser.add_argument('--raid-level', help='Pass in the RAID level you want to create. Possible supported values are: 0, 1, 5, 6, 10, 50 and 60. NOTE: Depending on your storage controller, not all RAID levels will be supported.', required=False)
parser.add_argument('--size', help='Pass in the size(CapacityBytes) in bytes for VD creation. This is OPTIONAL, if you don\'t pass in the size, VD creation will use full disk size to create the VD', required=False)
parser.add_argument('--stripesize', help='Pass in the stripesize(OptimumIOSizeBytes) in bytes for VD creation. This is OPTIONAL, if you don\'t pass in stripesize, controller will use the default value', required=False)
parser.add_argument('--name', help='Pass in the name for VD creation. This is OPTIONAL, if you don\'t pass in name, controller will use the default value', required=False)
parser.add_argument('--diskcachepolicy', help='Pass in disk cache policy setting for VD creation, supported values: Enabled and Disabled. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--readcachepolicy', help='Pass in read cache policy setting for VD creation, supported values: Off, ReadAhead and AdaptiveReadAhead. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--writecachepolicy', help='Pass in write cache policy setting for VD creation, supported values: ProtectedWriteBack, UnprotectedWriteBack and WriteThrough. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value', required=False)
parser.add_argument('--secure', help='Secure virtual disk for VD creation. Note: Make sure your controller already has encryption enabled and using encryption capable drives.', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-disks RAID.Mezzanine.1-1, this example return return disks and their raid status for controller RAID.Mezzanine.1-1.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651bbf --get-controllers, this example using iDRAC X-auth token session will return controller FQDDs.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --supported-raid-levels RAID.Integrated.1-1, this example will return supported RAID levels for controller RAID.Integrated.1-1.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root --create RAID.Mezzanine.1-1 --raid-level 0 --disks Disk.Bay.1:Enclosure.Internal.0-1:RAID.Mezzanine.1-1, this example will first prompt to enter iDRAC user password, then create one disk RAID 0.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --create RAID.Mezzanine.1-1 --raid-level 0 --disks  Disk.Bay.1:Enclosure.Internal.0-1:RAID.Mezzanine.1-1,Disk.Bay.7:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 --name RAID_1_OS, this example will create RAID 1 with VD name RAID_1_OS.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --create RAID.Mezzanine.1-1 --raid-level 0 --disks  Disk.Bay.1:Enclosure.Internal.0-1:RAID.Mezzanine.1-1,Disk.Bay.7:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 --name RAID_1_OS --size 107374182400 --stripesize 131072, this example will create 100GB size, 128KB stripesize RAID 1 virtual disk.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --create RAID.SL.3-1 --raid-level 1 --disks Disk.Bay.2:Enclosure.Internal.0-1:RAID.SL.3-1,Disk.Bay.3:Enclosure.Internal.0-1:RAID.SL.3-1 --diskcachepolicy Disabled --readcachepolicy Off --writecachepolicy UnprotectedWriteBack, this example shows creating a RAID 1 volume setting disk, read and write cache policies.
    \n- CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --create RAID.Mezzanine.1-1 --raid-level 0 --disks Disk.Bay.2:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 --secure, this example shows creating secured RAID 0 virtual disk.""")
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

def get_pdisk_details():
    test_valid_controller_FQDD_string(args["get_disk_details"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disk_details"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["get_disk_details"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, return code %s" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    drive_list = []
    if data['Drives'] == []:
        logging.warning("\n- WARNING, no drives detected for %s" % args["get_disk_details"])
        sys.exit(0)
    else:
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
    for i in drive_list:
        logging.info("\n- Detailed information for %s -\n" % i)
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        pprint(data), print("\n")

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

def get_supported_RAID_levels():
    non_supported = ""
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s?$select=StorageControllers' % (idrac_ip, args["supported_raid_levels"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Supported RAID levels for controller %s -\n" % args["supported_raid_levels"])
    print(data["StorageControllers"][0]["SupportedRAIDTypes"])    

def create_raid_vd():
    global job_id
    global job_type
    global current_vd_list
    current_vd_list = []
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["create"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["create"]),verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    data = response.json()
    for i in data["Members"]:
        for ii in i.items():
            current_vd_list.append(ii[1])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get iDRAC firmware version.")
        sys.exit(0)
    data = response.json()
    get_version = data['FirmwareVersion'].split(".")[:2]
    get_version = int("".join(get_version))
    if get_version < 440:
        raid_levels = {"0":"NonRedundant","1":"Mirrored","5":"StripedWithParity","10":"SpannedMirrors","50":"SpannedStripesWithParity"}
        try:
            volume_type = raid_levels[args["raid_level"]]  
        except:
            logging.error("\n- FAIL, invalid RAID level value entered")
            sys.exit(0)
    elif get_version >= 440:
        raid_levels = {"0":"RAID0","1":"RAID1","5":"RAID5","6":"RAID6","10":"RAID10","50":"RAID50","60":"RAID60"}
        try:
            volume_type = raid_levels[args["raid_level"]]  
        except:
            logging.error("\n- FAIL, invalid RAID level value entered")
            sys.exit(0)
    if args["size"]:
        vd_size = int(args["size"])
    if args["stripesize"]:
        vd_stripesize = int(args["stripesize"])
    if args["name"]:
        vd_name = args["name"]
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["create"])
    disks_list = args["disks"].split(",")
    final_disks_list = []
    for i in disks_list:
        disk_string = "/redfish/v1/Systems/System.Embedded.1/Storage/Drives/" + i
        create_disk_dict = {"@odata.id":disk_string}
        final_disks_list.append(create_disk_dict)
    if get_version < 440:
        payload = {"VolumeType":volume_type,"Drives":final_disks_list}
    elif get_version >= 440:
        payload = {"RAIDType":volume_type,"Drives":final_disks_list}
    if args["size"]:
        payload["CapacityBytes"] = int(args["size"])
    if args["stripesize"]:
        payload["OptimumIOSizeBytes"] = int(args["stripesize"])
    if args["name"]:
        payload["Name"] = vd_name
    if args["secure"]:
        payload["Encrypted"] = True
    if args["diskcachepolicy"]:
        payload["Oem"]={"Dell":{"DellVolume":{"DiskCachePolicy": args["diskcachepolicy"]}}}
    if args["readcachepolicy"]:
        payload["ReadCachePolicy"] = args["readcachepolicy"]
    if args["writecachepolicy"]:
        payload["WriteCachePolicy"] = args["writecachepolicy"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed to create \"%s\" virtual disk, status code 202 returned" % volume_type)
    else:
        logging.error("\n- FAIL, POST command failed, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure is:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    time.sleep(10)
    retry_count = 1
    while True:
        if retry_count == 5:
            logging.error("- WARNING, retry count of 5 has been hit to determine job type. Manually check the job queue for %s job status" % job_id)
            sys.exit(0)
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if "JobType" not in data.keys():
            logging.error("- WARNING, unable to determine job type, retry in 10 seconds")
            time.sleep(10)
            retry_count += 1
            continue
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
            logging.info("- PASS, staged job ID \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
            break
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
            logging.info("- PASS, realtime job ID \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
            break
    
def get_job_status_scheduled():
    retry_count = 0
    while True:
        if retry_count == 5:
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
            retry_count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, staged config job marked as scheduled, rebooting the system")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s\n" % data['Message'].strip("."))

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 0
    while True:
        if retry_count == 10:
            logging.error("- FAIL, GET job status retry count of 10 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.error("\n- WARNING, GET request failed to check job status, retry again")
            time.sleep(5)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
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
                pprint(i)
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["create"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["create"]),verify=verify_cert,auth=(idrac_username, idrac_password))
            if response.status_code != 200:
                logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
                logging.error("Extended Info Message: {0}".format(response.json()))
                sys.exit(0)
            new_vd_list = []
            data = response.json()
            for i in data["Members"]:
                for ii in i.items():
                    new_vd_list.append(ii[1])
            get_new_VD_fqdd = list(itertools.filterfalse(set(current_vd_list).__contains__, new_vd_list))
            logging.info("\n- INFO, new VD FQDD created: %s" % get_new_VD_fqdd[0].split("/")[-1])
            break
        else:
            logging.info("- INFO, job not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % response.status_code)
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        while True:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                if args["x"]:
                    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("- PASS, POST command passed to perform forced shutdown, status code return is %s" % response.status_code)
                    time.sleep(15)
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        logging.info("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        logging.error("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit(0)    
            else:
                continue 
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, Command passed to power ON server, status code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, Command passed to power ON server, code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(0)

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
    elif args["get_disks"]:
        get_pdisks()
    elif args["get_disk_details"]:
        get_pdisk_details()
    elif args["get_virtualdisks"]:
        get_virtual_disks()
    elif args["get_virtualdisk_details"]:
        get_virtual_disks_details()
    elif args["supported_raid_levels"]:
        get_supported_RAID_levels()
    elif args["create"] and args["disks"] and args["raid_level"]:
        create_raid_vd()
        if job_type == "realtime":
            loop_job_status_final()
        elif job_type == "staged":
            get_job_status_scheduled()
            reboot_server()
            loop_job_status_final()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

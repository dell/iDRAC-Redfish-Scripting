#!/usr/bin/python3
#
# GetRAIDLevelsREDFISH. Python script using Redfish API with OEM extension to get supported RAID levels for storage controller
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get supported RAID levels for storage controller based of parameters passed in for the POST command")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-disks', help='Get server storage controller disk FQDDs and their raid status, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_disks", required=False)
parser.add_argument('--target', help='Get supported RAID levels, pass in target controller FQDD, Example \"RAID.Slot.6-1\". Note: You must pass in --disktype and --diskprotocol also with --target which are the minimum required parameters needed to get RAID levels', required=False)
parser.add_argument('--disktype', help='DiskType, pass in 0 for \"IncludeAllTypes\", pass in 1 for \"IncludeHardDiskOnly\", pass in 2 for \"IncludeSolidStateOnly\"', required=False)
parser.add_argument('--diskprotocol', help='Diskprotocol, pass in 0 for \"AllProtocols\", pass in 1 for \"SAS\", pass in 2 for \"SATA\", pass in 3 for \"NVMe\"', required=False)
parser.add_argument('--formfactor', help='FormFactor, pass in 0 for \"IncludeAll\", pass in 1 for \"IncludeOnlyM.2\"', required=False)
parser.add_argument('--diskencrypt', help='DiskEncrypt, pass in 0 for \"IncludeFDECapableAndNonEncryptionCapableDisks\", pass in 1 for \"IncludeFDEDisksOnly\", pass in 2 for \"IncludeOnlyNonFDEDisks\"', required=False)
parser.add_argument('--blocksize', help='BlockSizeInBytes, pass in 0 for \"IncludeAllBlockSizeDisks\", pass in 1 for \"Include512BytesBlockSizeDisksOnly\", pass in 2 for \"Include4096BytesBlockSizeDisks\"', required=False)
parser.add_argument('--disk', help='PDArray, pass in disk FQDD string. If passing in multiple disks, use a comma separator', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetRAIDLevelsREDFISH.py -ip 192.168.0.120 -u root -p calvin --target RAID.Slot.6-1 --disktype 0 --diskprotocol 0, this example is going to return supported RAID levels for controller RAID.Slot.6-1 based off this disk criteria: all disk types and all disk protocols.
    \n- GetRAIDLevelsREDFISH.py -ip 192.168.0.120 -u root -p calvin --target RAID.Slot.6-1 --disktype 0 --diskprotocol 1 --blocksize 2, this example is going to return supported RAID levels for controller RAID.Slot.6-1 based off this disk criteria: all disk types, SAS disks only and 4096 block size only.
    \n- GetRAIDLevelsREDFISH.py -ip 192.168.0.120 -u root -p calvin --target RAID.Slot.6-1 --disktype 0 --diskprotocol 0 --disk Disk.Bay.0:Enclosure.Internal.0-1:RAID.Slot.6-1,Disk.Bay.1:Enclosure.Internal.0-1:RAID.Slot.6-1, this example is going to return supported RAID levels for controller RAID.Slot.6-1 based off this disk criteria: all disk types, all disk protocols and only using disk 0 and disk 1 """)
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
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
    
def get_supported_RAID_levels():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.GetRAIDLevels' % (idrac_ip)
    payload={"TargetFQDD":args["target"]}
    if args["disktype"]:
        if args["disktype"] == "0":
            payload["DiskType"] = "All"
        elif args["disktype"] == "1":
            payload["DiskType"] = "HDD"
        elif args["disktype"] == "2":
            payload["DiskType"] = "SSD"
        else:
            logging.warning("\n- WARNING, invalid value entered for --disktype argument")
            sys.exit(0)
    if args["diskprotocol"]:
        if args["diskprotocol"] == "0":
            payload["Diskprotocol"] = "AllProtocols"
        elif args["diskprotocol"] == "1":
            payload["Diskprotocol"] = "SAS"
        elif args["diskprotocol"] == "2":
            payload["Diskprotocol"] = "SATA"
        elif args["diskprotocol"] == "3":
            payload["Diskprotocol"] = "NVMe"
        else:
            logging.warning("\n- WARNING, invalid value entered for --diskprotocol argument")
            sys.exit(0)
    if args["formfactor"]:
        if args["formfactor"] == "0":
            payload["FormFactor"] = "All"
        elif args["formfactor"] == "1":
            payload["FormFactor"] = "M.2"
        else:
            logging.warning("\n- WARNING, invalid value entered for --formfactor argument")
            sys.exit(0)
    if args["diskencrypt"]:
        if args["diskencrypt"] == "0":
            payload["DiskEncrypt"] = "All"
        elif args["diskencrypt"] == "1":
            payload["DiskEncrypt"] = "FDE"
        elif args["diskencrypt"] == "2":
            payload["DiskEncrypt"] = "NonFDE"
        else:
            logging.warning("\n- WARNING, invalid value entered for --diskencrypt argument")
            sys.exit(0)
    if args["blocksize"]:
        if args["blocksize"] == "0":
            payload["BlockSizeInBytes"] = "All"
        elif args["blocksize"] == "1":
            payload["BlockSizeInBytes"] = "512"
        elif args["blocksize"] == "2":
            payload["BlockSizeInBytes"] = "4096"
        else:
            logging.warning("\n- WARNING, invalid value entered for --blocksize argument")
            sys.exit(0)
    if args["disk"]:
        if "," in args["disk"]:
            disk_list=args["disk"].split(",")
            payload["PDArray"] = disk_list
        else:
            payload["PDArray"] = [args["disk"]]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed to get RAID levels for controller %s" % args["target"])
    else:
        logging.error("\n- FAIL, POST command failed to get RAID levels for controller %s" % args["target"])
        data = response.json()
        logging.error("\n- POST command failure detailed results:\n %s" % data)
        sys.exit(0)
    if data['VDRAIDEnumArray'] == [] or data['VDRAIDEnumArray'] == None:
        logging.warning("- WARNING, no supported RAID levels detected based off disk argument values")
        sys.exit(0)
    logging.info("\n- RAID levels currently available to create based off available disks -\n")
    for i in data['VDRAIDEnumArray']:
        print(i)
        
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
    elif args["target"] and args["disktype"] and args["diskprotocol"]:
        get_supported_RAID_levels()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

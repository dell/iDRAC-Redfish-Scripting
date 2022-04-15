#!/usr/bin/python
#!/usr/bin/python3
#
# DellSlotCollectionREDFISH. Python script using Redfish API with OEM extension to get server slot information.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
import os
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API with OEM extension to get server slot information. This includes PSUs, Fans, DIMMs, CPUs, IDSDM, vFlash, PCIe, disks')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DellSlotCollectionREDFISH -ip 192.168.0.120 -u root -p calvin, this example will return server slot information.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_slot_collection():
    try:
        os.remove("slot_collection.txt")
    except:
        pass
    open_file = open("slot_collection.txt","a")
    get_timestamp = datetime.now()
    current_date_time = "- iDRAC IP %s, data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (idrac_ip, get_timestamp.month, get_timestamp.day, get_timestamp.year, get_timestamp.hour, get_timestamp.minute, get_timestamp.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Members']:
        pprint(i)
        print("\n")
        for ii in i.items():
            slot_collection_entry = ("%s: %s" % (ii[0],ii[1]))
            open_file.writelines("%s\n" % slot_collection_entry)
        open_file.writelines("\n")
    number_list=[i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if "Members" not in data or data["Members"] == [] or response.status_code == 400:
            break
        for i in data['Members']:
            for ii in i.items():
                slot_collection_entry = ("%s: %s" % (ii[0],ii[1]))
                pprint(i)
                print("\n")
                open_file.writelines("%s\n" % slot_collection_entry)
            open_file.writelines("\n")   
    logging.info("\n- INFO, slot collection information also captured in \"slot_collection.txt\" file")
    open_file.close()

    

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
    get_slot_collection()



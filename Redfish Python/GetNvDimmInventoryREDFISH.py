#!/usr/bin/python3
#
# GetNvDimmInventoryREDFISH. Python script using Redfish API DMTF to get server NVDIMM inventory.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
import os
import re
import requests
import sys
import time
import warnings

from pprint import pprint
from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API DMTF to get server NVDIMM Inventory')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetNvDimmInventoryREDFISH -ip 192.168.0.120 -u root -p calvin, this example will return NVDIMM information if NVDIMMs are detected on the server """)
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    
def get_NVDIMM_information():
    try:
        os.remove("NVDIMM_inventory.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step" % "NVDIMM_inventory.txt")
    open_file = open("NVDIMM_inventory.txt","a")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    nvdimm_uris = []
    for i in data['Members']:
        for ii in i.items():
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "NVDIMM" in data['MemoryType']:
                nvdimm_uris.append(ii[1])
    if nvdimm_uris == []:
        logging.warning("\n- WARNING, no NVDIMM(s) detected for iDRAC IP %s" % idrac_ip)
        sys.exit(0)
    else:
        logging.info("\n- INFO, NVDIMM URI(s) detected for iDRAC IP \"%s\"\n" % idrac_ip)
        time.sleep(1)
        for i in nvdimm_uris:
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            message = "\n- Detailed NVDIMM information for URI \"%s\" -\n" % i
            open_file.writelines("\n")
            open_file.writelines(message)
            print(message)
            for ii in data.items():
                pprint(ii)
                if ii[0] == 'Oem':
                    for iii in ii[1]['Dell']['DellMemory'].items():
                        if iii[0] != '@odata.context' or iii[0] != '@odata.type' or iii[0] != '@odata.id':
                            message = "%s: %s" % (iii[0], iii[1])
                            open_file.writelines("\n")
                            open_file.writelines(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    open_file.writelines("\n")
                    open_file.writelines(message)
    open_file.close()
    logging.info("\n- INFO, output also captured in \"NVDIMM_inventory.txt\" file")

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
    get_NVDIMM_information()

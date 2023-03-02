#!/usr/bin/python3
#
# DeleteFirmwarePackageREDFISH. Python script using Redfish API to delete a downloaded package which has not been applied yet.
# To delete the downloaded package, you must first find out the AVAILABLE URI entry for the download, then the Etag for this URI. You will need to pass in both the complete AVAILABLE URI and Etag
# to delete the downloaded payload.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
#
# Copyright (c) 2017, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to either get AVAILABLE entries for delete, get ETag for the AVAILABLE entry or DELETE the AVAILABLE downloaded package')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-available', help='Get AVAILABLE URI entries for delete', action="store_true", dest="get_available", required=False)
parser.add_argument('--get-etag', help='Get ETag id for AVAILABLE entry which is needed to delete, you must pass in the complete AVAILABLE URI string', dest="get_etag", required=False)
parser.add_argument('--uri', help='Pass in the complete AVAILABLE URI string', required=False)
parser.add_argument('--etag', help='Pass in the ETag for the AVAILABLE entry', required=False)
parser.add_argument('--delete-all', help='Automatically detect all AVAILABLE firmware entries and delete all', dest="delete_all", action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-available, this example will return any AVAILABLE downloaded URI entries which can be deleted.
    \n- DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-etag /redfish/v1/UpdateService/FirmwareInventory/Available-25806-4301X07, this example will return the Etag for the AVAILABLE URI entry.
    \n- DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin --uri /redfish/v1/UpdateService/FirmwareInventory/Available-25806-4301X07 --etag 4a2ae25594ccaa28535062b7b6d58df0, this example will delete the payload for the AVAILABLE package.
    \n- DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete-all, this example will delete all AVAILABLE URIs detected.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_available_entries():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get firmware inventory details")
        sys.exit(0)
    available_entries = []
    for i in data['Members']:
        for ii in i.items():
            if "Available" in ii[1]:
                available_entries.append(ii[1])
    if available_entries == []:
        logging.info("\n- No AVAILABLE entries for deleting payload")
    else:
        logging.info("\n- Available URI entries for deleting payload:\n")
        for i in available_entries:
            print(i)

def get_etag():
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_etag"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_etag"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get etag details for available URI.")
        sys.exit(0)
    try:
        ETag = response.headers['ETag']
    except:
        logging.error("- FAIL, unable to locate Etag in headers response")
        sys.exit(0)
    logging.info("\n- ETag for URI \"%s\": %s" % (args["get_etag"], ETag))

def delete_payload():
    url = 'https://%s%s' % (idrac_ip, args["uri"])
    if args["x"]:
        headers = {'X-Auth-Token': args["x"], "if-match": "\"%s\"" % args["etag"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {"if-match": "\"%s\"" % args["etag"]}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, Successfully deleted payload for URI %s" % args["uri"])
    else:
        logging.error("\n- FAIL, command failed to delete AVAILABLE URI %s, error: \n%s" % (args["uri"], data))
        sys.exit(0)
    
def delete_all_available_entries():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get firmware inventory details")
        sys.exit(0)
    available_entries = []
    for i in data['Members']:
        for ii in i.items():
            if "/available" in ii[1].lower():
                available_entries.append(ii[1])
    if available_entries == []:
        logging.warning("\n- WARNING, no AVAILABLE entries for deleting payload")
        sys.exit(0)
    else:
        logging.info("\n- INFO, available URI entries for deleting payload:\n")
        for i in available_entries:
            print(i)
    for i in available_entries:
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.error("- FAIL, GET command failed, error is %s" % data)
            sys.exit(0)
        ETag = response.headers['ETag']
        url = 'https://%s%s' % (idrac_ip, i)
        if args["x"]:
            headers = {'X-Auth-Token': args["x"], "if-match": ETag}
            response = requests.delete(url, headers=headers, verify=verify_cert)
        else:
            headers = {"if-match": ETag}
            response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200:
            logging.info("\n- PASS, Successfully deleted payload for URI %s" % i)
        else:
            logging.error("\n- FAIL, command failed to delete AVAILABLE URI %s, error: \n%s" % (i, data))
            sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    available_entries = []
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            if "/available" in ii[1].lower():
                available_entries.append(ii[1])
    if available_entries == []:
        logging.info("- PASS, all AVAILABLE firmware entries successfully deleted")
    else:
        logging.error("- FAIL, available firmware entries still detected. Entries are: %s" % available_entries)
        sys.exit(0)
    
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    if args["get_available"]:
        get_available_entries()
    elif args["get_etag"]:
        get_etag()
    elif args["etag"] and args["uri"]:
        delete_payload()
    elif args["delete_all"]:
        delete_all_available_entries()         
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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
import csv
import getpass
import json
import logging
import os
import re
import requests
import subprocess
import sys
import time
import warnings
import webbrowser

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to launch iDRAC HTML KVM session using your default browser.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- LaunchIdracRemoteKvmHtmlSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will launch iDRAC eHTML5 KVM session using your default browser.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.error("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    if "#DelliDRACCardService.GetKVMSession" not in data['Actions'].keys():
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
        
def export_ssl_cert():
    logging.info("- INFO, exporting iDRAC SSL server cert")
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (idrac_ip)
    payload = {"SSLCertType":"Server"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.debug("- INFO, POST command passed to export SSL cert")
    else:
        logging.error("\n- FAIL, POST command failed for ExportSSLCertificate action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    try:
        os.remove("ssl_cert.txt")
    except:
        logging.debug("- INFO, unable to locate ssl_cert.txt file, skipping step to delete file")
    try:
        with open("ssl_cert.txt", "w") as x:
            x.write(data['CertificateFile'])
    except:
        logging.error("- FAIL, unable to write cert contents to file")
        sys.exit(0)

def get_KVM_session_info():
    global temp_username
    global temp_password
    logging.info("- INFO, getting KVM session temporary username, password")
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.GetKVMSession' % (idrac_ip)
    payload={"SessionTypeName":"ssl_cert.txt"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.debug("- INFO, POST command passed to get KVM session")
    else:
        logging.error("\n- FAIL, POST command failed for GetKVMSession action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    try:
        temp_username = data["TempUsername"]
        temp_password = data["TempPassword"]
    except:
        logging.error("- FAIL, unable to locate temp username or password in JSON output")
        sys.exit(0)
    
def launch_KVM_session():
    logging.info("- INFO, launching iDRAC KVM session using your default browser")
    uri_string = "https://%s/console?username=%s&tempUsername=%s&tempPassword=%s" % (idrac_ip, idrac_username, temp_username, temp_password)
    webbrowser.open(uri_string)
    try:
        os.remove("ssl_cert.txt")
    except:
        logging.debug("- INFO, unable to locate ssl_cert.txt file, skipping step to delete file")

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
    export_ssl_cert()
    get_KVM_session_info()
    launch_KVM_session()

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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC certs or replace CSR for iDRAC. When replacing CSR, make sure the CSR has been signed first and once replaced, iDRAC must be reset for the new CSR to be applied.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--certid', help='Replace iDRAC CSR, pass in the cert ID of the cert you want to replace. If needed, execute -c argument to get the cert ID. Example: SecurityCertificate.1', required=False)
parser.add_argument('--filename', help='Replace iDRAC CSR, pass in the filename of the signed CSR.', required=False)
parser.add_argument('--get', help='Get current iDRAC certs', action="store_true", required=False)
parser.add_argument('--reset', help='Reset iDRAC to apply the new uploaded CSR. Note: Starting in iDRAC 5.10.10, iDRAC reset is no longer required after uploading new CSR. New CSR will be applied immediately.', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ReplaceCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current iDRAC cert(s).
    \n- ReplaceCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin --certid SecurityCertificate.1 --filename signed_CSR_cert.cer, this example will replace current CSR with new signed CSR.
    \n- ReplaceCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin --reset, this example will reset the iDRAC to apply the new CSR cert that was just uploaded. iDRAC version installed was 5.00.00.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/CertificateService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/CertificateService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def get_current_iDRAC_certs():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/CertificateService/CertificateLocations?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/CertificateService/CertificateLocations?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    logging.info("\n- Current certificates installed for iDRAC %s -\n" % idrac_ip)
    for i in data.items():
        pprint(i)

def replace_CSR():
    logging.info("\n- INFO, replacing CSR for iDRAC %s, this may take 5-10 seconds to complete\n" % idrac_ip)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logigng.error("\n- ERROR, unable to get iDRAC firmware version, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    url = 'https://%s/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate' % (idrac_ip)
    try:
        open_filename = open(args["filename"],"r")
    except:
        print("- FAIL, unable to locate file \"%s\"" % args["filename"])
        sys.exit(0)
    read_file = open_filename.read()
    open_filename.close()
    if int(data["FirmwareVersion"].replace(".","")) >= 5000000:
        payload = {"CertificateType": "PEM","CertificateUri":{"@odata.id":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates/%s" % args["certid"]},"CertificateString":read_file}
    else:
        payload = {"CertificateType": "PEM","CertificateUri":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates/%s" % args["certid"],"CertificateString":read_file}   
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS, replace CSR cert passed. iDRAC reset is needed for new cert to be applied")
    else:
        logging.error("- FAIL, replace CSR failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)

def reset_idrac():
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % idrac_ip
    payload={"ResetType":"GracefulRestart"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC\n" % response.status_code)
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    time.sleep(15)
    logging.info("- INFO, iDRAC will now reset and be back online within a few minutes.")

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
    if args["certid"] and args["filename"]:
        replace_CSR()
        if args["reset"]:
            reset_idrac()
        else:
            logging.warning("- WARNING, argument --reset not detected. If using iDRAC version older than 5.10.10, iDRAC reset is needed to apply newly uploaded cert. Rerun script again passing in only --reset agrument to reset iDRAC")
    elif args["get"]:
        get_current_iDRAC_certs()
    elif args["reset"]:
        reset_idrac()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

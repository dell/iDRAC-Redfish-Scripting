#!/usr/bin/python3
#
# IdracLicenseManagementREDFISH. Python script using DMTF Redfish API to manage iDRAC licenses.
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
import base64
import getpass
import json
import logging
import os
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using DMTF Redfish API to manage iDRAC licenses (LicenseService). Note: You must have iDRAC9 version 6.10.00 or newer to use the script.") 
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current iDRAC licenses', action="store_true", required=False)
parser.add_argument('--export-local', help='Export iDRAC license locally, pass in the license ID you want to export.', dest="export_local", required=False)
parser.add_argument('--import-networkshare', help='Import iDRAC license from network share, make sure to also pass in --uripath and --sharetype arguments, see examples for more details.', dest="import_networkshare", action="store_true", required=False)
parser.add_argument('--import-local', help='Import iDRAC license locally, pass in the license file name which contains the license in either base 64 string format or XML format.', dest="import_local", required=False)
parser.add_argument('--delete', help='Delete iDRAC license, pass in the complete URI path of the license', required=False)
parser.add_argument('--uripath', help='Pass in complete URI network share path where the license file is located for import. Make sure to also pass in license file name and XML license format is only supported for import from network share. See examples for correct URI syntax, each supported network share type.', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share to export / import iDRAC license. If needed, use argument -st to get supported values for your iDRAC firmware version', required=False)
parser.add_argument('--get-share-types', help='Get supported network share type values for your iDRAC firmware version', action="store_true", dest="get_share_types", required=False)
parser.add_argument('--username', help='Pass in the network share username if auth is configured (required if using CIFS share, optional for HTTP or HTTPS if auth enabled)', required=False)
parser.add_argument('--password', help='Pass in the network share username password if auth is configured (required if using CIFS share, optional for HTTP or HTTPS if auth enabled)', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return iDRAC licenses detected.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/LicenseService/Licenses/23623PA_Enterprise, this example will delete iDRAC license.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-networkshare --sharetype NFS --uripath //192.168.0.130/nfs/ABC4FF3_15g-omeadvplus-evaluation.xml, this example shows importing iDRAC license from NFS share.
    \n- IdracLicenseManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-local ABC4ZZ3_15g-omeadvplus-evaluation.xml, this example shows importing a iDRAC license stored locally.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --export-local 23623PA_Enterprise, this example will export the license locally.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-networkshare --sharetype CIFS --uripath //192.168.0.150/cifs_share/ABC4FF3_15g-omeadvplus-evaluation.xml --username root --password test123, this example shows importing license from CIFS share.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-networkshare --sharetype HTTP --uripath //192.168.0.170/http_share/ABC4FF3_15g-omeadvplus-evaluation.xml, this example shows importing from HTTP share.
    \n- IdracLicenseManagementDmtfREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-networkshare --sharetype HTTPS --uripath //192.168.0.100/https_share/ABC4FF3_15g-omeadvplus-evaluation.xml --username apache_user --password pass123, this example shows importing license from HTTPS share which uses auth.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- FAIL, status code %s detected, incorrect iDRAC credentials detected" % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- FAIL, GET request failed to validate LicenseService is supported, status code %s returned. Error:\n%s" % (response.status_code, data))
        sys.exit(0)

def get_idrac_license_info():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses?$expand=*($levels=1)' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to find iDRAC license data, error: %s" % response)
        sys.exit(0)
    data = response.json()
    if data['Members'] == []:
        logging.warning("\n- WARNING, no licenses detected for iDRAC %s" % idrac_ip)
    else:
        logging.info("\n- License(s) detected for iDRAC %s -\n" % idrac_ip)
        pprint(data)

def export_idrac_license_locally():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses/%s/DownloadURI' % (idrac_ip, args["export_local"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/LicenseService/Licenses/%s/DownloadURI' % (idrac_ip, args["export_local"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to find iDRAC license data, error: %s" % response)
        sys.exit(0)
    with open("%s.xml" % args["export_local"], "wb") as output:
        output.write(response.content)
    logging.info("\n- PASS, %s.xml license successfully exported locally" % args["export_local"])
   
def get_network_share_types():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/LicenseService?$select=Actions' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/LicenseService?$select=Actions' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get supported network share types, error is: %s" % response)
        sys.exit(0)
    data = response.json()
    logging.info("\n- Supported network share types for Export / Import license from network share -\n")
    print(data["Actions"]["#LicenseService.Install"]["TransferProtocol@Redfish.AllowableValues"])

def delete_idrac_license():
    url = 'https://%s%s' % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS: DELETE command passed to remove iDRAC license, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, DELETE command failed to remove iDRAC license, status code %s returned" % response.status_code)
        logging.error("\n- DELETE command failure results:\n %s" % response.json())
        sys.exit(0)    
    
def import_idrac_license_networkshare():
    global job_id
    url = 'https://%s/redfish/v1/LicenseService/Actions/LicenseService.Install' % (idrac_ip)
    payload = {"LicenseFileURI": args["uripath"], "TransferProtocol": args["sharetype"]}
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed to import license, status code %s returned\n" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed to import license, status code %s returned" % response.status_code)
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location']
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("- PASS, job ID %s successfuly created to import iDRAC license" % job_id.split("/")[-1])

def import_idrac_license_local():
    try:
        filename_open = open(args["import_local"], "r")
    except:
        print("\n- FAIL, unable to locate filename \"%s\"" % args["import_local"])
        sys.exit(0)
    name, extension = os.path.splitext(args["import_local"])
    if extension.lower() == ".xml":
        with open(args["import_local"], 'rb') as cert:
            cert_content = cert.read()
            read_file = base64.encodebytes(cert_content).decode('ascii')
    else:
        read_file = filename_open.read()
    filename_open.close()
    url = 'https://%s/redfish/v1/LicenseService/Licenses' % (idrac_ip)
    payload = {"LicenseString":read_file}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 201:
        logging.info("\n- PASS, license filename \"%s\" successfully imported" % args["import_local"])
    else:
        data = response.json()
        logging.error("\n- FAIL, unable to import license filename \"%s\", status code %s, error results: \n%s" % (args["import_local"], response.status_code, data))
        sys.exit(0)   

def loop_job_status():
    start_time = datetime.now()
    time.sleep(1)
    while True:
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        time.sleep(3)
        data = response.json()
        if str(current_time)[0:7] >= "0:05:00":
            logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif data["Oem"]["Dell"]["JobState"] == "Failed":
            logging.error("- FAIL: job ID %s failed, detailed error results: \n%s" % (job_id.split("/")[-1], data))
            sys.exit(0)
        elif data["Oem"]["Dell"]["JobState"] == "Completed":
            logging.info("\n- PASS, iDRAC license successfully imported from network share")
            break
        else:
            logging.info("- INFO, job status not completed, execution time: \"%s\"" % (str(current_time)[0:7]))

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
    if args["get"]:
        get_idrac_license_info()
    elif args["get_share_types"]:
        get_network_share_types()
    elif args["export_local"]:
        export_idrac_license_locally()
    elif args["import_networkshare"] and args["uripath"] and args["sharetype"]:
        import_idrac_license_networkshare()
        loop_job_status()
    elif args["import_local"]:
        import_idrac_license_local()
    elif args["delete"]:
        delete_idrac_license()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# IdracLicenseManagementOemREDFISH. Python script using Redfish API with OEM extension to manage iDRAC license(s).
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to manage iDRAC license(s). Supported script operations are: view current licenses, export / import / delete licenses")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current iDRAC licenses', action="store_true", required=False)
parser.add_argument('--export-local', help='Export iDRAC license locally, pass in the license ID you want to export. Note: This will export the license in base 64 string format', dest="export_local", required=False)
parser.add_argument('--export-share', help='Export iDRAC license to network share, pass in the license ID you want to export', dest="export_share", required=False)
parser.add_argument('--import-share', help='Import iDRAC license from network share', action="store_true", dest="import_share", required=False)
parser.add_argument('--import-local', help='Import iDRAC license locally, pass in the license file name which contains the license in either base 64 string format or XML format.', dest="import_local", required=False)
parser.add_argument('--delete', help='Delete iDRAC license, pass in the license ID you want to delete', required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share to export / import iDRAC license', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share to export / import iDRAC license. If needed, use argument -st to get supported values for your iDRAC firmware version', required=False)
parser.add_argument('--get-share-types', help='Get supported network share type values for your iDRAC firmware version', action="store_true", dest="get_share_types", required=False)
parser.add_argument('--sharename', help='Pass in the network share name for export / import iDRAC license', required=False)
parser.add_argument('--username', help='Pass in the network share username if auth is configured (required if using CIFS share)', required=False)
parser.add_argument('--password', help='Pass in the network share username password if auth is configured (required if using CIFS share)', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are On and Off. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--licensename', help='Pass in name of the license file on the network share you want to import', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- IdracLicenseManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return current iDRAC licenses installed.
    \n- IdracLicenseManagementOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --export-local 7386PA_iDRAC_Enterprise_license, this example will export iDRAC Enterprise license locally.
    \n- IdracLicenseManagementOemREDFISH.py -ip 192.168.0.120 -x 0dbf8d1fc38382ed5cffa07545f631c3 --export-share 7472PX_iDRAC_Enterprise_license --shareip 192.168.0.130 --sharename /nfs --sharetype NFS, this example using iDRAC x-auth token will export license to network share.
    \n- IdracLicenseManagementOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-share --shareip 192.168.0.130 --sharetype NFS --sharename /nfs --licensename iDRAC_enterprise_license.xml, this example will import iDRAC enterprise license from NFS share.
    \n- IdracLicenseManagementOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-local 7472PX_iDRAC_Enterprise_license.txt, this example shows importing local locense.
    \n- IdracLicenseManagementOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete 7386PA_iDRAC_Enterprise_license, this example shows deleting iDRAC license.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- FAIL, status code %s detected, incorrect iDRAC credentials detected" % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- FAIL, GET request failed to validate DellLicenseCollection is supported, status code %s returned. Error:\n%s" % (response.status_code, data))
        sys.exit(0)

def get_idrac_license_info():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to find iDRAC license data, error: %s" % response)
        sys.exit(0)
    data = response.json()
    if data['Members'] == []:
        logging.warning("\n- WARNING, no licenses detected for iDRAC %s" % idrac_ip)
    else:
        logging.info("\n- License(s) detected for iDRAC %s -\n" % idrac_ip)
        for i in (data['Members']):
            pprint(i), print("\n")
   
def get_network_share_types():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get supported network share types, error is: %s" % response)
        sys.exit(0)
    data = response.json()
    logging.info("\n- Supported network share types for Export / Import license from network share -\n")
    for i in data['Actions']['#DellLicenseManagementService.ExportLicenseToNetworkShare']['ShareType@Redfish.AllowableValues']:
        print(i)
    
def export_idrac_license_locally():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicense' % (idrac_ip)
    method = "ExportLicense"
    payload={"EntitlementID":args["export_local"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("- iDRAC license for \"%s\" ID:\n" % args["export_local"])
    print(data['LicenseFile'])
    with open("%s_iDRAC_license.txt" % args["export_local"], "w") as x:
        x.writelines(data['LicenseFile'])
    logging.info("\n- License also copied to \"%s_iDRAC_license.txt\" file" % args["export_local"])
    
def export_import_idrac_license_network_share():
    global job_id
    if args["export_share"]:
        license_filename = "%s_iDRAC_license.xml" % args["export_share"]
        method = "ExportLicenseToNetworkShare"
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicenseToNetworkShare' % (idrac_ip)
        payload = {"EntitlementID":args["export_share"],"FileName":license_filename}
    elif args["import_share"]:
        method = "ImportLicenseFromNetworkShare"
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ImportLicenseFromNetworkShare' % (idrac_ip)
        payload = {"FQDD":"iDRAC.Embedded.1","ImportOptions":"Force"}
        if args["licensename"]:
            payload["LicenseName"] = args["licensename"]
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"].upper()
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertificateWarning"] = args["ignorecertwarning"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))

def delete_idrac_license():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.DeleteLicense' % (idrac_ip)
    method = "DeleteLicense"
    payload={"EntitlementID":args["delete"],"DeleteOptions":"Force"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)

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
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ImportLicense' % (idrac_ip)
    payload = {"FQDD":"iDRAC.Embedded.1","ImportOptions":"Force","LicenseFile":read_file}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
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
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % statusCode)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:05:00":
            logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "The command was successful":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
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
    elif args["export_local"]:
        export_idrac_license_locally()
    elif args["get_share_types"]:
        get_network_share_types()
    elif args["import_local"]:
        import_idrac_license_local()
    elif args["export_share"] or args["import_share"]:
        export_import_idrac_license_network_share()
        loop_job_status()
    elif args["delete"]:
        delete_idrac_license()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

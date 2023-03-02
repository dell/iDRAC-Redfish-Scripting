#!/usr/bin/python3
#
# ExportServerConfigurationNetworkShareREDFISH. Python script using Redfish API to export server configuration profile to a supported network share.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 13.0
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

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to export server configuration profile (SCP) to a supported network share")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-target-values', help='Get supported values for --target argument', action="store_true", dest="get_target_values", required=False)
parser.add_argument('--target', help='Pass in Target value to get component attributes. You can pass in \"ALL" to get all component attributes or pass in specific component(s) to get only those attributes. If you pass in multiple values use a comma separator. To get all supported values, use argument --get-target-values', required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values: NFS, CIFS, HTTP and HTTPS.', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the network share username if your share is setup for auth.', required=False)
parser.add_argument('--password', help='Pass in the network share username password if your share is setup for auth', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--export-use', help='Pass in ExportUse value. Supported values are Default, Clone and Replace. If you don\'t use this parameter, default setting is Default or Normal export.', dest="export_use", required=False)
parser.add_argument('--include', help='Pass in IncludeInExport value. Supported values are 0 for \"Default\", 1 for \"IncludeReadOnly\", 2 for \"IncludePasswordHashValues\" or 3 for \"IncludeReadOnly,IncludePasswordHashValues\". If you don\'t use this parameter, default setting is Default for IncludeInExport.', required=False)
parser.add_argument('--filename', help='Pass in unique filename for the SCP file which will get created on the network share', required=False)
parser.add_argument('--format-type', help='Pass in the format type for SCP file generated. Supported values are XML and JSON', dest="format_type", required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Enabled and Disabled. This argument is only required if using HTTPS for share type', required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportSystemConfigurationNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --target ALL --format-type XML --shareip 192.168.0.130 --sharetype NFS --sharename /nfs --filename SCP_export_R740, this example is going to export attributes for all devices in a default XML SCP file to a NFS share.
    \n- ExportSystemConfigurationNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-target-values, this example will return supported values to pass in for --target argument.
    \n- ExportSystemConfigurationNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --target BIOS --format-type JSON --shareip 192.168.0.140 --sharetype CIFS --sharename cifs_share_vm --filename R740_scp_file --export-use Clone --username administrator --password password, this example is going to export only BIOS attributes in a clone JSON SCP file to a CIFS share.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def get_target_values():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get supported target values, status code %s returned" % response.status_code)
        print(data)
        sys.exit(0)
    logging.info("\n- INFO, supported values for --target argument\n")
    for i in data["Actions"]["Oem"]["#OemManager.v1_4_0.OemManager#OemManager.ExportSystemConfiguration"]["ShareParameters"]["Target@Redfish.AllowableValues"]:
        print(i)

def export_server_configuration_profile():
    global job_id
    method = "ExportSystemConfiguration"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    payload = {"ExportFormat":args['format_type'].upper(),"ShareParameters":{"Target":args["target"]}}
    if args["export_use"]:
        payload["ExportUse"] = args["export_use"]
    if args["include"]:
        if args["include"] == "0":
            payload["IncludeInExport"] = "Default"
        if args["include"] == "1":
            payload["IncludeInExport"] = "IncludeReadOnly"
        if args["include"] == "2":
            payload["IncludeInExport"] = "IncludePasswordHashValues"
        if args["include"] == "3":
            payload["IncludeInExport"] = "IncludeReadOnly,IncludePasswordHashValues"
    if args["shareip"]:
        payload["ShareParameters"]["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareParameters"]["ShareType"] = args["sharetype"].upper()
    if args["sharename"]:
        payload["ShareParameters"]["ShareName"] = args["sharename"]
    if args["filename"]:
            payload["ShareParameters"]["FileName"] = args["filename"]
    if args["username"]:
        payload["ShareParameters"]["Username"] = args["username"]
    if args["password"]:
        payload["ShareParameters"]["Password"] = args["password"]
    if args["workgroup"]:
        payload["ShareParameters"]["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["ShareParameters"]["IgnoreCertificateWarning"] = args["ignorecertwarning"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        logging.error("- FAIL, POST command failed to export system configuration, status code %s returned" % response.status_code)
        logging.error("- Error details: %s" % response.__dict__)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("\n- Job ID \"%s\" successfully created for ExportSystemConfiguration method\n" % job_id)

def loop_job_status():
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:05:00":
            logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "fail" in data['Message'].lower() or "unable" in data['Message'].lower() or "not" in data['Message'].lower():
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "Successfully exported Server Configuration Profile":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, %s, percent complete: %s" % (data['Message'],data['PercentComplete']))
            time.sleep(1)

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
    if args["get_target_values"]:
        get_target_values()
    elif args["target"] and args["format_type"] and args["filename"] and args["shareip"] and args["sharetype"]:
        export_server_configuration_profile()
        loop_job_status()
    else:
        logging.warning("\n- WARNING, arguments --target, --format-type, --filename, --sharename, --sharetype and --shareip are required for export. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# ExportHWInventoryREDFISH. Python script using Redfish API with OEM extension to export server hardware(HW)
# inventory to either local directory or network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _author_ = Grant Curell <grant_curell@dell.com>
# _version_ = 14.0
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
import getpass
import json
import logging
import re
import requests
import sys
import time
import urllib.parse
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export server hardware(HW) inventory to either local directory or supported network share.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password.', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values: Local, NFS, CIFS, HTTP and HTTPS.', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the network share username if your share is setup for auth.', required=False)
parser.add_argument('--password', help='Pass in the network share username password if your share is setup for auth.', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional.', required=False)
parser.add_argument('--filename', help='Pass in unique filename for export hardware inventory file, file extension must be .xml. This argument is required for export to network share but optional for local export. Default filename for local export is hwinv.xml if argument is not passed.', required=False, default='hwinv.xml')
parser.add_argument('--ignorecertwarning', help='Supported values are Enabled and Disabled. This argument is only required if using HTTPS for share type.', required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --shareip 192.168.0.130 --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename R650_export_hw_inv.xml, this example will export the server hardware inventory to CIFS share.
    \n- ExportHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --sharetype local, this example will export the HW configuration locally using default filename hwinv.xml.
    \n- ExportHWInventoryREDFISH.py -ip 192.168.0.120 -x 442b945cf658fbcebb6ba1ffdcf6c6f8 --sharetype NFS --shareip 192.168.0.180 --sharename /nfs --filename R650_hw.xml, this example using X-auth token session will export server hardware inventory to NFS share.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def export_hw_inventory():
    """
    Exports server hardware inventory either locally or to supported network share. Job ID will be returned in headers output to poll the progress of the action.
    """
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportHWInventory' % idrac_ip
    method = "ExportHWInventory"
    payload = {}
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        if args["sharetype"] == "local" or args["sharetype"] == "Local":
            payload["ShareType"] = args["sharetype"].title()
            logging.info("\n- INFO, collecting data for exporting server hardware inventory, this may take 15-30 seconds to complete")
        else:
            payload["ShareType"] = args["sharetype"].upper()
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["filename"]:
        payload["FileName"] = args["filename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:")
        logging.error(data)
        sys.exit(0)
    if args["sharetype"].lower() == "local":
        if response.headers['Location'] == "/redfish/v1/Dell/hwinv.xml":
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, response.headers['Location']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s' % (idrac_ip, response.headers['Location']), verify=verify_cert,auth=(idrac_username, idrac_password))
            if args["filename"]:
                export_filename = args["filename"]
            else:
                export_filename = "hwinv.xml"    
            with open(export_filename, "wb") as output:
                output.write(response.content)
            logging.info("\n- INFO, check your local directory for hardware inventory XML file \"%s\"" % export_filename)
            sys.exit(0)
        else:
            logging.error("- ERROR, unable to locate exported hardware inventory URI in headers output. Manually run GET on URI %s to see if file can be exported." % response.headers['Location'])
            sys.exit(0)
    else:
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            sys.exit(0)
        logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))

def loop_job_status():
    """
    Job ID returned from DellLCService.ExportHWInventory action, this will loop checking the job status until marked completed. 
    """
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now() - start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:05:00":
            logging.error("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "Hardware Inventory Export was successful":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job state not marked completed, current job status is running, polling again")
            time.sleep(2)

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
    export_hw_inventory()
    loop_job_status()

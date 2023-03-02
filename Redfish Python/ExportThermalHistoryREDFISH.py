#!/usr/bin/python3
#
# ExportThermalHistoryREDFISH. Python script using Redfish API with OEM extension to export server thermal history to a network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export server thermal history to a supported network share. NOTE: export locally is not supported for this OEM action.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--shareip', help='Pass in IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in share type of the network share. Supported values are NFS and CIFS', required=False)
parser.add_argument('--sharename', help='Pass in network share name', required=False)
parser.add_argument('--username', help='Pass in CIFS username. This argument is only required when using CIFS share.', required=False)
parser.add_argument('--password', help='Pass in CIFS username password. This argument is only required when using CIFS share.', required=False)
parser.add_argument('--workgroup', help='Pass in workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--filename', help='Pass in unique file name string for exporting thermal history file', required=False)
parser.add_argument('--filetype', help='Exported file type, supported values are XML or CSV', required=False)

args=vars(parser.parse_args())

logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --shareip 192.168.0.130 --ssl True --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename export_thermal_history_R640.xml --filetype XML, this example will validate SSL cert for all Redfish calls, export server thermal history in XML file format to a CIFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 --shareip 192.168.0.130 --sharetype NFS --sharename /nfs --filename R740_thermal.xml --filetype xml -x 25342b24713cbaeaf9568ab14770z11w, this example uses iDRAC X-auth token session to export thermal history to NFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root --shareip 192.168.0.130 --ssl True --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename export_thermal_history_R640.xml --filetype XML, this example will first prompt to enter iDRAC user password (will not be returned to the screen), validate SSL cert for all Redfish calls, export server thermal history in XML file format to a CIFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --shareip 192.168.0.130 --sharetype NFS --sharename /nfs --filename export_thermal_history_R640.xml --filetype CSV, this example will export thermal history in CSV file format to NFS share.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def export_thermal_history():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService/Actions/DellMetricService.ExportThermalHistory' % (idrac_ip)
    method = "ExportThermalHistory"
    payload={}
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["filename"]:
            payload["FileName"] = args["filename"]
    if args["filetype"]:
            payload["FileType"] = args["filetype"].upper()
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS, POST command passed for %s method, status code 202 returned" % method)
    else:
        logging.error("\n- ERROR, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- ERROR, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
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
            if data['Message'] == "The command was successful":
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
   if args["filename"] and args["filetype"] and args["shareip"] and args["sharetype"]:
        export_thermal_history()
        loop_job_status()
   else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

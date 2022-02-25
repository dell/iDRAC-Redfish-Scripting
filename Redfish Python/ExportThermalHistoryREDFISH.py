#
# ExportThermalHistoryREDFISH. Python script using Redfish API with OEM extension to export server thermal history to a network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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
parser.add_argument('-p', help='iDRAC password. NOTE: If you do not pass in this argument, script will prompt to enter iDRAC user password and will not be returned to the screen.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID. When using this token, you do not need to pass in username and password. All Redfish calls will use the token for auth (recommended).', required=False)
parser.add_argument('--verify-ssl-cert', help='verify SSL cert', type=lambda x: (str(x).lower() == 'true'), dest="verify_ssl_cert", required=False)
parser.add_argument('--script-examples', help='Get examples of executing script.', action="store_true", dest="script_examples", required=False)
parser.add_argument('--ipaddress', help='Pass in IP address of the network share', required=False)
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
    print("""\n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --verify-ssl-cert True --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename export_thermal_history_R640.xml --filetype XML, this example will validate SSL cert for all Redfish calls, export server thermal history in XML file format to a CIFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --filename R740_thermal.xml --filetype xml --verify-ssl-cert False -x 25342b24713cbaeaf9568ab14770z11w, this example uses iDRAC X-auth token session to export thermal history to NFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root --ipaddress 192.168.0.130 --verify-ssl-cert True --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename export_thermal_history_R640.xml --filetype XML, this example will first prompt to enter iDRAC user password (will not be returned to the screen), validate SSL cert for all Redfish calls, export server thermal history in XML file format to a CIFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --verify-ssl-cert False --sharetype NFS --sharename /nfs --filename export_thermal_history_R640.xml --filetype CSV, this example will NOT validate SSL cert for all Redfish calls, export thermal history in CSV file format to NFS share.""")

def check_supported_idrac_version():
    # Function to check support iDRAC version, if the iDRAC supports OEM extension for DellMetricService.
    try:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % idrac_ip, verify=args["verify_ssl_cert"],headers={'X-Auth-Token': args["x"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService' % idrac_ip, verify=args["verify_ssl_cert"],auth=(idrac_username, idrac_password))
    except requests.ConnectionError as error_message:
        logging.warning("\n- WARNING, either missing \"--verify-ssl-cert\" argument or SSL certificate verification failed for self signed certificate. If you passed in True for \"--verify-ssl-cert\", check to make sure iDRAC has correct signed certificate uploaded or execute script again passing in \"--verify-ssl-cert False\" to skip cert check.")
        sys.exit(0)
    data = response.json()
    if response.__dict__['reason'] == "Unauthorized":
        logging.warning("\n- WARNING, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def export_thermal_history():
    # Function to export thermal history to either CIFS or NFS share.
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService/Actions/DellMetricService.ExportThermalHistory' % (idrac_ip)
    method = "ExportThermalHistory"
    #headers = {'content-type': 'application/json'}
    payload={}
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
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
    #response = requests.post(url, data=json.dumps(payload), headers=headers, verify=args["verify_ssl_cert"],auth=(idrac_username,idrac_password))
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=args["verify_ssl_cert"])
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=args["verify_ssl_cert"],auth=(idrac_username, idrac_password))
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
    # Function to loop and check job staus for export thermal history. Script will loop until job ID marked completed or failed. 
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=args["verify_ssl_cert"],headers={'X-Auth-Token': args["x"]})    
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=args["verify_ssl_cert"],auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- ERROR, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:05:00":
            logging.error("\n- ERROR: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
            logging.error("- ERROR: job ID %s failed, failed message: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "The command was successful":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            pprint(data)
            break
        else:
            logging.info("- INFO job state not marked completed, current job status is running, polling again")
            
    

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    else:
        if args["x"] and not args["u"]:
            idrac_ip = args["ip"]
        elif args["ip"] and args["u"]:
            idrac_ip = args["ip"]
            idrac_username = args["u"]
        else:
            logging.error("\n- ERROR, missing -ip or -u argument")
            sys.exit(0)
        if not args["p"] and not args["x"]:
            idrac_password = getpass.getpass("\n- Enter iDRAC username \"%s\" password: " % idrac_username)
        if args["p"]:
            idrac_password = args["p"]
        check_supported_idrac_version()
        export_thermal_history()
        loop_job_status()
    
    
        
            
        
        

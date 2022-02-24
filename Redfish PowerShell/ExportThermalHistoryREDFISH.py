#
# ExportThermalHistoryREDFISH. Python script using Redfish API with OEM extension to export server thermal history to a network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
import json
import logging
import re
import requests
import sys
import time
import warnings

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export server thermal history to a supported network share. NOTE: export locally is not supported for this OEM action.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
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

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --sharetype CIFS --sharename cifs_share_vm --username administrator --password pass --filename export_thermal_history_R640.xml --filetype XML, this example will export server thermal history in XML file format to a CIFS share.
    \n- ExportThermalHistoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --filename export_thermal_history_R640.xml --filetype CSV, this example will export thermal history in CSV file format to NFS share.""")

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.__dict__['reason'] == "Unauthorized":
        logging.warning("\n- WARNING, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def export_thermal_history():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellMetricService/Actions/DellMetricService.ExportThermalHistory' % (idrac_ip)
    method = "ExportThermalHistory"
    headers = {'content-type': 'application/json'}
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
            payload["FileType"] = args["filetype"]
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
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
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode != 200:
            logging.error("\n- ERROR, GET command failed to check job status, return code %s" % statusCode)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = req.json()
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
            for i in data.items():
                if "odata" not in i[0] or "MessageArgs" not in i[0] or "TargetSettingsURI" not in i[0]:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            logging.info("- INFO job state not marked completed, current job status is running, polling again")
            
    

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    else:
        check_supported_idrac_version()
        export_thermal_history()
        loop_job_status()
    
    
        
            
        
        

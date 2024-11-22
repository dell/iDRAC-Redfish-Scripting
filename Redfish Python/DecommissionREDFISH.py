
#!/usr/bin/python3
# 
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2024, Dell, Inc.
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
import platform
import re
import requests
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to run DMTF decommission action. Note this action is only supported on iDRAC10 or newer.')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--get-types', help='Get supported decommission type values to pass in for POST action. Note: DMTF \"All\" value will run all supported DMTF types. Note: ManagerConfig DMTF type will also reboot the iDRAC. Note: all OEM types will reboot the iDRAC.', action="store_true", dest="get_types", required=False) 
parser.add_argument('--decommission', help='Perform decommission operation. Note argument --type is also required.', action="store_true", required=False) 
parser.add_argument('--type', help='Pass in Decommission type(s) you want to perform. Note if multiple types are passed in use a comma separator.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DecommissionREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-types, this example will return all supported Decommission types, both DMTF and OEM
    \n- DecommissionREDFISH.py -ip 192.168.0.120 -u root -p calvin --decommission --type Logs, this example will run Decommission action to clear iDRAC SEL and LC logs
    \n- DecommissionREDFISH.py -ip 192.168.0.120 -u root -p calvin --decommission --type ManagerConfig,DellFwStoreClean, this example will run Decommission action to reset iDRAC to default settings and remove non-recovery related firmware packages.""")
    sys.exit(0)
    
def get_server_generation():
    global idrac_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if "12" in data["Model"] or "13" in data["Model"]:
        idrac_version = 8
    elif "14" in data["Model"] or "15" in data["Model"] or "16" in data["Model"]:
        idrac_version = 9
    else:
        idrac_version = 10

def get_decommission_types():
    global idrac_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get supported decommission types, status code %s" % response.status_code)
        print(data)
        sys.exit(0)
    print("\n- Supported DMTF Decommission types: \n\n%s" % data["Actions"]["#ComputerSystem.Decommission"]["DecommissionTypes@Redfish.AllowableValues"])
    print("\n- Supported OEM Decommission types: \n\n%s" % data["Actions"]["#ComputerSystem.Decommission"]["OEMDecommissionTypes@Redfish.AllowableValues"])

def run_decommission():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get supported decommission types, status code %s" % response.status_code)
        print(data)
        sys.exit(0)
    dmtf_supported_types = data["Actions"]["#ComputerSystem.Decommission"]["DecommissionTypes@Redfish.AllowableValues"]
    oem_supported_types = data["Actions"]["#ComputerSystem.Decommission"]["OEMDecommissionTypes@Redfish.AllowableValues"]
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Decommission" % idrac_ip
    payload = {"DecommissionTypes":[], "OEMDecommissionTypes":[]}
    if "," in args["type"]:
        decommission_types = args["type"].split(",")
    else:
        decommission_types = [args["type"]]
    for i in decommission_types:
        if i in dmtf_supported_types:
            payload["DecommissionTypes"].append(i)
        if i in oem_supported_types:
            payload["OEMDecommissionTypes"].append(i)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS, status code %s returned for POST Decommission action" % response.status_code)
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned for POST Decommission action failure, detailed error results \n%s" % (response.status_code, data))
        sys.exit(0)

def loop_task_status():
    start_time = datetime.now()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/decommission' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/decommission' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code == 200 or response.status_code == 202:
            logging.debug("- PASS, GET request passed to check job status")
        else:
            logging.error("\n- FAIL, GET command failed to check task status, return code %s returned" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "1:00:00":
            logging.error("\n- FAIL: Timeout of 1 hour has been hit, script stopped\n")
            sys.exit(0)
        elif data['TaskState'] == "Failed":
            logging.error("- FAIL: task ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['TaskState'] == "Completed" and data['PercentComplete'] == 100:
            logging.info("\n--- PASS, Final Detailed Task Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, task not completed, current status: \"%s\"" % data['TaskState'])
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
        get_server_generation()
        if idrac_version != 10:
            logging.warning("\n- WARNING, iDRAC version detected does not support this feature")
            sys.exit(0)
    if args["get_types"]:
        get_decommission_types()
    elif args["decommission"] and args["type"]:
        run_decommission()
        loop_task_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    
        

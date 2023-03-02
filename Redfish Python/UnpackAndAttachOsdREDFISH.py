#!/usr/bin/python3
#
# UnpackAndAttachOsdREDFISH. Python script using Redfish API with OEM extension to either get driver pack information, unpack and attach driver pack or detach driver pack
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension either to get driver pack information, unpack and attach driver pack or detach driver pack")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-driverpack', help='Get driver pack information for current OS driver packs supported by iDRAC', dest="get_driverpack", action="store_true", required=False)
parser.add_argument('--get-attach-status', help='Get attach status for driver pack', dest="get_attach_status", action="store_true", required=False)
parser.add_argument('--driverpack', help='Unpack and attach driver pack, pass in the operating system(OS) string. Example: pass in \"Microsoft Windows Server 2012 R2\"(make sure to pass double quotes around the string value)', required=False)
parser.add_argument('--detach', help='Detach driver pack', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-driverpack, this example to get current driver pack list.
    \n- UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-attach-status, this example will return current driver pack attach status.
    \n- UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --driverpack \"Microsoft Windows Server 2022\". This example will unpack and attach Windows Server 2022 driver pack.
    \n- UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --detach, this example will detach attached driver pack.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_driver_pack_info():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetDriverPackInfo' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS: POST command passed to get driver pack information, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to get driver pack information, status code is %s" % (response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("\n- Driver packs supported for iDRAC %s\n" % idrac_ip)
    pprint(data['OSList'])

def get_attach_status():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    payload={}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS: POST command passed to get driver pack attach status, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to get driver pack attach status, status code is %s" % (response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("- INFO, Current driver pack attach status: %s" % data['DriversAttachStatus'])
    
def unpack_and_attach_driver_pack():
    global concrete_job_uri
    global start_time
    method = "UnpackAndAttach"
    start_time = datetime.now()
    logging.info("\n- INFO, starting %s operation which may take 5-10 seconds to create the task" % method)
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.UnpackAndAttach' % (idrac_ip)
    method = "UnpackAndAttach"
    payload = {"OSName":args["driverpack"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    concrete_job_uri = response.headers[u'Location']
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        concrete_job_uri = response.headers['Location']
        logging.info("- INFO, task URI created for method %s: %s\n" % (method, concrete_job_uri))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    
def detach_driver_pack():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachDrivers' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS: POST command passed to detach driver pack, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to detach driver pack, status code is %s" % (response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)

def check_concrete_job_status():
    while True:
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, concrete_job_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s%s' % (idrac_ip, concrete_job_uri), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code == 200 or response.status_code == 202:
            logging.debug("- PASS, GET command passed to get task details")
        else:
            logging.error("\n- FAIL, command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif data['TaskState'] == "Completed":
            if "Fail" in data['Messages'][0]['Message'] or "fail" in data['Messages'][0]['Message']:
                logging.error("- FAIL: concrete job failed, detailed error results: %s" % data.items())
                sys.exit(0)
            elif "completed successful" in data['Messages'][0]['Message'] or "command was successful" in data['Messages'][0]['Message']:
                logging.info("\n- PASS, task successfully marked completed")
                logging.info("\n- Final detailed task results -\n")
                for i in data.items():
                    pprint(i)
                logging.info("\n- INFO, task completion time: %s" % (current_time))
                break
            else:
                logging.error("- FAIL, unable to get final task message string")
                sys.exit(0)
        elif data["TaskState"] == "Exception":
            logging.error("\n- FAIL, final detailed task results -\n")
            for i in data.items():
                pprint(i)
            sys.exit(0)
        else:
            logging.info("- INFO, task not completed, current status: \"%s\", job execution time: \"%s\"" % (data['TaskState'], current_time))
            time.sleep(10)    

def check_attach_status(x):
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    payload={}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, POST command failed to get driverpack attach status, status code %s" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    if data['DriversAttachStatus'] == x:
        logging.info("- PASS, driverpack attach status successfully identified as \"%s\"" % x)
    else:
        logging.error("- FAIL, driverpack attach status not successfully identified as %s" % x)
        sys.exit(0)
        
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
    if args["get_driverpack"]:
        get_driver_pack_info()
    elif args["get_attach_status"]:
        get_attach_status()
    elif args["driverpack"]:
        unpack_and_attach_driver_pack()
        check_concrete_job_status()
        check_attach_status("Attached")
    elif args["detach"]:
        detach_driver_pack()
        check_attach_status("NotAttached")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

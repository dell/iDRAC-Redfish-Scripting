#!/usr/bin/python3
#
# BootToNetworkIsoOsdREDFISH. Python script using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-attach-status', help='Get attach status for network ISO', action="store_true", dest="get_attach_status", required=False)
parser.add_argument('--boot-iso', help='Boot to network ISO. Make sure to also pass in network share arguments, see examples for more details', action="store_true", dest="boot_iso", required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS and CIFS', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--imagename', help='Pass in the operating system(OS) string you want to boot from on your network share', required=False)
parser.add_argument('--detach-iso', help='Detach network ISO', action="store_true", dest="detach_iso", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- BootToNetworkIsoOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-attach-status, this example to get current network ISO attach status.
    \n- BootToNetworkIsoOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --boot-iso --shareip 192.168.0.130 --sharetype NFS --sharename /nfs --imagename ESXi.iso, this example will boot to network ISO on NFS share
    \n- BootToNetworkIsoOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin --detach-iso, this example will detach attached ISO.""")
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
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed to get ISO attach status, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to get ISO attach status, status code is %s" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit()
    logging.info("- INFO, current ISO attach status: %s" % data['ISOAttachStatus'])
    
def boot_to_network_iso():
    global concrete_job_uri
    global start_time
    method = "BootToNetworkISO"
    start_time = datetime.now()
    logging.info("\n- INFO, starting %s operation which may take 5-10 seconds to create the task" % method)
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.BootToNetworkISO' % (idrac_ip)
    payload={}
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["imagename"]:
        payload["ImageName"] = args["imagename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        concrete_job_uri = response.headers['Location']
        logging.info("- INFO, concrete job URI created for method %s: %s\n" % (method, concrete_job_uri))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    
def detach_network_iso():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachISOImage' % (idrac_ip)
    payload={}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed to detach ISO image, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to detach ISO image, status code is %s" % (response.status_code))
        data = response.json()
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
        logging.error("\n- FAIL, POST command failed to get ISO attach status, status code is %s" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    if data['ISOAttachStatus'] == x:
        logging.info("- PASS, ISO attach status successfully identified as \"%s\"" % x)
    else:
        logging.error("- FAIL, ISO attach status not successfully identified as %s" % x)
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
    if args["get_attach_status"]:
        get_attach_status()
    elif args["boot_iso"] and args["shareip"] and args["sharetype"] and args["sharename"]:
        boot_to_network_iso()
        check_concrete_job_status()
        check_attach_status("Attached")
    elif args["detach_iso"]:
        detach_network_iso()
        check_attach_status("NotAttached")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)   

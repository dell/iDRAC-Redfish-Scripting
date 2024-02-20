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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to change controller mode (RAID to HBA, HBA to RAID) for PERC 9 controllers only (H330, H730 and H830).")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-controller-mode', help='Get storage controller current mode pass in controller FQDD', dest="get_controller_mode", required=False)
parser.add_argument('--change-controller-mode', help='Change controller mode pass in controller FQDD', dest="change_controller_mode", required=False)
parser.add_argument('--mode', help='Pass in controller mode value you want to change to. Supported values: HBA and RAID', required=False)
parser.add_argument('--reboot', help='Pass in this argument to reboot the server now to apply configuration changes. Note if this argument is not passed in configuration job is still created and scheduled, will run next server manual reboot.', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ChangeControllerModePerc9REDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651bbf --get-controllers, this example using iDRAC X-auth token session will return controller FQDDs.
    \n- ChangeControllerModePerc9REDFISH.py -ip 192.168.0.120 -u root -p calvin --get-controller-mode RAID.Integrated.1-1, this example will return current mode for controller RAID.Integrated.1-1.
    \n- ChangeControllerModePerc9REDFISH.py -ip 192.168.0.120 -u root -p calvin --change-controller-mode RAID.Integrated.1-1 --mode HBA --reboot, this example shows rebooting the server now to change controller mode to HBA.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
        
def test_valid_controller_FQDD_string(x):
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string value is case sensitive)")
        sys.exit(1)

def get_storage_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, status code %s returned for GET request, error details:\n" % response.status_code)
        print(data)
        sys.exit(0)
    logging.info("\n- Server controller(s) detected -\n")
    for i in data['Members']:
        print(i['@odata.id'].split("/")[-1])

def get_controller_mode():
    test_valid_controller_FQDD_string(args["get_controller_mode"])
    if args["x"]:
        response = requests.get('https://{0}/redfish/v1/Systems/System.Embedded.1/Storage/{1}/Controllers/{1}?$select=Oem/Dell/DellStorageController/ControllerMode'.format(idrac_ip, args["get_controller_mode"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://{0}/redfish/v1/Systems/System.Embedded.1/Storage/{1}/Controllers/{1}?$select=Oem/Dell/DellStorageController/ControllerMode'.format(idrac_ip, args["get_controller_mode"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, status code %s returned for GET request, error details:\n" % response.status_code)
        print(data)
        sys.exit(0)
    logging.info("\n- Controller %s current mode: %s" % (args["get_controller_mode"], data["Oem"]["Dell"]["DellStorageController"]["ControllerMode"]))


def change_controller_mode():
    global job_id
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}, "Oem":{"Dell":{"DellStorageController":{"ControllerMode": args["mode"].upper()}}}}
    url = "https://{0}/redfish/v1/Systems/System.Embedded.1/Storage/{1}/Controllers/{1}/Settings".format(idrac_ip, args["change_controller_mode"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: PATCH command passed to change controller %s boot mode to %s" % (args["change_controller_mode"], args["mode"]))
    else:
        logging.error("\n- FAIL, PATCH command failed, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- PATCH command failure:\n %s" % data)
        sys.exit(1)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(1)
    logging.info("- PASS, config job ID %s successfully created" % job_id)
    
def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(1)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(5)
            count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, config job ID marked as scheduled, job will execute on next server manual reboot")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s\n" % data['Message'].strip("."))

def loop_job_status_final():
    start_time = datetime.now()
    count = 10 
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(1)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(10)
            count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % statusCode)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(1)
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit(1)
        elif "fail" in data['Message'].lower() or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
            sys.exit(1)
        elif data['JobState'] == "Completed":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to gracefully power OFF server")
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(60)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(1)
        while True:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                if args["x"]:
                    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("- PASS, POST command passed to perform forced shutdown")
                    time.sleep(60)
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        logging.info("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        logging.error("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit(1)    
            else:
                continue 
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to power ON server")
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(1)
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, Command passed to power ON server, code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(1)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(1)

def validate_controller_mode_job_completion():
    if args["x"]:
        response = requests.get('https://{0}/redfish/v1/Systems/System.Embedded.1/Storage/{1}/Controllers/{1}?$select=Oem/Dell/DellStorageController/ControllerMode'.format(idrac_ip, args["change_controller_mode"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://{0}/redfish/v1/Systems/System.Embedded.1/Storage/{1}/Controllers/{1}?$select=Oem/Dell/DellStorageController/ControllerMode'.format(idrac_ip, args["change_controller_mode"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, status code %s returned for GET request, error details:\n" % response.status_code)
        print(data)
        sys.exit(0)
    if data["Oem"]["Dell"]["DellStorageController"]["ControllerMode"] == args["mode"]:
        logging.info("\n- PASS, confirmed controller %s mode successfully set to %s" % (args["change_controller_mode"], args["mode"]))
    else:
        logging.error("\n- FAIL, controller %s mode not set to %s, current mode: %s" % (args["change_controller_mode"], args["mode"], data["Oem"]["Dell"]["DellStorageController"]["ControllerMode"]))
        sys.exit(1)

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
    if args["get_controllers"]:
        get_storage_controllers()
    elif args["get_controller_mode"]:
        get_controller_mode()
    elif args["change_controller_mode"] and args["mode"]:
        change_controller_mode()
        if args["reboot"]:
            reboot_server()
            loop_job_status_final()
            validate_controller_mode_job_completion()
        else:
            get_job_status_scheduled()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

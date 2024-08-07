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

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to schedule a repository update at a future reoccurrence date time.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current repository update schedule details.',action="store_true", required=False)
parser.add_argument('--get-idrac-time', help='Get current repository update schedule details.',action="store_true", dest="get_idrac_time", required=False)
parser.add_argument('--clear', help='Clear repository update schedule.',action="store_true", required=False)
parser.add_argument('--set', help='Set auto SupportAssist collection schedule.',action="store_true", required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS. NOTE: For HTTP/HTTPS, recommended to use either IIS or Apache.', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the auth username for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled', required=False)
parser.add_argument('--password', help='Pass in the auth username password for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--time', help='Set repository update schedule, pass in time value. Value format: HH:MM, example: \"06:00\"',required=False)
parser.add_argument('--repeat', help='Specify the number of recurrences of the repository update schedule. Possible values are 1-366.',required=False)
parser.add_argument('--dayofweek', help='Specify day of week on which the update is scheduled. The possible values are * (Any), Mon, Tue, Wed, Thu, Fri, Sat, Sun. The default value is *.',required=False)
parser.add_argument('--dayofmonth', help='Specify day of month on which the update is scheduled. The possible values are * (Any) or a number between 1-28. The default value is *.',required=False)
parser.add_argument('--weekofmonth', help='Specify week of the month in which the update is scheduled. The possible values are * (Any) or a number between 1 and 4. The default value is *.',required=False)
parser.add_argument('--apply-reboot', help='Reboot the server immediately to run any scheduled updates detected which need a server reboot to apply. Supported values: NoReboot and RebootRequired',dest="apply_reboot", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ScheduleRepositoryUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return current repository update schedule details.
    \n- ScheduleRepositoryUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear, this example will clear current repository update schedule.
    \n- ScheduleRepositoryUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin --set --shareip 192.168.0.130 --sharename nfs/T360_repo_new --sharetype NFS --time 12:40 --repeat 1 --apply-reboot RebootRequired, this example using NFS share will create a repository update job to run at 12:40 today and once the repo update job runs and completes, a new schedule repo update job will get created and scheduled to run tomorrow at 12:40.
    \n- ScheduleRepositoryUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin --set --shareip 192.168.0.120 --sharename http_share/T360_repo_new --sharetype HTTP --time 23:00 --repeat 5 --apply-reboot RebootRequired --dayofweek Mon, this example using HTTP share will run scheduled repository update for the next 5 Mondays at 23:00.""")
    sys.exit(0)

def check_supported_idrac_version():
    supported = ""
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.error("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "SupportAssistCollection" in i:
            supported = "yes"
    if supported == "no":
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    payload = {"GetRequest":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.debug("\n- PASS: POST command passed for %s action GET iDRAC time, status code 200 returned\n" % method)
    else:
        logging.error("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("\n- INFO, current iDRAC date/time: %s" % data["TimeData"])

def get_repository_update_schedule_details():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetUpdateSchedule' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to get scheduled repository update details\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
    for i in data.items():
        if "ExtendedInfo" not in i[0]:
            print("%s: %s" % (i[0], i[1]))

def clear_repository_update_schedule_details():
    # Disable auto update feature using PATCH
    url = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"LCAttributes.1.AutoUpdate":"Disabled"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.debug("\n- PASS, PATCH command passed to successfully disable auto update attribute")
    else:
        logging.error("\n- FAIL, PATCH ommand failed to disable auto update attribute, status code %s returned\n" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    # Clear repository update schedule using POST call. Note this command will pass even if a scheduled update is not detected.
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.ClearUpdateSchedule' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to clear scheduled repository update\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)

def set_repository_update_schedule():
    # Enable auto update feature using PATCH
    url = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"LCAttributes.1.AutoUpdate":"Enabled"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.debug("\n- PASS, PATCH command passed to successfully enable auto update attribute")
    else:
        logging.error("\n- FAIL, PATCH ommand failed to enable auto update attribute, status code %s returned\n" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    # create respository update schedule using POST
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.SetUpdateSchedule' % (idrac_ip)
    payload = {}
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
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    if args["time"]:
        payload["Time"] = args["time"]
    if args["repeat"]:
        payload["Repeat"] = int(args["repeat"])
    if args["dayofweek"]:
        payload["DayofWeek"] = args["dayofweek"]
    if args["dayofmonth"]:
        payload["DayofMonth"] = int(args["dayofmonth"])
    if args["weekofmonth"]:
        payload["WeekofMonth"] = int(args["weekofmonth"])
    if args["apply_reboot"]:
        payload["ApplyReboot"] = args["apply_reboot"] 
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, POST command passed to create scheduled repository update\n")
    else:
        logging.error("\n- ERROR, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
            
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
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
        get_repository_update_schedule_details()
    elif args["clear"]:
        clear_repository_update_schedule_details()
    elif args["get_idrac_time"]:
        get_idrac_time()
    elif args["set"] and args["repeat"] and args["time"] or args["apply_reboot"]:
        set_repository_update_schedule()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

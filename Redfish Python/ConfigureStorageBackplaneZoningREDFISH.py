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

parser=argparse.ArgumentParser(description="Python script using Redfish API to configure storage backplane zoning. Backplane zoning is the process of split the current backplane into two backplanes. Note this feature is only supported on x24 backplanes and must have either PERC or HBA controller(s) connected to the backplane. Note power cycle of the server is required to apply the new backplane zone setting. ")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-enclosures', help='Get current supported storage enclosures which support zoning. If supported enclosure(s) are detected current setting and possible zoning values will also be returned. Note if you have two controllers connected to x24 backplane you will see two supported enclosures detected and you only need to use one enclosure FQDD to change backplane zone.', action="store_true", dest="get_enclosures", required=False)
parser.add_argument('--set-zone', help='Set backplane zone pass in storage enclosure FQDD.', dest="set_zone", required=False)
parser.add_argument('--value', help='Pass in backplane zone value you want to apply.', required=False)
parser.add_argument('--no-powercycle', help='Pass in this argument if you do not want to powercycle the server now to apply the new backplane zone. Note new zone will get applied to the backplane on next server powercycle. Note graceful restart or warm reboot will not apply the new backplane zone setting.', dest="no_powercycle", action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ConfigureStorageBackplaneZoningREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651bbf --get-enclosures, this example will return current supported storage enclosures which support zoning.
    \n- ConfigureStorageBackplaneZoningREDFISH.py -ip 192.168.0.120 -u root -p calvin --set-zone Enclosure.Internal.0-1:RAID.SL.3-1 --value SplitMode-4:20, this example will set new backplane zone to SplitMode-4:20, powercycle will be performed immediately to apply the new zone.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_storage_enclosures():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get chassis storage enclosures, status code %s returned" % response.status_code)
        sys.exit(0)
    enclosure_list = []
    if data["Members"] == []:
        logging.warning("\n- WARNING, empty Members list detected for Chassis schema")
        sys.exit(0)
    for i in data['Members']:
        enclosure_list.append(i['@odata.id'].split("/")[-1])
    enclosure_list.remove("System.Embedded.1")
    if enclosure_list == []:
        logging.warning("\n- WARNING, no storage enclosures detected for this server")
        sys.exit(0)
    supported_backplanes = "no"
    for i in enclosure_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Chassis/%s' % (idrac_ip, i),verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Chassis/%s' % (idrac_ip, i),verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.warning("\n- WARNING, GET request failed to get chassis storage enclosure details, status code %s returned" % response.status_code)
            sys.exit(0)
        if "pcie" not in data["Description"].lower() and data["Oem"]["Dell"]["DellChassisEnclosure"]["BackplaneType"] == "Shared":
            logging.info("\n- INFO, enclosure \"%s\" detected supports backplane zoning" % i)
            print("- Current backplane zone setting: %s" % data["Oem"]["Dell"]["DellChassisEnclosure"]["RAIDEnclosureConfigMode"])
            print("- Possible backplane zone values: %s" % data["Oem"]["Dell"]["DellChassisEnclosure"]["RAIDEnclosureConfigMode@Redfish.AllowableValues"])
            supported_backplanes = "yes"
    if supported_backplanes == "no":
        logging.warning("\n- WARNING, no supported zoning storage enclosures detected")
                

def change_backplane_zone():
    global job_id
    url = "https://%s/redfish/v1/Chassis/%s/Settings" % (idrac_ip, args["set_zone"])
    payload = {"Oem":{"Dell":{"DellChassisEnclosure":{"RAIDEnclosureConfigMode":args["value"]}}},"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.info("\n- PASS: PATCH command passed to change backplane zone setting, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to change backplane zone setting, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- Detailed failure results:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, config job ID %s successfully created" % job_id)
    
def loop_job_status_final():
    start_time = datetime.now()
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % statusCode)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:30:00":
            logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped. Check iDRAC job queue and LC logs for more details\n")
            sys.exit(0)
        elif "fail" in data['Message'].lower() or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            logging.info("- PASS, %s successfully marked completed" % job_id)
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def reboot_server():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': 'PowerCycle'}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("- PASS, POST command passed to power cycle the server")
    else:
        logging.error("\n- FAIL, POST command failed to power cycle server, status code %s returned\n" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
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
    if args["get_enclosures"]:
        get_storage_enclosures()
    elif args["set_zone"] and args["value"]:
        change_backplane_zone()
        loop_job_status_final()
        if args["no_powercycle"]:
            logging.info("\n- INFO, user selected to not powercycle the server now. New backplane zone setting will get applied on next server powercycle")
        else:
            logging.info("- INFO, server will now perform power cycle to apply new backplane zone")
            reboot_server()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# DeleteVirtualDiskREDFISH. Python script using Redfish API to either get controllers / current virtual disks or delete virtual disk.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
#
# Copyright (c) 2018, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / current virtual disks or delete virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--get-virtualdisk-details', help='Get complete details for all virtual disks behind storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisk_details", required=False)
parser.add_argument('--delete', help='Pass in virtual disk FQDD to delete virtual disk, Example "\Disk.Virtual.0:RAID.Mezzanine.1-1\"', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- DeleteVirtualDiskREDFISH.py -ip 192.168.0.120 -x 3fe2401de68b718b5ce2761cb0651aac --get-controllers, this example using iDRAC X-auth token session will return controller FQDDs.
    \n- DeleteVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-virtualdisks, this example will return current virtual disks for storage RAID.Integrated.1-1.
    \n- DeleteVirtualDiskREDFISH.py -ip 192.168.0.120 -u root --delete Disk.Virtual.2:RAID.Mezzanine.1-1, this example will first prompt to enter iDRAC user password, then delete virtual disk 2.""")
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
        sys.exit(0)

def get_storage_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_virtual_disks():
    test_valid_controller_FQDD_string(args["get_virtualdisks"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        logging.warning("\n- WARNING, no volume(s) detected for %s" % args["get_virtualdisks"])
        sys.exit(0)
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    logging.info("\n- Volume(s) detected for %s controller -\n" % args["get_virtualdisks"])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))

def get_virtual_disks_details():
    test_valid_controller_FQDD_string(args["get_virtualdisk_details"])
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisk_details"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisk_details"]),verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list = []
    if data['Members'] == []:
        logging.error("\n- WARNING, no volume(s) detected for %s" % args["get_virtualdisk_details"])
        sys.exit(0)
    else:
        logging.info("\n- Volume(s) detected for %s controller -\n" % args["get_virtualdisk_details"])
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
            print(i['@odata.id'].split("/")[-1])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        logging.info("\n----- Detailed Volume information for %s -----\n" % ii)
        for i in data.items():
            pprint(i)
        print("\n")

def delete_vd():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        logging.info("\n- PASS: DELETE command passed to delete \"%s\" virtual disk, status code 202 returned" % args["delete"])
    else:
        logging.error("\n- FAIL, DELETE command failed, status code is %s" % response.status_code)
        data = response.json()
        logging.error("\n- DELETE command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)   
    retry_count = 1
    while True:
        if retry_count == 5:
            logging.error("- WARNING, retry count of 5 has been hit to determine job type. Manually check the job queue for job status")
            sys.exit(0)
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if "JobType" not in data.keys():
            logging.error("- WARNING, unable to determine job type, retry in 10 seconds")
            time.sleep(10)
            retry_count += 1
            continue
        if data['JobType'] == "RAIDConfiguration":
            job_type = "staged"
            logging.info("- PASS, staged job ID \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
            break
        elif data['JobType'] == "RealTimeNoRebootConfiguration":
            job_type = "realtime"
            logging.info("- PASS, realtime job ID \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
            break

def get_job_status_scheduled():
    retry_count = 0
    while True:
        if retry_count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(5)
            retry_count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, staged config job marked as scheduled, rebooting the system")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s\n" % data['Message'].strip("."))

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 0
    while True:
        if retry_count == 10:
            logging.error("- FAIL, GET job status retry count of 10 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.error("\n- WARNING, GET request failed to check job status, retry again")
            time.sleep(5)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job not completed, current status: \"%s\"" % data['Message'].strip("."))
            time.sleep(10)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- INFO, Current server power state is: %s" % data['PowerState'])
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
            logging.info("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % response.status_code)
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
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
                    logging.info("- PASS, POST command passed to perform forced shutdown, status code return is %s" % response.status_code)
                    time.sleep(15)
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
                        sys.exit(0)    
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
            logging.info("- PASS, Command passed to power ON server, status code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
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
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(0)
        
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip=args["ip"]
        idrac_username=args["u"]
        if args["p"]:
            idrac_password=args["p"]
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
    elif args["get_virtualdisks"]:
        get_virtual_disks()
    elif args["get_virtualdisk_details"]:
        get_virtual_disks_details()
    elif args["delete"]:
        delete_vd()
        if job_type == "realtime":
            loop_job_status_final()
        elif job_type == "staged":
            get_job_status_scheduled()
            reboot_server()
            loop_job_status_final()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

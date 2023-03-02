#!/usr/bin/python3
#
# SystemEraseREDFISH. Python script using Redfish API with OEM extension to perform iDRAC System Erase feature.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
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
import os
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform System Erase feature. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get', help='Get supported System Erase components to pass in for --erase argument', action="store_true", required=False)
parser.add_argument('--erase', help='Pass in the system erase component(s) you want to erase. If passing in multiple components, make sure to use comma separator. Example: BIOS,IDRAC,DIAG. NOTE: These values are case sensitive, make sure to pass in exact string values you get from -g argument.', required=False)
parser.add_argument('--poweron', help='Pass in this argument if you want the server to automatically power ON after system erase process is complete/iDRAC reboot. By default, once the system erase process is complete, server will be in OFF state, reboot the iDRAC and stay in OFF state.', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get supported component values which can be passed in for System Erase action.
    \n- SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin --erase DIAG,DrvPack, this example wil erase diag and driver pack, leave server in OFF state.
    \n- SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin --erase BIOS --poweron, this example will reset BIOS to default settings and power back ON the server.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def get_components():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get supported component values,status code %s returned" % response.status_code)
        sys.exit()
    logging.info("\n- Supported component values for System Erase operation -\n")
    for i in data['Actions']['#DellLCService.SystemErase']['Component@Redfish.AllowableValues']:
        if i == "BIOS":
            print("BIOS: \"Reset BIOS to default configuration settings\"")
        elif i == "DIAG":
            print("DIAG: \"Delete only DIAG firmware image stored on iDRAC\"")
        elif i == "DrvPack":
            print("DrvPack: \"Delete only Driver Pack firmware image stored on iDRAC\"")
        elif i == "IDRAC":
            print("IDRAC: \"Reset iDRAC to default settings\"")
        elif i == "LCData":
            print("LCData: \"Delete Lifecycle Controller data(clears: Lifecycle logs, LC inventory, any rollback firmware packages stored on iDRAC)\"")
        elif i == "NonVolatileMemory":
            print("NonVolatileMemory: \"Erase NVDIMM devices\"")
        elif i == "OverwritePD":
            print("OverwritePD: \"Erase non ISE HDD devices\"")
        elif i == "CryptographicErasePD":
            print("CryptographicErasePD: \"Erase ISE/SED/NVMe devices\"")
        elif i == "PERCNVCache":
            print("PERCNVCache: \"Erase pinned cache on the PERC controller\"")
        elif i == "CryptographicErasePD":
            print("CryptographicErasePD: \"Erase ISE/SED/NVMe devices\"")
        elif i == "vFlash":
            print("vFlash: \"Erase iDRAC vFlash card\"")
        elif i == "AllApps":
            print("AllApps: \"Delete DIAG/Driver Pack firmware images and SupportAssist related non-volatile storage\"")
        else:
            print(i)

def system_erase():
    global job_id
    global method
    method = "SystemErase"
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SystemErase' % (idrac_ip)    
    if "," in args["erase"]:
        component_list =args["erase"].split(",")
        payload={"Component":component_list}
    else:
        payload={"Component":[args["erase"]]}
    logging.info("\n- INFO, component(s) selected for System Erase operation -\n")
    for i in payload["Component"]:
        print(i)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("- PASS, job ID %s successfuly created for %s method. Script will now loop polling job status until marked completed\n" % (job_id, method))    

def loop_job_status():
    start_time = datetime.now()
    count_number = 0
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, JobStatus not completed, current status: \"%s\"" % (data['Message']))
    start_job_status_message = data['Message']
    retry_count = 1
    while True:
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except:
            if retry_count == 10:
                logging.info("- INFO, retry count of 10 has been reached to communicate with iDRAC, script will exit")
                sys.exit(0)
            else:
                logging.info("- INFO, lost iDRAC network connection, retry GET request after 10 second sleep delay")
                retry_count += 1
                time.sleep(15)
                continue
        current_time = (datetime.now()-start_time)
        if response.status_code == 200:
            current_job_status = data['Message']
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            sys.exit(0)
        data = response.json()
        new_job_status_message = data['Message']
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit(0)
        elif data['JobState'] == "Failed" or "fail" in data['Message'].lower() or "unable" in data['Message'].lower() or "invalid" in data['Message'].lower() or "cannot" in data['Message'].lower():
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['Message'] == "Job completed successfully.":
            logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            logging.info("\n- INFO, server is in OFF state due to System Erase process completed, iDRAC will now reboot.")
            if args["poweron"]:
                if args["x"]:
                    logging.warning("- WARNING, X-auth token session was deleted due to iDRAC reboot, unable to power on server.")
                    sys.exit(0)
                logging.info("- INFO, user selected to automatically power ON the server once iDRAC reboot is complete. Script will wait 6 minutes for iDRAC to come back up and attempt to power ON the server")
                time.sleep(360)
                count = 0
                while True:
                    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                    payload = {'ResetType': 'On'}
                    headers = {'content-type': 'application/json'}
                    if "IDRAC" in args["erase"]:
                        if args["x"]:
                            logging.warning("- WARNING, X-auth token session was deleted due to iDRAC reset to default, unable to power on server.")
                            sys.exit(0)
                        logging.info("- INFO, iDRAC component selected. Default iDRAC username/password will be used to attempt power on server")
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=("root", "calvin"))
                    else:
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))   
                    if count == 5:
                        logging.error("- FAIL, 5 attempts at powering ON the server has failed, script will exit")
                        sys.exit(0)
                    if response.status_code == 204 or response.status_code == 202 or response.status_code == 200:
                        logging.info("- PASS, POST command passed to power ON server")
                        time.sleep(30)
                        if "BIOS" in args["erase"]:
                            if args["x"]:
                                logging.warning("- WARNING, X-auth token session was deleted due to iDRAC reboot, unable to power on server.")
                                sys.exit(0)
                            logging.info("- INFO, BIOS component selected. Server will power off one more time and automatically power back onto complete the process.")
                            count = 0
                            while True:
                                url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % idrac_ip
                                payload = {}
                                headers = {'content-type': 'application/json'}
                                if "IDRAC" in args["erase"]:
                                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=("root","calvin"))
                                else:
                                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))    
                                statusCode = response.status_code
                                data = response.json()
                                if response.status_code == 204 or response.status_code == 202 or response.status_code == 200:
                                    logging.info("- PASS, POST command passed to get server status")
                                else:
                                    logging.error("- FAIL, unable to get current server status, status code %s returned." % response.status_code)
                                    logging.error("- Detailed error message: %s" % data)
                                    sys.exit(0)
                                if data['ServerStatus'] == "PoweredOff":
                                    logging.info("- PASS, verified server is in OFF state, executing power ON operation")
                                    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                                    payload = {'ResetType': 'On'}
                                    headers = {'content-type': 'application/json'}
                                    if "IDRAC" in args["erase"]:
                                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=("root","calvin"))
                                    else:
                                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))    
                                    statusCode = response.status_code
                                    if statusCode == 204 or statusCode == 202 or statusCode == 200:
                                        logging.info("- PASS, POST command passed to power ON server")
                                        return
                                    else:
                                        logging.error("- FAIL, unable to power ON server, status code return is %s" %response.status_code)
                                        logging.error("- Detailed error message: %s" % data)
                                        sys.exit(0)
                                elif count == 10:
                                    logging.info("- INFO, server still in POST/ON state after 10 attempts checking power state. Check the iDRAC Lifecycle logs, server to debug issue")
                                    sys.exit(0)
                                else:
                                    logging.info("- INFO, server still in POST/ON state, waiting for server to power down before executing power ON operation")
                                    time.sleep(60)
                                    count += 1   
                        else:
                            return
                    else:
                        logging.info("\n- FAIL, POST command failed to power ON server, status code: %s\n" % response.status_code)
                        logging.info("Extended Info Message: {0}".format(response.json()))
                        logging.info("- INFO, script will wait 1 minute and attempt power ON operation again")
                        time.sleep(60)
                        count += 1
                        continue
            else:
                if "BIOS" in args["erase"]:
                    logging.error("- INFO, BIOS component selected. Manually power on the server for BIOS to complete reset to defaults. Server will power off one more time, process is complete.")
                    return
                else:
                    return
        else:
            if start_job_status_message != new_job_status_message:
                logging.info("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
                start_job_status_message = new_job_status_message
            continue
            
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
    if args["erase"]:
        system_erase()
        loop_job_status()
    elif args["get"]:
        get_components()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

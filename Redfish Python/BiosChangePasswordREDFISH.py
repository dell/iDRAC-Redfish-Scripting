#!/usr/bin/python3
#
# BiosChangePasswordREDFISH. Python script using Redfish API to set / change or delete either BIOS setup or system password
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to set, change or delete either BIOS setup or system password")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--type', help='Set, Change or Delete BIOS password, pass in the type of password you want to change. Pass in \"1\" for System password, \"2" for Setup password, \"3\" for PersistentMemPassphrase', required=False)
parser.add_argument('--old', help='Change BIOS password, pass in the old password. If you are setting new password, pass in \"\" for --old argument', required=False)
parser.add_argument('--new', help='Change BIOS password, pass in the new password. If you are clearing the password, pass in \"\" for --new argument', required=False)
parser.add_argument('--noreboot', help='Pass in this argument to NOT auto reboot the server to change BIOS password. Job will still be scheduled and execute on next server manual reboot.', action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 1 --old "" --new "p@ssw0rd", this example will reboot the server now to set BIOS system password.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root --type 1 --old "" --new "p@ssw0rd" --noreboot, this example will first prompt to enter iDRAC user password, then create config job to set BIOS system password but not auto reboot the server to apply the job.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 1 --old "p@ssw0rd" --new "newpwd", this example will reboot the server now to change BIOS system password.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 2 --old "p@ssw0rd" --new "", this example will reboot the server now to clear BIOS setup password.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 1 --old "", this example will prompt to the screen to enter BIOS system password to set, reboot server now to apply.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 1, this example will prompt to the screen to enter current BIOS system password, then prompt to enter new system password to set, reboot server now to apply.
    \n- BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin --type 1 --new "", this example will prompt to the screen to enter current BIOS system password, then clear it, reboot server now to apply.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def change_bios_password():
    if args["type"] == "1":
        password_name = "SysPassword"
    elif args["type"] == "2":
        password_name = "SetupPassword"
    elif args["type"] == "3":
        password_name = "PersistentMemPassphrase"
    else:
        logging.error("\n- FAIL, invalid value passed in for -c option")
        sys.exit(0)
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ChangePassword" % idrac_ip
    if args["new"] == "":
        if not args["old"]:
            args["old"] = getpass.getpass("\n- Argument --old not detected, pass in old(current) BIOS password: ")
        payload = {"PasswordName":password_name,"OldPassword":args["old"],"NewPassword":""}
        logging.info("\n- INFO, clearing BIOS %s" % password_name)
    elif args["old"] == "":
        if not args["new"]:
            args["new"] = getpass.getpass("\n- Argument --new not detected, pass in new BIOS password: ")
        payload = {"PasswordName":password_name,"":args["old"],"NewPassword":args["new"]}
        logging.info("\n- INFO, setting new BIOS %s" % password_name)
    elif args["new"] == "":
        if not args["old"]:
            args["old"] = getpass.getpass("\n- Argument --old not detected, pass in old(current) BIOS password: ")
        payload = {"PasswordName":password_name,"":args["old"],"NewPassword":args["new"]}
        logging.info("\n- INFO, deleting BIOS %s" % password_name)
    elif not args["new"] and not args["old"]:
        args["old"] = getpass.getpass("\n- Argument --old not detected, pass in old(current) BIOS password: ")
        args["new"] = getpass.getpass("\n- Argument --new not detected, pass in new BIOS password: ")
        payload = {"PasswordName":password_name,"":args["old"],"NewPassword":args["new"]}
        logging.info("\n- INFO, changing BIOS %s" % password_name)
    else:
        payload = {"PasswordName":password_name,"OldPassword":args["old"],"NewPassword":args["new"]}
        logging.info("- INFO, changing BIOS %s" % password_name)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.__dict__
    if response.status_code == 200:
        logging.info("\n- PASS: status code %s returned for POST action Bios.ChangePassword" % response.status_code)
    else:
        logging.error("\n- FAIL, Command failed, errror code is %s" % response.status_code)
        detail_message = str(response.__dict__)
        logging.info(detail_message)
        sys.exit(0)
    
def create_bios_config_job():
    global job_id
    global start_time
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("- PASS: POST command passed to create target config job, status code %s returned." % response.status_code)
    else:
        logging.error("\n- FAIL, Command failed, status code is %s\n" % response.status_code)
        detail_message = str(response.__dict__)
        logging.error(detail_message)
        sys.exit(0)
    create_dict = str(response.__dict__)
    job_id_search = re.search("JID_.+?,",create_dict).group()
    job_id = re.sub("[,']","",job_id_search)
    logging.info("- INFO: %s job ID successfully created" % job_id)
    start_time = datetime.now()

def check_schedule_job_status():
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        time.sleep(10)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])
            time.sleep(5)
                                                                          
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
            elif current_time >= "0:05:00":
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

def check_job_status_final():
    if args["type"] == "1":
        logging.info("\n- INFO, BIOS system password config job detected. If setting new or changing BIOS system password, server will halt during POST prompting to enter password. System password must be entered for POST to complete, mark the job completed\n") 
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "0:50:00":
            logging.error("\n- FAIL: Timeout of 50 minutes has been hit, script stopped\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            logging.error("- FAIL: %s failed" % job_id)
            sys.exit(0)
        elif data['Message'] == "Job completed successfully.":
            logging.info("\n- Final detailed job results -\n")
            pprint(data)
            break
        else:
            logging.info("- INFO, job status not complete, current status: \"%s\"" % data['Message'])
            time.sleep(30)
            
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
    if args["type"]:
        change_bios_password()
        create_bios_config_job()
        check_schedule_job_status()
        if args["noreboot"]:
            logging.info("\n- INFO, --noreboot argument detected, config job is still scheduled and will execute on next server manual reboot")
            sys.exit(0)
        else:
            reboot_server()
            check_job_status_final()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)

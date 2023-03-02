#!/usr/bin/python3
#
# RunDiagnosticsREDFISH. Python script using Redfish API with OEM extension to run remote diagnostics on the server.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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
import re
import requests
import sys
import time
import warnings
import webbrowser

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to run remote diagnostics on the server.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--reboot-type', help='Pass in the reboot job type. Pass in \"0\" for GracefulRebootWithForcedShutdown, \"1\" for GracefulRebootWithoutForcedShutdown or \"2\" for Powercycle (forced)', dest="reboot_type", required=False)
parser.add_argument('--runmode', help='Pass in the run mode type you want to execute for diags. Pass in \"0\" for Express only, \"1\" for Express and Extended or \"2\" for Extended only. Note: Run express diags, average completion time: 15-30 minutes. Run extended diags, average completion time: 3-5 hours but timings will vary based on your server configuration.', required=False)
parser.add_argument('--export', help='Export diags results, pass in 1 for local, 2 for NFS, 3 for CIFS, 4 for HTTP or 5 for HTTPS. If using network share, you will need to also use IP address, sharename, sharetype, username, password arguments.', required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username password', required=False)
parser.add_argument('--filename', help='Pass in unique filename for the diags results', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin --reboot-type 2 --runmode 0, this example will perform forced server reboot and run express diagnostics.
    \n- RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin --reboot-type 1 --runmode 2, this example will perform graceful without forced server reboot, run extended diagnostics.
    \n- RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin --export 1, this example will export the DIAGs results locally using your default browser.
    \n- RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin --export 2 --shareip 192.168.0.130 --sharename /nfs --filename diags.log, this example will export DIAGs results to NFS share.""")
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

def export_diags():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportePSADiagnosticsResult' % (idrac_ip)
    method = "ExportePSADiagnosticsResult"
    payload = {}
    if args["export"] == "1":
        payload["ShareType"] = "Local"
    if args["export"] == "2":
        payload["ShareType"] = "NFS"
    if args["export"] == "3":
        payload["ShareType"] = "CIFS"
    if args["export"] == "4":
        payload["ShareType"] = "HTTP"
    if args["export"] == "5":
        payload["ShareType"] = "HTTPS"
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["filename"]:
            payload["FileName"] = args["filename"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertificateWarning"] = args["ignorecertwarning"]   
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
    if args["export"] == "1":
        if response.headers['Location'] == "/redfish/v1/Dell/diags.txt" or response.headers['Location'] == "/redfish/v1/Oem/Dell/diags.txt":
            python_version = sys.version_info
            while True:
                if python_version.major <= 2:
                    request = raw_input("\n- INFO, use browser session to view diags text file? Type \"y\" or \"n\": ")
                elif python_version.major >= 3:
                    request = input("\n- INFO, use browser session to view diags text file? Type \"y\" or \"n\": ")
                else:
                    logging.error("- FAIL, unable to get current python version, manually run GET on URI \"%s\" to view diags text file" % response.headers['Location'])
                    sys.exit(0)
                if str(request).lower() == "y":
                    webbrowser.open('https://%s%s' % (idrac_ip, response.headers['Location']))
                    logging.info("\n- INFO, check you default browser session to view diags text file.")
                    return
                elif str(request).lower() == "n":
                    sys.exit(0)
                else:
                    logging.error("- FAIL, incorrect value passed in for request, try again")
                    continue
    else:
        data = response.json()
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            sys.exit(0)
        logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
        loop_job_status()

def run_remote_diags():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.RunePSADiagnostics' % (idrac_ip)
    method = "RunePSADiagnostics"
    payload={}
    if args["reboot_type"]:
        if args["reboot_type"] == "0":
            payload["RebootJobType"] = "GracefulRebootWithForcedShutdown"
        elif args["reboot_type"] == "1":
            payload["RebootJobType"] = "GracefulRebootWithoutForcedShutdown"
        elif args["reboot_type"] == "2":
            payload["RebootJobType"] = "PowerCycle"
        else:
            logging.error("- FAIL, invalid value entered for --reboot-type argument")
            sys.exit(0)
    if args["runmode"]:
        if args["runmode"] == "0":
            payload["RunMode"] = "Express"
        elif args["runmode"] == "1":
            payload["RunMode"] = "ExpressAndExtended"
        elif args["runmode"] == "2":
            payload["RunMode"] = "Extended"
        else:
            logging.error("- FAIL, invalid value entered for --runmode argument")
            sys.exit(0)
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
    logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
    
def loop_job_status():
    start_time = datetime.now()
    if args["export"]:
        logging.info("- INFO, script will loop checking job status until marked completed")
    else:
        logging.info("- INFO, server will now automatically reboot and run remote diagnostics once POST completes. Script will check job status every 1 minute until marked completed\n")
        time.sleep(10)
    while True:
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            if "Max retries exceeded with url" in str(error_message):
                logging.warning("- WARNING, max retries exceeded with URL error detected, retry GET command")
                time.sleep(10)
                continue
            else:
                logging.warning("- WARNING, GET command failed to get job status, script will exit")
                sys.exit(0)   
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        max_timeout = "10:00:00"
        if str(current_time)[0:7] >= max_timeout and len(str(current_time)[0:7]) == len(max_timeout):
            logging.error("\n- FAIL: Timeout of 10 hours has been hit, script stopped. Check iDRAC LC logs or Job Queue to debug.\n")
            sys.exit(0)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
            logging.error("- FAIL: job ID %s failed, failed message: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "Job completed successfully." or data['Message'] == "Successfully exported the ePSA Diagnostics results.":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                pprint(i)
            break
        else:
            logging.info("- INFO, job not marked completed, status running, execution time: %s" % str(current_time)[0:7])
            if args["export"]:
                continue
            else:
                time.sleep(60)
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
    if args["export"]:
        export_diags()
    elif args["runmode"] and args["reboot_type"]:
        run_remote_diags()
        loop_job_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

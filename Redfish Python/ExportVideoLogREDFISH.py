#!/usr/bin/python3
#
# ExportVideoLogREDFISH. Python script using Redfish API with OEM extension to export either boot capture videos or crash capture video locally.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
import requests
import os
import sys
import time
import warnings
import webbrowser

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export either boot capture videos or crash capture video locally. NOTE: iDRAC downloads boot capture videos locally in a zip file using your default browser.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--filetype', help='Pass in the filetype to export locally. Supported values: 1 and 2. Pass in 1 for BootCaptureVideo or 2 for CrashCaptureVideo. Note: script will prompt you to save the zip file locally using your default browser. Extract the video files(dvc format) from the zip to view them.', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportVideoLogEDFISH.py -ip 192.168.0.120 -u root -p calvin --filetype 1, this example will download iDRAC boot capture videos locally in a zip file using your default browser.""")
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

def export_video_log():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportVideoLog' % (idrac_ip)
    method = "ExportVideoLog"
    logging.info("\n- INFO, collecting video capture logs, this may take 15-30 seconds to complete")
    payload={"ShareType":"Local"}
    if args["filetype"] == "1":
        payload["FileType"] = "BootCaptureVideo"
    elif args["filetype"] == "2":
        payload["FileType"] = "CrashCaptureVideo"
    else:
        logging.error("\n- FAIL, invalid value passed in for argument --filetype")
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
        python_version = sys.version_info
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    time.sleep(10)
    try:
        video_log_capture_zip_uri = response.headers['Location']
    except:
        logging.error("- FAIL, unable to locate video capture URI in POST headers output")
        sys.exit(0)
    while True:
        if python_version.major <= 2:
            request = raw_input("\n* Would you like to open browser session to download video capture zip file? Type \"y\" to download or \"n\" to not download: ")
        elif python_version.major >= 3:
            request = input("\n* Would you like to open browser session to download video capture zip file? Type \"y\" to download or \"n\" to not download: ")
        else:
            logging.error("- FAIL, unable to get current python version, manually run GET on URI \"%s\" to download exported hardware inventory file" % response.headers['Location'])
            sys.exit(0)
        if request.lower() == "y":
            webbrowser.open('https://%s%s' % (idrac_ip, video_log_capture_zip_uri))
            logging.info("\n- INFO, check you default browser session for downloaded video capture zip file. If needed to watch the video capture files(dvc format), download the video player from the iDRAC GUI/Maintenance/Troubleshooting page.")
            break
        elif request.lower() == "n":
            break
        else:
            logging.error("\n- FAIL, incorrect value passed in for request, try again")
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
    if args["filetype"]:
        export_video_log()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

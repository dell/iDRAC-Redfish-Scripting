#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import csv
import getpass
import json
import logging
import os
import re
import requests
import subprocess
import sys
import time
import warnings
import webbrowser

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to launch iDRAC virtual KVM session using a browser session.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--browser', help='Pass in browser type to launch virtual KVM session, supported values are chrome, edge and firefox. Note if this argument is not passed in KVM session will launch using default browser configured.', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- LaunchIdracRemoteKvmHtmlSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will launch iDRAC virtual KVM session using default browser.
    \n- LaunchIdracRemoteKvmHtmlSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin --browser chrome, this example will launch iDRAC virtual KVM session using Chrome browser.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.error("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    if "#DelliDRACCardService.GetKVMSession" not in data['Actions'].keys():
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def create_x_auth_session():
    global x_auth_token
    global x_auth_session_uri
    url = 'https://%s/redfish/v1/SessionService/Sessions' % idrac_ip
    payload = {"UserName":idrac_username,"Password":idrac_password}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
    data = response.json()
    if response.status_code == 201:
        logging.debug("- PASS, successfully created X auth session")
    else:
        try:
            logging.error("\n- FAIL, unable to create X-auth_token session, status code %s returned, detailed error results:\n %s" % (response.status_code, data))
        except:
            logging.error("\n- FAIL, unable to create X-auth_token session, status code %s returned" % (response.status_code))
        sys.exit(0)
    x_auth_token = response.headers["X-Auth-Token"]
    x_auth_session_uri = response.headers["Location"]
        
def export_ssl_cert():
    logging.info("- INFO, exporting iDRAC SSL server cert")
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (idrac_ip)
    payload = {"SSLCertType":"Server"}
    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.debug("- INFO, POST command passed to export SSL cert")
    else:
        logging.error("\n- FAIL, POST command failed for ExportSSLCertificate action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    try:
        os.remove("ssl_cert.txt")
    except:
        logging.debug("- INFO, unable to locate ssl_cert.txt file, skipping step to delete file")
    try:
        with open("ssl_cert.txt", "w") as x:
            x.write(data['CertificateFile'])
    except:
        logging.error("- FAIL, unable to write cert contents to file")
        sys.exit(0)

def get_KVM_session_info():
    global temp_username
    global temp_password
    logging.info("- INFO, getting KVM session temporary username, password")
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.GetKVMSession' % (idrac_ip)
    payload={"SessionTypeName":"ssl_cert.txt"}
    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        logging.debug("- INFO, POST command passed to get KVM session")
    else:
        logging.error("\n- FAIL, POST command failed for GetKVMSession action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    try:
        temp_username = data["TempUsername"]
        temp_password = data["TempPassword"]
    except:
        logging.error("- FAIL, unable to locate temp username or password in JSON output")
        sys.exit(0)

def get_browser_path(browser_name):
    browser_name = browser_name.lower()
    if sys.platform.startswith("win"):
        paths = {
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe"
        }
    elif sys.platform.startswith("darwin"):
        paths = {
            "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "firefox": "/Applications/Firefox.app/Contents/MacOS/firefox"
        }
    else:
        paths = {
            "chrome": "/usr/bin/google-chrome",
            "edge": "/usr/bin/microsoft-edge",
            "firefox": "/usr/bin/firefox"
        }
    return paths.get(browser_name)

def open_url(browser_name, url):
    browser_path = get_browser_path(browser_name)
    if not browser_path or not os.path.exists(browser_path):
        logging.error("- ERROR: %s browser either not installed or is installed but not using the native installation path" % browser_name.title())
        delete_session()
        sys.exit(1)
    webbrowser.register(browser_name,None,webbrowser.BackgroundBrowser(browser_path))
    webbrowser.get(browser_name).open(url)

def launch_KVM_session():
    logging.info("- INFO, launching iDRAC KVM session using your default browser")
    uri_string = "https://%s/console?username=%s&tempUsername=%s&tempPassword=%s" % (idrac_ip, idrac_username, temp_username, temp_password)
    if args["browser"]:
        open_url(args["browser"], uri_string)
    else:
        webbrowser.open(uri_string)    
    try:
        os.remove("ssl_cert.txt")
    except:
        logging.debug("- INFO, unable to locate ssl_cert.txt file, skipping step to delete file")
    

def delete_session():
    try:
        url = 'https://%s%s' % (idrac_ip, x_auth_session_uri)
    except:
        logging.debug("- INFO, no session to delete, skipping this step")
        sys.exit(0)
    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
    response = requests.delete(url, headers=headers, verify=verify_cert)
    if response.status_code == 202 or response.status_code == 200 or response.status_code == 204:
        logging.debug("\n- PASS: DELETE command passed to delete session, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, DELETE command failed, status code returned %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- DELETE command failure:\n %s" % data)
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
    if not args["x"]:
        create_x_auth_session()
        args["x"] = x_auth_token
    export_ssl_cert()
    get_KVM_session_info()
    launch_KVM_session()
    time.sleep(10)
    delete_session()

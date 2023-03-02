#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2022, Dell, Inc.
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
import warnings

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either enable serial data capture, export serial data or clear serial data. NOTE: This feature requires iDRAC Datacenter license.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--enable', help = 'Enabled iDRAC settings to capture serial data', required = False, action='store_true')
parser.add_argument('--export', help = 'Export captured serial data locally', required = False, action='store_true')
parser.add_argument('--clear', help = 'Clear serial data stored by iDRAC', required = False, action='store_true')
parser.add_argument('--disable', help = 'Disable iDRAC settings to capture serial data', required = False, action='store_true')

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --enable, this example will enable iDRAC serial data capture.
    \n- ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --export, this example will export captured serial data.
    \n- ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --clear, this example will clear serial data.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0) 

def enable_disable_iDRAC_attributes_enable_capture_serial(attribute_setting):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"SerialCapture.1.Enable":attribute_setting}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS, PATCH command passed to %s serial data capture, status code %s returned\n" % (attribute_setting.upper().rstrip("D"), response.status_code))
        if "error" in data.keys():
            logging.warning("\n- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
            logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
    else:
        logging.error("\n- FAIL, Command failed to set attributes, status code : %s\n" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)

def export_serial_data():
    method = "SerialDataExport"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataExport' % (idrac_ip)
    payload={}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.warning("- WARNING, serial logs enabled but no serial content has been stored in iDRAC. Reboot server to start generating serial content stored in iDRAC")
        sys.exit(0)
    elif response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % response.__dict__)
        sys.exit(0)
    try:
        os.remove("serial_data_logs.txt")
    except:
        pass
    filename_open = open("serial_data_logs.txt", "w")
    dict_response = response.__dict__['_content']
    string_convert = str(dict_response)
    string_convert = string_convert.lstrip("'b")
    string_convert = string_convert.rstrip("'")
    string_convert = string_convert.split("\\n")
    for key in string_convert:
        key = key.replace("\\r", "")
        key = key.replace("\\t", "")
        filename_open.writelines(key)
        filename_open.writelines("\n")
    filename_open.close()
    logging.info("- INFO, Exported serial logs captured to file \"%s\\%s\"" % (os.getcwd(), "serial_data_logs.txt"))

def clear_serial_data():
    method = "SerialDataClear"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataClear' % (idrac_ip)
    payload={}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % response.__dict__)
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
    if args["enable"]:
        enable_disable_iDRAC_attributes_enable_capture_serial("Enabled")
    elif args["export"]:
        export_serial_data()
    elif args["clear"]:
        clear_serial_data()
    elif args["disable"]:
        enable_disable_iDRAC_attributes_enable_capture_serial("Disabled")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

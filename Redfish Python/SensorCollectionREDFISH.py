#!/usr/bin/python3
#
# SensorCollectionREDFISH. Python script using Redfish API OEM extensoion to get iDRAC sensor collection data.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2019, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API OEM extension to sensor collection data.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get-numeric', help='Get all Dell Numeric Sensor Collection data', action="store_true", required=False)
parser.add_argument('--get-power', help='Get all Dell PS(power supply) Numeric Sensor Collection data', action="store_true", required=False)
parser.add_argument('--get-status', help='Get all Dell Presence And Status Sensor Collection data', action="store_true", required=False)
parser.add_argument('--get-sensor', help='Get all Dell Sensor Collection data', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SensorCollectionREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-numeric, this example will return Dell numeric sensor data information.
    \n- SensorCollectionREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-sensor, this example will return Dell sensor data information.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellNumericSensorCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellNumericSensorCollection' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    try:
        os.remove("sensor_collection.txt")
    except:
        logging.debug("- INFO, file not detected, skipping step to delete")

def get_sensor_data():
    open_file = open("sensor_collection.txt","a")
    get_time = datetime.now()
    current_date_time = "- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (get_time.month, get_time.day, get_time.year, get_time.hour, get_time.minute, get_time.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if args["get_numeric"]:
        sensor_key = "DellNumericSensorCollection"
    elif args["get_power"]:
        sensor_key = "DellPSNumericSensorCollection"
    elif args["get_status"]:
        sensor_key = "DellPresenceAndStatusSensorCollection"
    elif args["get_sensor"]:
        sensor_key = "DellSensorCollection"
    else:
        logging.error("- FAIL, you must pass in at least one parameter to get sensor collection data")
        sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/%s' % (idrac_ip, sensor_key), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/%s' % (idrac_ip, sensor_key), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    logging.info("\n- Data collection data for \"%s\"\n" % sensor_key) 
    if data['Members'] == []:
        logging.warning("- WARNING, no data available for URI \"redfish/v1/Dell/Systems/System.Embedded.1/%s\"" % sensor_key)
        sys.exit(0)
    for i in data['Members']:
        for ii in i.items():
            sensor_entry = ("%s: %s" % (ii[0],ii[1]))
            print(sensor_entry)
            open_file.writelines("%s\n" % sensor_entry)
        print("\n")
        open_file.writelines("\n")
    if 'Members@odata.nextLink' in data:
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    open_file.close()
                    logging.info("\n- INFO, iDRAC Server Slot Information also captured in \"%s_server_slot_info.txt\" file" % idrac_ip)
                    sys.exit(0)
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            if "Members" not in data or data["Members"] == [] or response.status_code == 400:
                break
            for i in data['Members']:
                pprint(i), print("\n")
                for ii in i.items():
                    server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
                    open_file.writelines("%s\n" % server_slot_entry)
                open_file.writelines("\n")
    logging.info("\n- INFO, \"%s\" data also captured in \"sensor_collection.txt\" file" % sensor_key)
    open_file.close()
        
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
    if args["get_numeric"] or args["get_power"] or args["get_status"] or args["get_sensor"]:
        get_sensor_data()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

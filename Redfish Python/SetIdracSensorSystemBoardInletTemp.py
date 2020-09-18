#!/usr/bin/python
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get or set min/max system board inlet temps")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SetIdracSensorSystemBoardInletTemp.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get the current system board inlet temp readings. SetIdracSensorSystemBoardInletTemp.py -ip 192.168.0.120 -u root -p calvin --min 4 --max 46, this example will set both min and max inlet temp readings.') 
parser.add_argument('-g', help='get current system board inlet temp readings, pass in \"y\"', required=False)
parser.add_argument('--min', help='Pass in value to set min warning threshold (lower caution) for system board inlet temp', required=False)
parser.add_argument('--max', help='Pass in value to set max warning threshold (upper caution) for system board inlet temp', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish.")
        sys.exit()
    else:
        pass


def get_current_system_board_temps():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, GET request failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()
    else:
        print("\n- INFO, current system board inlet temp readings \n")
    for i in data["Thresholds"].items():
        print("%s: %s" % (i[0], i[1]))


def set_inlet_temp():
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp" % idrac_ip
    if args["min"]:
        print("\n- INFO, setting LowerCaution property to %s reading" % args["min"])
        payload = {"Thresholds":{"LowerCaution":{"Reading":int(args["min"])}}}
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        data = response.json()
        if statusCode == 200:
            print("- PASS, PATCH operation passed to set LowerCaution property")
        else:
            print("- FAIL, PATCH command failed to set LowerCaution property, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
            sys.exit()
    if args["max"]:
        print("\n- INFO, setting UpperCaution property to %s reading" % args["max"])
        payload = {"Thresholds":{"UpperCaution":{"Reading":int(args["max"])}}}
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        data = response.json()
        if statusCode == 200:
            print("- PASS, PATCH operation passed to set UpperCaution property")
        else:
            print("- FAIL, PATCH command failed to set UpperCaution property, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
            sys.exit()
            
       
    
            

        


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_current_system_board_temps()
    elif args["min"] or args["max"]:
        set_inlet_temp()
    else:
        print("- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")
    



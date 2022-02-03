#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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
import json
import requests
import os
import sys
import warnings

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either enable serial data capture, export serial data or clear serial data. NOTE: This feature requires iDRAC Datacenter license.")
parser.add_argument('-ip',help = 'iDRAC IP address', required = True)
parser.add_argument('-u', help = 'iDRAC username', required = True)
parser.add_argument('-p', help = 'iDRAC password', required = True)
parser.add_argument('script_examples',action = "store_true",help = 'ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin -s, this example will enable iDRAC serial data capture. ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin -e, this example will export captured serial data. ExportClearSerialDataLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin -c, this example will clear serial data.')
parser.add_argument('-s', help = 'Enabled iDRAC settings to capture serial data', required = False, action='store_true')
parser.add_argument('-e', help = 'Export captured serial data locally', required = False, action='store_true')
parser.add_argument('-c', help = 'Clear serial data stored by iDRAC', required = False, action='store_true')
parser.add_argument('-d', help = 'Disable iDRAC settings to capture serial data', required = False, action='store_true')

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def set_iDRAC_attributes_enable_capture_serial():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    headers = {'content-type': 'application/json'}
    payload = {"Attributes":{"SerialCapture.1.Enable":"Enabled","Serial.1.Enable":"Enabled"}}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS, PATCH command passed to successfully set attributes to enable serial data capture, status code %s returned\n" % response.status_code)
        if "error" in data.keys():
            print("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
            print("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            pass
    else:
        print("\n- FAIL, Command failed to set attributes, status code : %s\n" % response.status_code)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()

def export_serial_data():
    method = "SerialDataExport"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataExport' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        print("\n- POST command failure results:\n %s" % response.__dict__)
        sys.exit()
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
    print("- INFO, Exported serial logs captured to file \"%s\\%s\"" % (os.getcwd(), "serial_data_logs.txt"))

def clear_serial_data():
    method = "SerialDataClear"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/SerialInterfaces/Serial.1/Actions/Oem/DellSerialInterface.SerialDataClear' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        print("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        print("\n- POST command failure results:\n %s" % response.__dict__)
        sys.exit()

def disable_iDRAC_attributes_enable_capture_serial():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    headers = {'content-type': 'application/json'}
    payload = {"Attributes":{"SerialCapture.1.Enable":"Disabled"}}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS, PATCH command passed to successfully disable attribute for serial data capture, status code %s returned\n" % response.status_code)
        if "error" in data.keys():
            print("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
            print("\n- INFO, for attributes that detected no error, these will still get applied")
        else:
            pass
    else:
        print("\n- FAIL, Command failed to set attributes, status code : %s\n" % response.status_code)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()

if __name__ == "__main__":
    if args["s"]:
        set_iDRAC_attributes_enable_capture_serial()
    elif args["e"]:
        export_serial_data()
    elif args["c"]:
        clear_serial_data()
    elif args["d"]:
        disable_iDRAC_attributes_enable_capture_serial()
    else:
        print("- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")
    
    
        

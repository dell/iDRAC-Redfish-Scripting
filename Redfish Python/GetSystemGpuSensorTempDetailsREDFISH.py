#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2024, Dell, Inc.
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
import sys
import warnings

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to system and GPU sensor / temperature information")
parser.add_argument('-ip', help='Pass in iDRAC IP address', required=False)
parser.add_argument('-u', help='Pass in iDRAC username', required=False)
parser.add_argument('-p', help='Pass in iDRAC password. If not passed in, script will prompt to enter password which will not be echoed to the screen', required=False)
parser.add_argument('--ssl', help='Verify SSL certificate for all Redfish calls, pass in \"true\". This argument is optional, if you do not pass in this argument, all Redfish calls will ignore SSL cert checks.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID to execute all Redfish calls instead of passing in username/password', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-system-inlet-temp', help='Get current system board inlet temperature', action="store_true", dest="get_system_inlet_temp", required=False)
parser.add_argument('--get-system-exhaust-temp', help='Get current system board exhaust temperature', action="store_true", dest="get_system_exhaust_temp", required=False)
parser.add_argument('--get-system-power-use', help='Get current system board power consumption', action="store_true", dest="get_system_power_use", required=False)
parser.add_argument('--get-gpu-temp', help='Get current GPU temperatures', action="store_true", dest="get_gpu_temp", required=False)
parser.add_argument('--get-gpu-fan', help='Get current GPU fan speed and Pulse Width Modulation (PWM). This argument will only get details for GPU fans which are in slots 7 to 16', action="store_true", dest="get_gpu_fan", required=False)
parser.add_argument('--all', help='Pass in this argument to get data for all supported arguments', action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetSystemGpuSensorTempDetailsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-system-inlet-temp, this example will return only system inlet temp information.
    \n- GetSystemGpuSensorTempDetailsREDFISH.py -ip 100.82.167.168 -u root -p calvin --get-system-inlet-temp --get-system-exhaust-temp, this example will return both system inlet and exhaust tempt information.
    \n- GetSystemGpuSensorTempDetailsREDFISH.py -ip 100.82.167.168 -u root -p calvin --all, this example will return system inlet and exhaust temp, system power consumption, gpu temps and gpu fan speed/pwm.""")
    sys.exit(0)

def check_supported_idrac_version():
    global argument_detected
    argument_detected = "no"
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/ThermalSubsystem' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/ThermalSubsystem' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit(1)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to validate iDRAC creds, status code %s returned." % response.status_code)
        logging.warning(data)
        sys.exit(1)
    
def get_system_board_inlet_temp():
    global argument_detected
    argument_detected = "yes"
    print("\n")
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp?$select=Reading' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardInletTemp?$select=Reading' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get system board inlet temp, status code %s returned." % response.status_code)
        logging.warning(data)
        return
    logging.info("- System Board Inlet Temp\n\nReading: %s" % data["Reading"])

def get_system_board_exhaust_temp():
    global argument_detected
    argument_detected = "yes"
    print("\n")
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardExhaustTemp?$select=Reading' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardExhaustTemp?$select=Reading' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get system board exhaust temp, status code %s returned." % response.status_code)
        logging.warning(data)
        return
    logging.info("- System Board Exhaust Temp\n\nReading: %s" % data["Reading"])

def get_system_board_power_consumption():
    global argument_detected
    argument_detected = "yes"
    print("\n")
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardPwrConsumption?$select=Reading' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Sensors/SystemBoardPwrConsumption?$select=Reading' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get system board power consumption" % response.status_code)
        logging.warning(data)
        return
    logging.info("- System Board Power Consumption\n\nReading: %s" % data["Reading"])

def get_gpu_temps():
    global argument_detected
    argument_detected = "yes"
    print("\n")
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get all gpu members, status code %s returned." % response.status_code)
        logging.warning(data)
        return
    gpu_id_list = []
    for i in data.items():
        if i[0] == "Members":
            for ii in i[1]:
                if "cpu" in ii["@odata.id"].lower():
                    continue
                else:
                    gpu_id_list.append(ii["@odata.id"].split("/")[-1])
    if gpu_id_list == []:
        logging.warning("- WARNING, no GPUs detected for server configuration")
        return
    for i in gpu_id_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors/%s/Oem/Dell/ThermalMetrics' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors/%s/Oem/Dell/ThermalMetrics' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logging.warning("\n- WARNING, GET request failed to get gpu temps, status code %s returned." % response.status_code)
            logging.warning(data)
            return
        logging.info("- GPU %s Temp Info -\n" % i)
        for i in data.items():
            if i[0] == "Temperatures":
                for ii in i[1]:
                    for iii in ii.items():
                        if iii[0] == "Name":
                            print("%s: %s" % (iii[0], iii[1]))
                        if iii[0] == "ReadingCelsius":
                            print("%s: %s\n" % (iii[0], iii[1]))

def get_gpu_fan_rpm_pwm():
    global argument_detected
    argument_detected = "yes"
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/ThermalSubsystem/Fans?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/ThermalSubsystem/Fans?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get all fan members, status code %s returned." % response.status_code)
        logging.warning(data)
        return
    if data["Members"] == []:
        logging.warning("- WARNING, no GPU fans detected for server configuration")
        return
    fan_count = 0
    for i in data["Members"]:
        if "7" in i["Name"] or "8" in i["Name"] or "9" in i["Name"] or "10" in i["Name"] or "11" in i["Name"] or "12" in i["Name"] or "13" in i["Name"] or "14" in i["Name"] or "15" in i["Name"] or "16" in i["Name"]:
            logging.info("\n- %s Info -\n"% i["Name"])
            fan_count += 1
            if "Oem" not in i.keys():
                logging.warning("FanPWM: \"iDRAC version detected does not support this property, update to latest iDRAC version\"")
            for ii in i.items():
                if ii[0] == "SpeedPercent":
                    for iii in ii[1].items():
                        print("%s: %s" % (iii[0], iii[1]))
                if ii[0] == "Oem":
                    print("FanPWM: %s" % ii[1]["Dell"]["FanPWM"])
        else:
            continue
    if fan_count == 0:
        logging.warning("- WARNING, no GPU fans detected for server configuration")

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    if args["get_system_inlet_temp"]:
        get_system_board_inlet_temp()
    if args["get_system_exhaust_temp"]:
        get_system_board_exhaust_temp()
    if args["get_system_power_use"]:
        get_system_board_power_consumption()
    if args["get_gpu_temp"]:
        get_gpu_temps()
    if args["get_gpu_fan"]:
        get_gpu_fan_rpm_pwm()
    if args["all"]:
        get_system_board_inlet_temp()
        get_system_board_exhaust_temp()
        get_system_board_power_consumption()
        get_gpu_temps()
        get_gpu_fan_rpm_pwm()
    if argument_detected == "no" and not args["all"]:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

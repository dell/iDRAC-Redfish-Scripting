#!/usr/bin/python3
#
# ServerVirtualAcPowerCycleREDFISH. Python script using Redfish API to virtual a/c power cycle the server.
#
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
import sys
import time
import warnings

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to virtual a/c power cycle the server. Note: you must have iDRAC9 version 6.10.00 or newer to run DMTF a/c power cycle, 7.00.06 version or newer to run OEM a/c power cycle.")
parser.add_argument('-ip', help='Pass in iDRAC IP address', required=False)
parser.add_argument('-u', help='Pass in iDRAC username', required=False)
parser.add_argument('-p', help='Pass in iDRAC password. If not passed in, script will prompt to enter password which will not be echoed to the screen', required=False)
parser.add_argument('--ssl', help='Verify SSL certificate for all Redfish calls, pass in \"true\". This argument is optional, if you do not pass in this argument, all Redfish calls will ignore SSL cert checks.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID to execute all Redfish calls instead of passing in username/password', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--ac-cycle', help='Virtual a/c power cycle the server using DMTF method. Note: This method will not completely drain flea power', action="store_true", dest="ac_cycle", required=False)
parser.add_argument('--oem-ac-cycle', help='Virtual a/c cycle the server using OEM method. Note: This method will completely drain flee power which is equivalent to the action of disconnecting power cables. Note: Server must be powered off first before running this OEM action.', action="store_true", dest="oem_ac_cycle", required=False)
parser.add_argument('--final-power-state', help='Final server power state after performing virtual OEM AC cycle. Supported values: On and Off', dest="final_power_state", required=False)
parser.add_argument('--power-off', help='Power off server first before running virtual AC cycle. Server in OFF state first is required if running OEM virtual AC cycle.', action="store_true", dest="power_off", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ServerVirtualAcPowerCycleREDFISH.py -ip 192.168.0.120 -u root -p calvin --ac-cycle, this example will a/c power cycle the server.
    \n- ServerVirtualAcPowerCycleREDFISH.py -ip 192.168.0.120 -u root -p calvin --power-off --oem-ac-cycle --final-power-state On, this example will first power off the server, perform full virtual a/c power cycle and power on the server once operation is complete""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to validate iDRAC creds, status code %s returned." % response.status_code)
        logging.warning(data)
        sys.exit(1)

def power_off_server():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1?$select=PowerState' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1?$select=PowerState' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get current server power state, status code %s returned." % response.status_code)
        logging.warning(data)
        sys.exit(0)
    if data["PowerState"].lower() == "off":
        logging.info("- INFO, server already in OFF state, skipping power off operation")
        return
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" % idrac_ip
    payload = {"ResetType": "ForceOff"}
    if args["x"]:
        headers = {"content-type": "application/json", "X-Auth-Token": args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {"content-type": "application/json"}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to power off the server")
        time.sleep(10)
    else:
        logging.error("\n- FAIL, POST command failed, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        sys.exit(1)

def ac_power_cycle():
    if args["power_off"]:
        power_off_server()    
    url = 'https://%s/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset' % idrac_ip
    payload = {"ResetType": "PowerCycle"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to perform virtual server a/c power cycle, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, Command failed, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        sys.exit(1)

def oem_ac_power_cycle():
    if args["power_off"]:
        power_off_server() 
    url = 'https://%s/redfish/v1/Chassis/System.Embedded.1/Actions/Oem/DellOemChassis.ExtendedReset' % idrac_ip
    if args["final_power_state"]:
        payload = {"ResetType": "PowerCycle", "FinalPowerState":args["final_power_state"].title()}
    else:
        payload = {"ResetType": "PowerCycle"}    
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to perform full virtual server a/c power cycle, status code %s returned" % response.status_code)
        if args["final_power_state"].lower() == "on":
            logging.info("\n- INFO, wait a few minutes for the process to complete, server will automatically power on")
    else:
        logging.error("\n- FAIL, Command failed, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        sys.exit(1)
        

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
    if args["ac_cycle"]:
        ac_power_cycle()
    elif args["oem_ac_cycle"]:
        oem_ac_power_cycle()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#
# SetChassisIndicatorledREDFISH. Python script using Redfish API to either get current chassis indicator LED state or set chassis indicator LED state.
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
import json
import logging
import re
import requests
import sys
import time
import warnings

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current chassis indicator LED state or set chassis indicator LED state")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('--script-examples', help='Get examples of executing script.', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current chassis indicator LED state', action="store_true", required=False)
parser.add_argument('--set', help='Set chassis indicator LED state, pass in one of the supported values: \"Lit\" or \"Blinking\". These values are case sensitive so pass in the exact string syntax', required=False)
args=vars(parser.parse_args())

logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def script_examples():
    print("""SetChassisIndicatorLedREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will return current chassis LED state.
    \nSetChassisIndicatorLedREDFISH.py -ip 192.168.0.120 -u root -p calvin --set Lit, this example will disable blinking and set chassis LED state to Lit.
    \nSetChassisIndicatorLedREDFISH.py -ip 192.168.0.120 -u root -p calvin --set Blinking, this example will set chassis LED to blink.""")

def get_current_chassis_indicator_LED_state():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit(0)
    elif response.status_code != 200:
        logging.error("- ERROR, status code %s returned, error results: %s" % (response.status_code, data))
        sys.exit(0)
    logging.info("\n- INFO, current chassis indicator LED state is: %s" % data['IndicatorLED'])

def set_current_chassis_indicator_LED_state():
    url = 'https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip
    payload = {'IndicatorLED': args["set"]}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS, PATCH command successfully completed \"%s\" request for chassis indicator LED" % args["set"])
    else:
        logging.error("\n- ERROR, status code %s returned, detailed failure results:\n%s" % (response.status_code, response.__dict__))
        sys.exit(0)
        

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    elif args["get"]:
        get_current_chassis_indicator_LED_state()
    elif args["set"]:
        set_current_chassis_indicator_LED_state()
    else:
        script_examples()
        
        



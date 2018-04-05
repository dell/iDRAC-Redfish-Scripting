#
# SetChassisIndicatorledREDFISH. Python script using Redfish API to either get current chassis indicator LED state or set chassis indicator LED state.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

import requests, json, sys, re, time, warnings, argparse

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current chassis indicator LED state or set chassis indicator LED state")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-g', help='Get current chassis indicator LED state, pass in \"y\"', required=False)
parser.add_argument('-s', help='Set chassis indicator LED state, pass in one of the supported values: \"Off\" or \"Blinking\". These values are case sensitive so pass in the exact string syntax', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def get_current_chassis_indicator_LED_state():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, current chassis indicator LED state is: %s" % data[u'IndicatorLED'])

def set_current_chassis_indicator_LED_state():
    url = 'https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip
    payload = {'IndicatorLED': args["s"]}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    #print response.__dict__
    if response.status_code == 200:
        print("\n- PASS, PATCH command successfully completed \"%s\" request for chassis indicator LED" % args["s"])
    else:
        print("\n- FAIL, status code %s returned, detailed failure results:\n" % response.status_code)
        print response.__dict__
        

if __name__ == "__main__":
    if args["g"]:
        get_current_chassis_indicator_LED_state()
    elif args["s"]:
        set_current_chassis_indicator_LED_state()
        



#
# SetPowerStateREDFISH. Python script using Redfish API to change current server power state.
#
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
import json
import requests
import sys
import warnings

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(
    description="Python script using Redfish API to either get current server power state and possible power state "
                "values or execute server power state change")
parser.add_argument('-ip', help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
mutex_group = parser.add_mutually_exclusive_group(required=True)
mutex_group.add_argument('--script-examples', action="store_true",
                         help='Prints a set of examples for this script.')
mutex_group.add_argument('-g',
                         help='Get current power state of the server and possible values for ComputerSystem.Reset.',
                         action='store_true')
mutex_group.add_argument('-r',
                         help='Pass in the computer system reset type you want to perform. To get supported possible '
                              'values, execute the script with -g argument')

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]

def test_idrac_creds():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    if response.status_code == 401:
        print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit(1)
    else:
        pass


def get_current_power_state():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip, verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s\n" % data['PowerState'])
    print("- Supported values for server power control are:\n")
    for i in data['Actions']['#ComputerSystem.Reset']['ResetType@Redfish.AllowableValues']:
        print(i)


def set_power_state():
    requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip, verify=False,
                 auth=(idrac_username, idrac_password))
    print("\n- INFO, setting new server power state to: %s" % (args["r"]))

    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': args["r"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,
                             auth=(idrac_username, idrac_password))

    status_code = response.status_code
    if status_code == 204:
        print("\n- PASS, status code %s returned, server power state successfully set to \"%s\"\n" % (
            status_code, args["r"]))
    else:
        print("\n- FAIL, Command failed, status code %s returned\n" % status_code)
        print(response.json())
        sys.exit(1)


if __name__ == "__main__":
    test_idrac_creds()
    if args["g"]:
        get_current_power_state()
    elif args["r"]:
        set_power_state()
    elif args["script_examples"]:
        print('\nSetPowerStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -g, this example will '
              'return the current power state of the server and supported values for changing the '
              'server power state. \n\nSetPowerStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -r On,'
              ' this example will power on the server.')
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")

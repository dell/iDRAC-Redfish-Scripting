#
# SetPowerStateREDFISH. Python script using Redfish API to change current server power state.
#
# NOTE: Recommended to run GetPowerStateREDFISH script first to get current server power state.
#
# NOTE: For power_state_ioption, make sure you pass in the exact string value as returned from GetPowerStateREDFISH script. These values are case sensitive.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2017, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
    power_state_option = sys.argv[4]

except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password. / power state option. Example: \"script_name.py 192.168.0.120 root calvin On\"")
    sys.exit()

response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
data = response.json()
print("\n- Current server power state is: %s, setting new server power state to: %s" % (data[u'PowerState'], power_state_option))

url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
payload = {'ResetType': power_state_option}
headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))

statusCode = response.status_code
if statusCode == 204:
    print("\n- PASS, status code %s returned, server power state successfully set to \"%s\"\n" % (statusCode, power_state_option))
else:
    print("\n- FAIL, Command failed, status code %s returned\n" % statusCode)
    print(response.json())
    sys.exit()


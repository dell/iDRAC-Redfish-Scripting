#
# SetIdracDefaultSettingsREDFISH. Python script using Redfish API to reset iDRAC to default configuration settings.
#
# NOTE: Once the script is complete, iDRAC will reset to complete the reset to default process and you will lose network connection. iDRAC should be back up within one minute.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to reset the iDRAC to default configuration settings")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SetIdracDefaultSettingsREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get supported values for reset type. SetIdracDefaultSettingsREDFISH.py -ip 192.168.0.120 -u root -p calvin -r ResetAllWithRootDefaults, this example will reset the iDRAC to default settings and reset iDRAC user to root\calvin')
parser.add_argument('-g', help='Get supported reset type values, pass in a value of \"y\"', required=False)
parser.add_argument('-r', help='Pass in the reset type value you want to perform for iDRAC reset. NOTE: Make sure to pass in exact string value, value is case sensitive.', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

# Function to get reset type values

def get_reset_type_values():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        print("\n- FAIL, GET command failed to get reset values, error details: %s" % response)
        sys.exit()
    print("\n- Supported reset type values for iDRAC reset to defaults -\n")
    for i in data[u'Actions'][u'Oem'][u'DellManager.v1_0_0#DellManager.ResetToDefaults'][u'ResetType@Redfish.AllowableValues']:
        if i == "All":
            print("%s: Reset all iDRAC\'s configuration to default and reset user to shipping value." % i)
        if i == "ResetAllWithRootDefaults":
            print("%s: Reset all iDRAC's configuration to default and reset user to root\calvin" % i)
        if i == "Default":
            print("%s: Reset all iDRAC\'s configuration to default and preserve user, network settings." % i)
        




# Function to reset iDRAC to default settings.

def set_idrac_default_settings():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults' % (idrac_ip)
    payload = {"ResetType": args["r"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for POST command to reset iDRAC to default settings using reset type \"%s\"" % (statusCode, args["r"]))
    else:
        print("\n- FAIL, status code %s returned, unable to reset iDRAC to default settings" % statusCode)
        sys.exit()
    time.sleep(15)
    print("\n- iDRAC will now reset to default settings and restart the iDRAC. iDRAC should be back up within a few minutes.")
    
### Run code

if __name__ == "__main__":
    if args["g"]:
        get_reset_type_values()
    elif args["r"]:
        set_idrac_default_settings()
    else:
        print("\n- FAIL, either missing required parameter(s) or incorrect parameter or parameter value passed in")


#
# IdracResetToDefaultsREDFISH. Python script using Redfish API to reset iDRAC to default settings.
#
# NOTE: Once the script is complete, iDRAC will reset to complete the process and you will lose network connection. iDRAC should be back up within a few minutes.
# 
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

from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to reset the iDRAC to default settings')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-r', help='Pass in the iDRAC reset type. Supported values are 1, 2 and 3. 1 for All(All configuration is set to default), 2 for ResetAllWithRootDefaults(All configuration including network is set to default. Exception root user password set to calvin) or 3 for Default(All configuration is set to default except users and network settings are preserved)', required=True)


args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]



def reset_idrac_to_default_settings():
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults" % idrac_ip
    if args["r"] == "1":
        payload = {"ResetType":"All"}
        reset_type = "All"
    elif args["r"] == "2":
        payload = {"ResetType":"ResetAllWithRootDefaults"}
        reset_type = "ResetAllWithRootDefaults"
    elif args["r"] == "3":
        payload = {"ResetType":"Default"}
        reset_type = "Default"
    else:
        print("\n- FAIL, invalid value passed in for reset type(-r). Execute script with -h to see supported values for reset type")
        sys.exit()
    
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for POST command to reset iDRAC to \"%s\" setting\n" % (statusCode, reset_type))
    else:
        data=response.json()
        print("\n- FAIL, status code %s returned, error is: \n%s") % (statusCode, data)
        sys.exit()
    time.sleep(15)
    print("- WARNING, iDRAC will now reset and be back online within a few minutes.")
    

if __name__ == "__main__":
    reset_idrac_to_default_settings()


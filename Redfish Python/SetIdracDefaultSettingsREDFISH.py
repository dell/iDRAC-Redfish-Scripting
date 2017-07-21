#
# SetIdracDefaultSettingsREDFISH. Python script using Redfish API to set iDRAC to default settings.
#
# NOTE: Once the script is complete, iDRAC will reset to complete the reset to defaut process and you will lose network connection. iDRAC should be back up within one minute.
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

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password. Example: \"script_name.py 192.168.0.120 root calvin\"")
    sys.exit()


### Function to reset iDRAC to default settings.

def set_idrac_default_settings():
    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults' % (idrac_ip)
    
    payload = {"ResetType": "All"}
    
    headers = {'content-type': 'application/json'}
    
    response = requests.post(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))

    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for POST command to reset iDRAC to default settings") % statusCode
    else:
        print("\n- FAIL, status code %s returned, password was not changed") % statusCode
        sys.exit()
    time.sleep(15)
    print("\n- iDRAC will now reset to default settings and restart the iDRAC. iDRAC should be back up within 1 minute.")
    
### Run code

if __name__ == "__main__":
    set_idrac_default_settings()


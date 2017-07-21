#
# ChangeIdracUserPasswordREDFISH. Python script using Redfish API to change iDRAC username password. Once the password is changed, the script will also execute a GET command to verify the password change was successful.
#
# NOTE: For iDRAC account ID parameter, pass in the ID of the user. Example: If changing root password, pass in a value of 2 for account ID parameter.
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
    idrac_account_id = sys.argv[4]
    idrac_new_password = sys.argv[5]
   
except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password / idrac_account_id / idrac_new_password. Example: \"script_name.py 192.168.0.120 root calvin 2 test\"")
    sys.exit()


### Function to change iDRAC user password and verify password was changed by executing GET command with new password

def set_idrac_user_password():
    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, idrac_account_id)
    
    payload = {'Password': idrac_new_password}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))

    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for PATCH command to change iDRAC user password") % statusCode
    else:
        print("\n- FAIL, status code %s returned, password was not changed") % statusCode
        sys.exit()
    time.sleep(5)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, idrac_account_id),verify=False,auth=(idrac_username, idrac_new_password))
    
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for GET command, iDRAC user password change success") % statusCode
    else:
        print("\n- FAIL, status code %s returned for GET command") % statusCode
        sys.exit()
    
### Run code

if __name__ == "__main__":
    set_idrac_user_password()


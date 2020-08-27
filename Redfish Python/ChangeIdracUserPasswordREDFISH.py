#!/usr/bin/python
# ChangeIdracUserPasswordREDFISH. Python script using Redfish API with OEM extension to change iDRAC username password. Once the password is changed, the script will also execute a GET command to verify the password change was successful.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 8.0
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


parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to change iDRAC username password. Once the password is changed, the script will execute GET command to verify the password change was successful.")
parser.add_argument('script_examples',action="store_true",help='ChangeIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get user account information for all iDRAC users. ChangeIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u user -p calvin -id 3 -np pAssw0rd, this example shows changing iDRAC user ID 3 password.')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-g', help='Get iDRAC user account information, pass in \"y\". This will return detailed information for each iDRAC user account.', required=False)
parser.add_argument('-id', help='Pass in the iDRAC user account ID you want to change the password for. If needed, use argument -g to get the iDRAC user account ID.', required=False)
parser.add_argument('-np', help='Pass in the new password you want to set for the iDRAC user ID.', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

### Function to get iDRAC user accounts information

def get_iDRAC_user_account_info():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts' % (idrac_ip),verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        pass
    else:
        data = response.json()
        print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
        sys.exit()
    data = response.json()
    print("\n- iDRAC User Account Information -")
    for i in data["Members"]:
        for ii in i.items():
            remove_id_1 = ii[1].strip("/")[-1]
            if remove_id_1 == "1":
                continue
            else:
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                statusCode = response.status_code
                if statusCode == 200:
                    pass
                else:
                    data = response.json()
                    print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
                    sys.exit()
                data=response.json()
                print("\n")
                for i in data.items():
                    if "@" in i[0] or i[0] == "Links":
                        pass
                    else:
                        print("%s: %s" % (i[0], i[1]))
                


### Function to change iDRAC user password and verify password was changed by executing GET command with new password

def set_idrac_user_password():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, idrac_account_id),verify=False,auth=(idrac_username, idrac_password))
    if response.status_code == 401:
        print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials and privilege level")
        sys.exit()
    else:
        pass
    data = response.json()
    username = data["UserName"]
    user_roleID = data["RoleId"]
    user_id = data["Id"]
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, idrac_account_id)
    payload = {'Password': idrac_new_password}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))

    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for PATCH command to change iDRAC user password for user ID %s" % (statusCode, user_id))
    else:
        data = response.json()
        print("\n- FAIL, status code %s returned, password was not changed. Detailed error results: \n%s" % (statusCode, data))
        sys.exit()
    
    time.sleep(10)
    count = 1
    while True:
        if count == 10:
            print("- WARNING, GET request to validate iDRAC user account \"%s\" new password failed, retry count of 10 has been reached" % user_id)
            sys.exit()
        else:
            if idrac_username == username:
                print("- INFO, executing GET request to validate new password set for iDRAC user \"%s\"" % idrac_username)
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, idrac_account_id),verify=False,auth=(idrac_username, idrac_new_password))
            else:
                if user_roleID == "None":
                    print("- WARNING, iDRAC user \"%s\" privileges set to None, password is changed but unable to execute GET request due to incorrect privilege level" % username)
                    sys.exit()
                else:
                    print("- INFO, executing GET request to validate new password set for iDRAC user \"%s\"" % username)
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, user_id),verify=False,auth=(username, idrac_new_password))
                    statusCode = response.status_code
        if statusCode == 401:
            print("- WARNING, GET request failed to test iDRAC user account \"%s\" new password, retry" % idrac_account_id)
            time.sleep(10)
            count+=1
            continue
        else:
            pass
        if statusCode == 200:
            print("\n- PASS, status code %s returned for GET command, iDRAC user password change successful for account ID %s" % (statusCode, idrac_account_id))
            break
        else:
            data = response.json()
            print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (statusCode, data))
            sys.exit()
    
### Run code

if __name__ == "__main__":
    if args["g"]:
        get_iDRAC_user_account_info()
    elif args["id"] and args["np"]:
        idrac_account_id = args["id"]
        idrac_new_password = args["np"]
        set_idrac_user_password()
    else:
        print("\n- FAIL, either missing parameter(s) or invalid parameter value(s) passed in. If needed, review help text for script examples")


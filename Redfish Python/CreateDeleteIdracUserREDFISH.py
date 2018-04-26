#
# CreateDeleteIdracUserREDFISH. Python script using Redfish API to either get current iDRAC settings, create or delete iDRAC user.
#
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC user settings, create iDRAC user or delete iDRAC user using the user account ID")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-g', help='Get current iDRAC user settings, pass in the user account ID. Supported values are 1 to 16', required=False)
parser.add_argument('-C', help='Create iDRAC user, pass in the user account ID. Supported values are 1 to 16. When creating new iDRAC user, you must also use -U, -P, -E and -R along with -C' , required=False)
parser.add_argument('-U', help='Pass in new iDRAC username', required=False)
parser.add_argument('-P', help='Pass in new iDRAC username password', required=False)
parser.add_argument('-E', help='Enable the iDRAC user, pass in either \"True\" or \"False\"', required=False)
parser.add_argument('-R', help='Pass in the iDRAC user privileges you want to set for the user. Supported values are: \"Administrator\", \"Operator\", \"ReadOnly\" and \"None\"', required=False)
parser.add_argument('-D', help='To delete iDRAC user account, pass in the user account ID', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["C"]:
    try:
        new_idrac_username = args["U"]
        new_idrac_password = args["P"]
        new_idrac_user_enable = args["E"].title()
        new_idrac_user_role = args["R"]
    except:
        print("\n- FAIL, missing one or multiple required arguments to create new iDRAC user. You must use -C, -U, -P, -E and -R arguments to create a new iDRAC user")
        sys.exit()
    if new_idrac_user_enable == "True":
        new_idrac_user_enable = True
    elif new_idrac_user_enable == "False":
        new_idrac_user_enable = False
            

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_idrac_user_settings(x):
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, x),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, current iDRAC user settings for account ID \"%s\"\n" % x)
    for i in data.items():
        if i[0] == "Password":
            print("Password: *****")
        else:
            print("%s: %s" % (i[0],i[1]))

def create_idrac_user():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["C"])
    payload = {'UserName':new_idrac_username,'Password': new_idrac_password,'Enabled':new_idrac_user_enable,'RoleId':new_idrac_user_role}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for PATCH command to create new iDRAC user for account ID %s" % (statusCode, args["C"])) 
    else:
        print("\n- FAIL, status code %s returned, unable to create new iDRAC user. Detailed error information is: %s" % (statusCode, response.__dict__))
        sys.exit()

def delete_idrac_user():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["D"])
    payload = {'Enabled':False,'RoleId':'None'}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    payload = {'UserName':'','Password': ''}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    print("\n- PASS, iDRAC user cleared for account ID %s" % (args["D"])) 
    
    
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_idrac_user_settings(args["g"])
    elif args["C"]:
        create_idrac_user()
        get_idrac_user_settings(args["C"])
    elif args["D"]:
        delete_idrac_user()
        get_idrac_user_settings(args["D"])
        
    






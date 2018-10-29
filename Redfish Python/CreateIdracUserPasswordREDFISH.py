#
# CreateIdracUserPasswordREDFISH. Python script using Redfish API to either create or delete iDRAC user
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to either create or delete iDRAC user')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC username pasword', required=True)
parser.add_argument('script_examples',action="store_true",help='CreateIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -id 3 -un user3 -pwd test123 -pl 2 -e y, this example will create iDRAC user for id 3, enable and set privileges to operator. CreateIdracUserPasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -d 3, this example will delete iDRAC user id 3')
parser.add_argument('-g', help='Get current iDRAC user account information for all iDRAC ids, pass in \"y\". If you only want to get a specific iDRAC user account, pass in argument -id also with -g', required=False)
parser.add_argument('-id', help='Pass in the iDRAC user account ID you want to configure', required=False)
parser.add_argument('-un', help='Pass in the name of the iDRAC user you want to create', required=False)
parser.add_argument('-pwd', help='Pass in the password of the iDRAC user you are creating', required=False)
parser.add_argument('-pl', help='Pass in the privilege level for the user you are creating. Supported values are 1 for \"Administrator\", 2 for \"Operator\", 3 for \"ReadOnly" for 4 for \"None\"', required=False)
parser.add_argument('-e', help='Enable the new user you are creating, pass in \"y\" to enable, \"n\" to disable', required=False)
parser.add_argument('-d', help='Delete iDRAC user, pass in the iDRAC user account id', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


### Function to change iDRAC user password and verify password was changed by executing GET command with new password

def create_idrac_user_password():
    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["id"])
    payload = {"UserName":args["un"], "Password":args["pwd"]}
    if args["pl"] == "1":
        payload["RoleId"]="Administrator"
    elif args["pl"] == "2":
        payload["RoleId"]="Operator"
    elif args["pl"] == "3":
        payload["RoleId"]="ReadOnly"
    elif args["pl"] == "4":
        payload["RoleId"]="None"
    else:
        print("- FAIL, invalid value passed in for argument -pl")
        sys.exit()
    if args["e"] == "y":
        payload["Enabled"] = True
    elif args["e"] == "n":
        payload["Enabled"] = False
    else:
        print("- FAIL, invalid value passed in for argument -e")
        sys.exit()
    
    print("\n- Parameters and values passed in for PATCH command to create iDRAC user\n")
    for i in payload.items():
        if i[0] == "Password":
            print("Password: ******")
        else:
            print("%s: %s" % (i[0],i[1]))
    print("Id: %s" % args["id"])
    
   
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))

    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, status code %s returned for PATCH command to create iDRAC user \"%s\"" % (statusCode, args["un"]))
    else:
        print("\n- FAIL, status code %s returned, password was not changed") % statusCode
        sys.exit()

def verify_idrac_user_created():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["id"]),verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode != 200:
        print("\n- FAIL, status code %s returned for GET command") % statusCode
        sys.exit()
    else:
        pass
    data = response.json()
    if data[u'UserName'] == args["un"]:
        print("\n- PASS, iDRAC user \"%s\" successfully created" % args["un"])
    else:
        print("\n- FAIL, iDRAC user %s not successfully created, GET command complete details %s" % (args["un"], data))
        sys.exit()

def delete_idrac_user():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["d"])
    payload = {"Enabled":False,"RoleId":"None"}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    data = response.json()
    if statusCode == 200:
        pass
    else:
        print("\n- FAIL, status code %s returned, iDRAC user not deleted. Detailed error results %s" % (statusCode, data))
        sys.exit()
    payload = {"UserName":""}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    data = response.json()
    if statusCode == 200:
        print("\n- PASS, status code %s returned for PATCH command to delete iDRAC user id %s" % (statusCode, args["d"]))
    else:
        print("\n- FAIL, status code %s returned, iDRAC user not deleted. Detailed error results %s" % (statusCode, data))
        sys.exit()
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["d"]),verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode != 200:
        print("\n- FAIL, status code %s returned for GET command") % statusCode
        sys.exit()
    else:
        pass
    data = response.json()
    if data[u'UserName'] == "":
        print("\n- PASS, iDRAC user id \"%s\" successfully deleted" % args["d"])
    else:
        print("\n- FAIL, iDRAC user %s not successfully deleted, GET command complete details %s" % (args["d"], data))
        sys.exit()

def get_current_iDRAC_user_information():
    if args["id"]:
        print("\n- Current iDRAC account user information for id %s" % args["id"])
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, args["id"]),verify=False,auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        if statusCode != 200:
            print("\n- FAIL, status code %s returned for GET command") % statusCode
            sys.exit()
        else:
            pass
        data = response.json()
        print("\n")
        for i in data.items():
            if i[0] == "@odata.type" or i[0] == "Links" or i[0] == "@odata.context":
                pass
            else:
                print("%s: %s" % (i[0], i[1]))
        sys.exit()
    else:
        print("\n- Current iDRAC account user information -")
        for i in range(2,17):
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            statusCode = response.status_code
            if statusCode != 200:
                print("\n- FAIL, status code %s returned for GET command") % statusCode
                sys.exit()
            else:
                pass
            data = response.json()
            print("\n")
            for i in data.items():
                if i[0] == "@odata.type" or i[0] == "Links" or i[0] == "@odata.context":
                    pass
                else:
                    print("%s: %s" % (i[0], i[1]))
        
    

if __name__ == "__main__":
    if args["id"] and args["un"] and args["pwd"] and args["pl"]:
        create_idrac_user_password()
        verify_idrac_user_created()
    elif args["d"]:
        delete_idrac_user()
    elif args["g"]:
        get_current_iDRAC_user_information()   
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")
        


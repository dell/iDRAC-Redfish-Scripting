#
# GetRemoteServicesAPIStatusREDFISH. Python script using Redfish API with OEM extension to get the server remote services status
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2019, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get the server remote services status. This will return: lifecycle controller(LC) status, real time monitoring (RT) status, server status and overall status of the command")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)




args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        print("\n- FAIL, either incorrect iDRAC username / password passed in or iDRAC user doesn't have correct privileges")
        sys.exit()
    if response.status_code == 401:
        print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def get_remote_service_api_status():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
    method = "GetRemoteServicesAPIStatus"
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n-PASS: POST command passed for %s method, status code 200 returned\n" % method)
    else:
        print("\n-FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))
    

    

if __name__ == "__main__":
    check_supported_idrac_version()
    get_remote_service_api_status()
    
    
        
            
        
        

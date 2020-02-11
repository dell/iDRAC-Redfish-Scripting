#
# ManageIdracTimeREDFISH. Python script using Redfish API with OEM extension to either GET or SET iDRAC time
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2020, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either GET or SET iDRAC time")
parser.add_argument('script_examples',action="store_true",help='ManageIdracTimeREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get current iDRAC time. ManageIdracTimeREDFISH.py -ip 192.168.0.120 -u root -p calvin -s 2019-11-18T17:00:10-06:00, this example sets iDRAC current time.')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-g', help='Get current iDRAC time, pass in \"y\"', required=False)
parser.add_argument('-s', help='To set iDRAC time, pass in the correct date / time in supported format. To see valid format, execute -g argument first to get current time and supported format.', required=False)




args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        print("\n- FAIL, either incorrect iDRAC username / password passed in or iDRAC user doesn't have correct privileges")
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":True}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n-PASS: POST command passed for %s action GET iDRAC time, status code 200 returned\n" % method)
    else:
        print("\n-FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))

def set_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":False, "TimeData":args["s"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n-PASS: POST command passed for %s action to SET iDRAC time, status code 200 returned\n" % method)
    else:
        print("\n-FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

    

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_idrac_time()
    elif args["s"]:
        set_idrac_time()
    else:
        print("\n- FAIL, either missing argument or incorrect argument used. If needed, check script help text.")
        sys.exit()
    
    
    
        
            
        
        

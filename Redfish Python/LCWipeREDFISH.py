#
# LCWipeREDFISH. Python script using Redfish API with OEM extension to delete all configurations from the iDRAC LifecycleController.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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


import requests, json, sys, re, time, warnings, argparse, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to delete all configurations from the iDRAC LifecycleController. NOTE: This method is destructive and will reset all configuration settings on the server.")
parser.add_argument('script_examples',action="store_true",help='LCWipeREDFISH.py -ip 192.168.0.120 -u root -p calvin -e On, this example will delete all iDRAC LifecycleController configuration and return the server to ON state')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-e', help='End host power state. Pass in \"On\" if you want the server to be in ON state once LCWipe process is complete or pass in \"Off\" for server to be in Off state once LCWipe process is complete', required=True)




args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def lc_wipe():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.LCWipe' % (idrac_ip)
    method = "LCWipe"
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code 200 returned" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))
    print("\n- WARNING, iDRAC will now reset to start LCWipe operation. Script will wait 5 minutes and then ping the iDRAC to check network connection")
    time.sleep(300)

def check_idrac_connection():
    while True:
        command="ping %s -n 5" % idrac_ip
        execute_command=subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).communicate()[0]
        re_search=re.search("Lost = .+? ",execute_command).group()
        if re_search != 'Lost = 0 ':
            print("- WARNING, unable to ping iDRAC IP, script will wait 1 minute and try again")
            time.sleep(60)
            continue
        else:
            print("- PASS, successful ping reply to iDRAC IP, script will wait 3 minutes for iDRAC to be ready")
            time.sleep(180)
            break 
        
        

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_power_state = data[u'PowerState']
    if current_power_state == "On":
        print("\n- WARNING, server will now reboot and power OFF after POST to complete the LCWipe operation")
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'ForceOff'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to power OFF server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power OFF server, status code is: %s" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        time.sleep(10)
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to power ON server, code return is %s" % statusCode)
            time.sleep(60)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    if current_power_state == "Off":
        print("\n- WARNING, server will now power ON and OFF after POST to complete the LCWipe operation")
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to power ON server, code return is %s" % statusCode)
            time.sleep(60)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()

def get_remote_service_api_status():
    while True:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
        method = "GetRemoteServicesAPIStatus"
        headers = {'content-type': 'application/json'}
        payload={}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        data=response.json()
        if response.status_code == 200:
            pass
        else:
            print("\n-FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
            data = response.json()
            print("\n-POST command failure results:\n %s" % data)
            sys.exit()
        if data[u'ServerStatus'] == "PoweredOff":
            print("\n- PASS, host successfully auto powered OFF after completing POST")
            time.sleep(30)
            break
        else:
            print("- WARNING, server still in ON state and waiting to auto power off to complete LCWipe operation")
            time.sleep(30)

def final_server_state():
    if args["e"] == "On" or args["e"] == "on":
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to power ON server, code return is %s, LCWipe operation is complete" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
    if args["e"] == "Off" or args["e"] == "off":
        print("\n- PASS, LCWipe operation is complete, server left in OFF state")
        

    

if __name__ == "__main__":
    check_supported_idrac_version()
    lc_wipe()
    check_idrac_connection()
    reboot_server()
    get_remote_service_api_status()
    final_server_state()
    
    
        
            
        
        

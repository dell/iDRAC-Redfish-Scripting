#
# SetBiosDefaultSettingsREDFISH. Python script using Redfish API to set BIOS to default settings
#
# NOTE: For reboot_now option, pass in "y" if you want to reboot the server now or "n" which will still set the flag to set BIOS to default settings but not reboot the server now. Reset to default will get applied when the next manual reboot of the server occurs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

import requests, json, sys, re, time, warnings, os

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
    reboot_now = sys.argv[4].lower()
except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password / reboot now choice. Example: \"script_name.py 192.168.0.120 root calvin y\"")
    sys.exit()

  
### Function to set BIOS reset to default flag, will be applied on next server reboot

def set_bios_reset_to_default():
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ResetBios/" % idrac_ip
    headers = {'content-type': 'application/json'}
    response = requests.post(url, headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS: status code %s returned, flag set for BIOS reset to defaults which will get applied on next server reboot\n" % statusCode)
    else:
        print("\n- FAIL, Command failed, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    
### Function to check if reboot server is needed
                                                                          
def reboot_server():
    if reboot_now == "y" or reboot_now == "yes":
        print("\n- WARNING, user selected to automatically reboot the server now")
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("- WARNING, Current server power state is: %s\n" % data[u'PowerState'])
        if data[u'PowerState'] == "On":
            url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
            payload = {'ResetType': 'ForceOff'}
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
            statusCode = response.status_code
            if statusCode == 204:
                print("- PASS, Command passed to power OFF server, code return is %s\n" % statusCode)
            else:
                print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
                print("Extended Info Message: {0}".format(response.json()))
                sys.exit()
            time.sleep(30)
            payload = {'ResetType': 'On'}
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
            statusCode = response.status_code
            if statusCode == 204:
                print("- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
            else:
                print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
                print("Extended Info Message: {0}".format(response.json()))
                sys.exit()
        else:
            url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
            payload = {'ResetType': 'On'}
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
            statusCode = response.status_code
            if statusCode == 204:
                print("- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
            else:
                print("- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
                print("Extended Info Message: {0}".format(response.json()))
                sys.exit()
    elif reboot_now == "n" or reboot_now == "no":
        print("\n- WARNING, user selected to not automatically reboot the server now, BIOS reset to defaults will be applied on next server reboot")
        sys.exit()
    else:
        print("\n- WARNING, invalid reboot_now option, server will not reboot but flag is still set to reset BIOS to default settings. Will be applied on next server reboot")
        sys.exit()


### Run code

if __name__ == "__main__":
    set_bios_reset_to_default()
    reboot_server()
    print("\n- WARNING, system will now POST and reset the BIOS to default settings, automatically reboot one more time to complete the process.")
    print("  Once the server is back in idle state, execute the GET bios attributes script to view the default BIOS settings.")




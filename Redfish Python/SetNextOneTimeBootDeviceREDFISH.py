#
# SetNextOneTimeBootDeviceREDFISH. Python script using Redfish API to set next reboot one time boot device.
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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



parser = argparse.ArgumentParser(description='Python script using Redfish API to get current next boot onetime boot setting and supported values or set next boot onetime boot device.')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC username pasword', required=True)
parser.add_argument('script_examples',action="store_true",help='SetNextOneTimeBootDeviceREDFISH -ip 191.268.0.120 -u root -p calvin -c, this will get the current next boot setting and possible values.\n- SetNextOneTimeBootDeviceREDFISH -ip 192.168.0.10 -u root -p calvin -o Pxe -r y, this will set next one time boot to PXE and reboot the server now. Once the system completes POST, system will PXE boot.\n- SetNextOneTimeBootDeviceREDFISH.py -ip 192.168.0.120 -u root -p calvin -o UefiTarget -U VenHw(986D1755-B9D0-4F8D-A0DA-D1DB18672045) -r y. This example will reboot the server and one time boot to the Uefi target vendor device ID which is HTTP device path. The vendor device ID string information is in F2 UEFI Device Manager.')
parser.add_argument('-c', help='user option, pass in \"y\" to get current next boot onetime boot setting and possible values', required=False)
parser.add_argument('-o', help='user option, pass in the string onetime boot device you want to set for next reboot. NOTE: This value is case sensitive so pass in exact value as stated in possible values for -c option', required=False, type=str)
parser.add_argument('-U', help='user option to set UEFI target path. This will be used with -o option if you pass in UefiTarget value. ', required=False)
parser.add_argument('-r', help='user option, pass in \"y\" if you want the server to reboot now once you set next boot onetime boot device or \"n\" to not reboot now', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

### Function to get current next boot onetime boot setting possible values for onetime boot

def get_current_setting_next_boot_supported_values():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n-Supported values for next server reboot, one time boot:\n")
    for i in data[u'Boot'][u'BootSourceOverrideTarget@Redfish.AllowableValues']:
      print(i)
    print("\n- Current next reboot, one time boot setting is: %s" % data[u'Boot'][u'BootSourceOverrideTarget'])
    sys.exit()
    
### Function to set next boot onetime boot device

def set_next_boot_onetime_boot_device():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip
    if args["o"] == "UefiTarget" and args["U"]:
      payload = {"Boot":{"BootSourceOverrideTarget":args["o"],"UefiTargetBootSourceOverride":args["U"]}}
    else:
      payload = {"Boot":{"BootSourceOverrideTarget":args["o"]}} 
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    statusCode = response.status_code
    time.sleep(5)
    if statusCode == 200:
      if args["o"] == "UefiTarget" and args["U"]:
        print("\n- PASS: PATCH command passed to set UEFI target path to \"%s\" and next boot onetime boot device to: %s" % (args["U"],args["o"]))
      else:
        print("\n- PASS, PATCH command passed to set next boot onetime boot device to: \"%s\"" % args["o"])
    else:
      print("\n- FAIL, Command failed, error code is %s" % statusCode)
      detail_message=str(response.__dict__)
      print(detail_message)
      sys.exit()


### Function to reboot or  power on the server
                                                                          
def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data[u'PowerState'])
    if data[u'PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to gracefully power OFF server, code return is %s" % statusCode)
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        count = 0
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data[u'PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            elif count == 20:
                print("- WARNING, unable to graceful shutdown the server, will perform forced shutdown now")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, Command passed to forcefully power OFF server, code return is %s" % statusCode)
                    time.sleep(15)
                else:
                    print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
                
            else:
                time.sleep(2)
                count+=1
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data[u'PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()



### Run code

if __name__ == "__main__":
  if args["c"]:
    get_current_setting_next_boot_supported_values()
  elif args["o"] and args["r"]:
    set_next_boot_onetime_boot_device()
    if args["r"] == "n":
      print("- WARNING, no reboot selected for -r argument. Onetime boot will be applied on next manual server reboot")
      sys.exit()
    elif args["r"] == "y":
        reboot_server()
        print("\n- System will now complete POST and one time boot to \"%s\"" % args["o"])
    else:
        print("- FAIL, invalid value passed in for -r argument. Check script help for supported values")
        sys.exit()
  else:
      print("\n- FAIL, either missing or invalid parameter(s) passed in. If needed, see script help text for supported parameters and script examples")




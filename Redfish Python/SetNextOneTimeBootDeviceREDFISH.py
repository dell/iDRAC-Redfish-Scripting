#
# SetNextOneTimeBootDeviceREDFISH. Python script using Redfish API to set next reboot one time boot device.
#
# NOTE: Execute "SetNextOneTimeBootDeviceREDFISH -h" to get help text,  supported parameter options.
#
# NOTE: Its recommended to run "SetNextOneTimeBootDeviceREDFISH -c" to get the current setting and possible values first.
#
# NOTE: If you select no to not reboot the server now, one time boot device for next boot will still be set but will not boot to that device until next manual server reboot.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
parser.add_argument('-i', help='iDRAC IP Address', required=False, type=str)
parser.add_argument('-u', help='iDRAC username', required=False, type=str)
parser.add_argument('-p', help='iDRAC username pasword', required=False, type=str)
parser.add_argument('-e', help='pass in "y" to print executing script examples', required=False, type=str)
parser.add_argument('-c', help='user option, pass in \"y\" to get current next boot onetime boot setting and possible values', required=False, type=str)
parser.add_argument('-o', help='user option, pass in the string onetime boot device you want to set for next reboot. NOTE: This value is case sensitive so pass in exact value as stated in possible values for -c option', required=False, type=str)
parser.add_argument('-U', help='user option to set UEFI target path. This will be used with -o option if you pass in UefiTarget value. ', required=False, type=str)
parser.add_argument('-r', help='user option, pass in \"y\" if you want the server to reboot now once you set next boot onetime boot device or \"n\" to not reboot now', required=False, type=str)

args = parser.parse_args()

idrac_ip=args.i
idrac_username=args.u
idrac_password=args.p

if args.e == "y":
  print("\n- SetNextOneTimeBootDeviceREDFISH -i 191.268.0.120 -u root -p calvin -c, this will get the current next boot setting and possible values.\n- SetNextOneTimeBootDeviceREDFISH -i 192.168.0.10 -u root -p calvin -o Pxe -r y, this will set next one time boot to PXE and reboot the server now. Once the system completes POST, system will PXE boot.\n- SetNextOneTimeBootDevivceREDFISH -i 192.168.0.120 -u root -p calvin -o UefiTarget -U http://192.168.0.130/dellshell.efi -r y. This will set UEFI target path, set next onetime boot to UefiTarget and reboot the server now.")

### Function to get current next boot onetime boot setting possible values for onetime boot

def get_current_setting_next_boot_supported_values():
  if args.c == "y":
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n-Supported values for next server reboot, one time boot:\n")
    for i in data[u'Boot'][u'BootSourceOverrideTarget@Redfish.AllowableValues']:
      print(i)
    print("\n- Current next reboot, one time boot setting is: %s" % data[u'Boot'][u'BootSourceOverrideTarget'])
    sys.exit()
  elif args.c == "n":
    sys.exit()
    
    
                    


### Function to set next boot onetime boot device

def set_next_boot_onetime_boot_device():
  if args.o:
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip
    if args.o == "UefiTarget" and args.U:
      payload = {"Boot":{"BootSourceOverrideTarget":args.o,"UefiTargetBootSourceOverride":args.U}}
    else:
      payload = {"Boot":{"BootSourceOverrideTarget":args.o}} 
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    statusCode = response.status_code
    time.sleep(5)
    if statusCode == 200:
      if args.o == "UefiTarget" and args.U:
        print("\n- PASS: Command passed to set UEFI target path to \"%s\" and next boot onetime boot device to: %s" % (args.U,args.o))
      else:
        print("\n- PASS, Command passed to set next boot onetime boot device to: \"%s\"" % args.o)
    else:
      print("\n- FAIL, Command failed, errror code is %s" % statusCode)
      detail_message=str(response.__dict__)
      print(detail_message)
      sys.exit()


### Function to reboot the server
                                                                          
def reboot_server():
  if args.o == "None":
    print("\n- Next boot onetime boot device set to \"%s\", no reboot server action is required" % args.o)
    sys.exit()
  elif args.r == "y":
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data[u'PowerState'])
    if data[u'PowerState'] == "On":
      url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
      payload = {'ResetType': 'ForceOff'}
      headers = {'content-type': 'application/json'}
      response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
      statusCode = response.status_code
      if statusCode == 204:
        print("\n- PASS, Command passed to power OFF server, code return is %s" % statusCode)
      else:
        print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
      time.sleep(10)
      payload = {'ResetType': 'On'}
      headers = {'content-type': 'application/json'}
      response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
      statusCode = response.status_code
      if statusCode == 204:
        print("\n- PASS, Command passed to power ON server, code return is %s" % statusCode)
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
        print("\n- PASS, Command passed to power ON server, code return is %s" % statusCode)
      else:
        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    print("\n- Flag will now be set during POST and server will onetime boot to device \"%s\"" % args.o)
  elif args.r == "n":
    print("\n- User selected to not reboot the server now but next boot onetime boot is still set to \"%s\" which will occur on next server reboot." % args.o)
    sys.exit()



### Run code

if __name__ == "__main__":
  get_current_setting_next_boot_supported_values()
  set_next_boot_onetime_boot_device()
  reboot_server()




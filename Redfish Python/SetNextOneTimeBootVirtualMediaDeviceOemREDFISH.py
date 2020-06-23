#
# SetNextOneTimeBootVirtualMediaDeviceOemREDFISH. Python script using Redfish API with OEM extension to set next onetime boot device to either virtual optical or virtual floppy.
#
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to set next onetime boot device to either virtual optical or virtual floppy.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SetNextOneTimeBootVirtualMediaDeviceOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -d 1 -r y, this example will set next next ontime boot device to virtual cd and reboot now')
parser.add_argument('-d', help='Pass in \"1\" to set next onetime boot device to virtual cd. Pass in \"2\" to set next onetime boot device to virtual floppy', required=True)
parser.add_argument('-r', help='Pass in \"y\" if you want the server to reboot now once you set next boot onetime boot device or \"n\" to not reboot now', required=True)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def set_next_onetime_boot_device_virtual_media():    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    if args["d"] == "1":
        payload = {"ShareParameters":{"Target":"ALL"},"ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"ServerBoot.1#BootOnce\">Enabled</Attribute><Attribute Name=\"ServerBoot.1#FirstBootDevice\">VCD-DVD</Attribute></Component></SystemConfiguration>"}
        print("\n- WARNING, setting next onetime boot device to Virtual CD")
    elif args["d"] == "2":
        payload = {"ShareParameters":{"Target":"ALL"},"ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"ServerBoot.1#BootOnce\">Enabled</Attribute><Attribute Name=\"ServerBoot.1#FirstBootDevice\">vFDD</Attribute></Component></SystemConfiguration>"}
        print("\n- WARNING, setting next onetime boot device to Virtual Floppy")
    else:
        print("\n- FAIL, invalid value passed in for argument -d")
        sys.exit()
    
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    response_dict=str(response.__dict__)
    try:
        job_id_search=re.search("JID_.+?,",response_dict).group()
    except:
        print("\n- FAIL: status code %s returned" % response.status_code)
        print("- Detailed error information: %s" % response_dict)
        sys.exit()

    job_id=re.sub("[,']","",job_id_search)
    if response.status_code != 202:
        print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code)  
        sys.exit()
    else:
        pass
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        current_time=(datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            pass
            time.sleep(3)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in data[u'Oem'][u'Dell'][u'Message'] or "completed with errors" in data[u'Oem'][u'Dell'][u'Message'] or "Not one" in data[u'Oem'][u'Dell'][u'Message'] or "not compliant" in data[u'Oem'][u'Dell'][u'Message'] or "Unable" in data[u'Oem'][u'Dell'][u'Message'] or "The system could not be shut down" in data[u'Oem'][u'Dell'][u'Message'] or "timed out" in data[u'Oem'][u'Dell'][u'Message']:
            print("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data[u'Oem'][u'Dell'][u'JobState']))
            print("- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- Config results for job ID %s\n" % job_id)
            for i in data['Messages']:
                    for ii in i.items():
                        if ii[0] == "Oem":
                            print("-" * 80)
                            for iii in ii[1]['Dell'].items():
                                print("%s: %s" % (iii[0], iii[1]))
                        else:
                            pass
        elif "No changes" in data[u'Oem'][u'Dell'][u'Message']:
            if args["d"] == "1":
                print("- WARNING, next onetime boot device already set to Virtual CD, no changes applied")
            elif args["d"] == "2":
                print("- WARNING, next onetime boot device already set to Virtual Floppy, no changes applied")
            break
        elif "Successfully imported" in data[u'Oem'][u'Dell'][u'Message'] or "completed with errors" in data[u'Oem'][u'Dell'][u'Message'] or "Successfully imported" in data[u'Oem'][u'Dell'][u'Message']:
            if args["d"] == "1":
                print("- PASS, successfully set next onetime boot device to Virtual CD")
            elif args["d"] == "2":
                print("- PASS, successfully set next onetime boot device to Virtual Floppy")
            break
        else:
            time.sleep(1)
            continue


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
            print("- PASS, Command passed to gracefully power OFF server, %s status code returned" % statusCode)
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
                    print("- PASS, Command passed to forcefully power OFF server, %s status code returned" % statusCode)
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
            print("- PASS, Command passed to power ON server, %s status code returned" % statusCode)
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
            print("- PASS, Command passed to power ON server, %s status code returned" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()

        
if __name__ == "__main__":
    if args["d"] and args["r"]:
        set_next_onetime_boot_device_virtual_media()
        if args["r"] == "n":
            print("- WARNING, no reboot selected for -r argument. Onetime boot will be applied on next manual server reboot")
            sys.exit()
        elif args["r"] == "y":
            reboot_server()
            if args["d"] == "1":
                print("- WARNING, System will now reboot and onetime boot to Virtual CD after POST")
            elif args["d"] == "2":
                print("- WARNING, System will now reboot and onetime boot to Virtual Floppy after POST")
        else:
            print("- FAIL, invalid value passed in for -r argument. Check script help for supported values")
            sys.exit()
    else:
        print("\n- FAIL, either missing or invalid parameter(s) passed in. If needed, see script help text for supported parameters and script examples")

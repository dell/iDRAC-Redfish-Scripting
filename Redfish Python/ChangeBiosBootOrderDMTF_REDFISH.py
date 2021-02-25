#
# ChangeBiosBootOrderDMTF_REDFISH. Python script using Redfish API DMTF standard to change the BIOS boot order
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 9.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF standard to change the BIOS boot order. Script will perform a server reboot which is required to apply these changes.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ChangeBiosBootOrderDMTF_REDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get the current boot order. ChangeBiosBootOrderDMTF_REDFISH.py -ip 192.168.0.120 -u root -p calvin -c Boot000A, Boot0002, this example will change the boot order and set Boot000A as first device, Boot0002 as second device in the boot order. NOTE: This example shows using iDRAC 4.00. ChangeBiosBootOrderDMTF_REDFISH.py -ip 192.168.0.120 -u root -p calvin -c HardDisk.List.1-1, this example will set HD as first device in the boot order. NOTE: This example is using iDRAC 4.40.')
parser.add_argument('-g', help='Get current boot order, pass in \"y\"', required=False)
parser.add_argument('-c', help='Change boot order, pass in the ID of the boot device(s). You can pass in one, multiple or all. If you only pass in one device Id, the rest of the boot order will get moved down. Note: If you pass in multiple, use a comma separator. Examples: Boot0004,Boot0005,Boot0006 (iDRAC 4.00) or HardDisk.List.1-1,Disk.SDInternal.1-1 (iDRAC 4.40). Before changing the boot order, recommended to get the current boot order first to get the correct ID strings for your iDRAC version.', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_current_boot_order():
    while True:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200 or response.status_code == 202:
            data = response.json()
            if "Attributes" in data.keys():
                break
            elif count == 5:
                print("- WARNING, GET command failed to locate \"Attributes\" key in output, script will exit")
                sys.exit()
            else:
                print("- INFO, \"Attribute\" key is not found in GET output, retry")
                time.sleep(10)
                count+=1
                continue
    current_boot_mode=data['Attributes']['BootMode']
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    boot_device_display_name = ""
    boot_device_id = ""
    count = 0
    print("\n- Current boot order detected for BIOS boot mode \"%s\" -\n" % current_boot_mode)
    if data["Members"] == []:
        print("- WARNING, no boot devices detected for BIOS boot mode %s" % current_boot_mode)
        sys.exit()
    for i in data['Members']:
        for ii in i.items():
            response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            for i in data.items():
                if i[0] == "DisplayName":
                    boot_device_display_name = i[1]
                if i[0] == "Id":
                    boot_device_id = i[1]
            if boot_device_display_name != "" and boot_device_id != "":
                print("SequenceNumber: %s, DisplayName: %s, Id: %s" % (count, boot_device_display_name, boot_device_id))
                count+=1
    sys.exit()
    
    
def change_boot_order():
    global job_id
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    current_boot_mode=data['Attributes']['BootMode']
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip
    if "," in args["c"]:
        boot_order_ids = args["c"].split(",")
    else:
        boot_order_ids = [args["c"]]
    payload = {"Boot":{"BootOrder":boot_order_ids}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    status_code = response.status_code
    data = response.json()
    if status_code == 200 or status_code == 202:
        print("\n- PASS: PATCH command passed to change %s boot order sequence" % current_boot_mode)
    else:
        print("\n- FAIL, PATCH command failed to change %s boot order sequence, status code is %s" % (current_boot_mode, status_code))
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers PATCH response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID \"%s\" successfully created to change %s boot order sequence" % (job_id, current_boot_mode))
    
def get_job_status_scheduled():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data['Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            print("- INFO: job status not scheduled, current status: %s" % data['Message'])                                                                      

def reboot_server():
    count = 1
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to attempt gracefully power OFF server, status code %s returned" % statusCode)
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            if count == 5:
                print("- INFO, server still in ON state after 5 minutes, will force OFF server")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, Command passed to force power OFF server, status code %s returned" % statusCode)
                    return
                else:
                    print("\n- FAIL, Command failed to force power OFF server, status code is: %s\n" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
                
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            else:
                print("- WARNING, server power state still ON, will wait for 5 minutes before forcing server power off")
                count+=1
                time.sleep(60)
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code %s returned" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
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
    

   

def loop_job_status_final():
    start_time=datetime.now()
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            if "Max retries exceeded with url" in str(error_message):
                print("- INFO, max retries exceeded with URL error, retry GET command")
                time.sleep(10)
                continue
            else:
                print("- WARNING, GET command failed to get job status. Detail error results: %s" % error_message)
                sys.exit()   
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n- Final detailed job results -")
            print("\n JobID = "+data['Id'])
            print(" Name = "+data['Name'])
            print(" Message = "+data['Message'])
            print(" PercentComplete = "+str(data['PercentComplete'])+"\n")
            break
        else:
            print("- INFO, job status not complete, current status: \"%s\"" % data['Message'])
            time.sleep(30)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_current_boot_order()
    elif args["c"]:
        change_boot_order()
        get_job_status_scheduled()
        reboot_server()
        loop_job_status_final()
        get_current_boot_order()



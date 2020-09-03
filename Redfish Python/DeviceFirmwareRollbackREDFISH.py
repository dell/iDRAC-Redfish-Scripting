#
# DeviceFirmwareRollbackREDFISH. Python script using Redfish API with OEM extension to rollback firmware for a device iDRAC supports. 
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

import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")



parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to rollback firmware for a device iDRAC supports")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareRollbackREDFISH.py -ip 192.168.0.120 -u root -p calvin -gr y, this example will return devices which support rollback. DeviceFirmwareRollbackREDFISH.py -ip 192.168.0.120 -u root -p calvin -r /redfish/v1/UpdateService/FirmwareInventory/Previous-159-2.7.7, this example will rollback BIOS to version 2.7.7.') 
parser.add_argument('-gf', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-gr', help='Get current PREVIOUS URI entries for rollback support, pass in \"y\"', required=False)
parser.add_argument('-r', help='Pass in the PREVIOUS URI entry you want to rollback the firmware. If needed, use argument -gr to get this URI.', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]



def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, iDRAC version detected does not support this feature, status code %s returned" % response.status_code)
        sys.exit()


def get_rollback_entires():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    previous_devices=[]
    data = req.json()
    for i in data["Members"]:
        for ii in i.items():
            if "Previous" in ii[1]:
                previous_devices.append(ii[1])
    if previous_devices == []:
        print("- WARNING, no PREVIOUS firmware images detected for rollback support")
        sys.exit()
    print("\n- Device(s) detected for rollback support -\n")
    for i in previous_devices:
        response = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        data = response.json()
        print("Name: %s" % data["Name"])
        print("Version: %s" % data["Version"])
        print("URI: %s" % i)
        print("\n")


def get_FW_inventory():
    print("\n- WARNING, getting current firmware inventory for iDRAC %s -\n" % idrac_ip)
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    installed_devices=[]
    data = req.json()
    for i in data['Members']:
        for ii in i.items():
            if ii[0] == "Oem":
                for iii in ii[1]["Dell"]["DellSoftwareInventory"].items():
                    if "odata" in iii[0]:
                        pass
                    else:
                        print("%s: %s" % (iii[0],iii[1]))
                
            elif "odata" in ii[0] or "Description" in ii[0]:
                pass
            else:
                print("%s: %s" % (ii[0],ii[1]))
        print("\n")

def rollback_fw():
    global job_id
    global start_time
    start_time=datetime.now()
    url = 'https://%s/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate' % (idrac_ip)
    payload = {"ImageURI":args["r"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        data = response.json()
        print("\n- FAIL, POST command failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()
    try:
        job_id = response.headers["Location"].split("/")[-1]
    except:
        print("- FAIL, unable to locate job ID in headers output")
        sys.exit()
    print("\n- PASS, rollback job ID \"%s\" successfully created" % job_id) 




def check_job_status():
    current_time = str(datetime.now()-start_time)[0:7]
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        if data["TaskState"] == "Completed":
            print("\n- PASS, job ID %s successfuly marked completed, detailed final job status results:\n" % data[u"Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        current_time = str(datetime.now()-start_time)[0:7]   
        statusCode = req.status_code
        data = req.json()
        message_string=data["Messages"]
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit()
        elif "failed" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Failed" in data['Oem']['Dell']['Message']:
            print("- FAIL: Job failed, current message is: %s" % data["Messages"])
            sys.exit()
        elif "scheduled" in data['Oem']['Dell']['Message']:
            print("\n- PASS, job ID %s successfully marked as scheduled, powering on or rebooting the server to apply the update" % data["Id"])
            break
        elif "completed successfully" in data['Oem']['Dell']['Message']:
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
        else:
            print("- INFO: %s, current job execution time is: %s" % (message_string[0]["Message"], current_time))
            time.sleep(1)
            continue

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
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
            if data['PowerState'] == "Off":
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
                    break
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


def loop_check_final_job_status():
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
        statusCode = req.status_code
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit()
        elif "Fail" in data['Oem']['Dell']['Message'] or "fail" in data['Oem']['Dell']['Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        
        elif "completed successfully" in data['Oem']['Dell']['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- INFO, job status not completed, current status: \"%s\", execution time: \"%s\"" % (data['Oem']['Dell']['Message'], current_time))
            time.sleep(20)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["gf"]:
        get_FW_inventory()
    elif args["gr"]:
        get_rollback_entires()
    elif args["r"]:
        rollback_fw()
        check_job_status()
        reboot_server()
        loop_check_final_job_status()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")







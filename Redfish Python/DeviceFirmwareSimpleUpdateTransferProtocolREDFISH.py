#
# DeviceFirmwareSimpleUpdateTransferProtocolREDFISH. Python script using Redfish API to update a device firmware with DMTF standard SimpleUpdate with TransferProtocol. Only supported file image type is Windows Dell Update Packages(DUPs).
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

import requests, json, sys, re, time, warnings, argparse, os, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

# Code to validate all correct parameters are passed in

parser=argparse.ArgumentParser(description="Python script using Redfish API to update device firmware using DMTF standard SimpleUpdate with TransferProtocol. Only supported file image type is Windows Dell Update Packages(DUPs)")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareSimpleUpdateTransferProtocolREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will return current firmware versions for all devices supported for updates. DeviceFirmwareSimpleUpdateTransferProtocolREDFISH.py -ip 192.168.0.120 -u root -p calvin -T HTTP --uri http://192.168.0.130/updates_http/CPLD_Firmware_WN64_1.0.2_A00.EXE -r y, this example will reboot the server now and update CPLD firmware using HTTP share') 
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get current supported transfer protocols for SimpleUpdate action, pass in \"y\"', required=False)
parser.add_argument('--uri', help='Pass in the complete URI path of the network share along with the firmware image name', required=False)
parser.add_argument('-t', help='Pass in the transfer protocol type you are using for the URI path.', required=False)
parser.add_argument('-r', help='Reboot type, pass in \"y\" if you want the server to reboot now to apply the update or \"n\" to not reboot the server now. If you select \"n\", job will still get scheduled but won\'t be applied until next manual server reboot. Note: This option is only required for devices that need a server reboot to apply the update. If updating iDRAC, DIAGS, ISM, USC or Driver Pack, this option is not needed.', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    try:
        for i in data[u'Actions'][u'#UpdateService.SimpleUpdate'][u'TransferProtocol@Redfish.AllowableValues']:
            pass
    except:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    

def check_idrac_lost_connection():
    while True:
        ping_command = "ping %s -n 2" % idrac_ip
        ping_output = subprocess.Popen(ping_command, stdout = subprocess.PIPE, shell=True).communicate()[0]
        ping_results = re.search("Lost = .", ping_output).group()
        if ping_results == "Lost = 0":
            break
        else:
            print("\n- WARNING, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
            time.sleep(180)
    
def get_FW_inventory():
    print("\n- WARNING, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    installed_devices=[]
    data = req.json()
    for i in data[u'Members']:
        for ii in i.items():
            if "Installed" in ii[1]:
                installed_devices.append(ii[1])
    for i in installed_devices:
        req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        updateable_status = data[u'Updateable']
        version = data[u'Version']
        device_name = data[u'Name']
        print("Device Name: %s, Firmware Version: %s, Updatable: %s" % (device_name, version, updateable_status))
    sys.exit()

def get_supported_protocols():
    req = requests.get('https://%s/redfish/v1/UpdateService' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    installed_devices=[]
    data = req.json()
    print("\n- Supported protocols for TransferProtocol parameter (-t argument) -\n")
    try:
        for i in data[u'Actions'][u'#UpdateService.SimpleUpdate'][u'TransferProtocol@Redfish.AllowableValues']:
            print(i)
    except:
        print("- FAIL, unable to retrieve supported protocols")
        sys.exit()
    
def install_image_payload():
    global job_id
    url = 'https://%s/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate' % (idrac_ip)
    payload = {"ImageURI":args["uri"], "TransferProtocol":args["t"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
            pass
    else:
        print("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    job_id_location = response.headers['Location']
    job_id = re.search("JID_.+",job_id_location).group()
    print("\n- PASS, %s firmware update job ID successfully created for update image \"%s\"" % (job_id, args["uri"].split("/")[-1]))


def check_job_status():
    global start_time
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        if data[u"TaskState"] == "Completed":
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data[u"Id"])
            for i in data[u'Oem'][u'Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        current_time = str(datetime.now()-start_time)[0:7]   
        statusCode = req.status_code
        data = req.json()
        message_string=data[u"Messages"]
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit()
        elif "failed" in data[u'Oem'][u'Dell'][u'Message'] or "completed with errors" in data[u'Oem'][u'Dell'][u'Message'] or "Failed" in data[u'Oem'][u'Dell'][u'Message'] or "internal error" in data[u'Oem'][u'Dell'][u'Message']:
            print("- FAIL: Job failed, current message is: %s" % data[u"Messages"])
            sys.exit()
        elif "scheduled" in data[u'Oem'][u'Dell'][u'Message']:
            break
        elif "completed successfully" in data[u'Oem'][u'Dell'][u'Message']:
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data[u"Id"])
            for i in data[u'Oem'][u'Dell'].items():
                if i[0] == "Name":
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            print("- Message: %s, current job execution time is: %s" % (message_string[0][u"Message"], current_time))
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
    elif data[u'PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
            time.sleep(30)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()


def loop_check_final_job_status():
    while True:
        check_idrac_lost_connection()
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
        elif "Fail" in data[u'Oem'][u'Dell'][u'Message'] or "fail" in data[u'Oem'][u'Dell'][u'Message'] or "Unable" in data[u'Oem'][u'Dell'][u'Message']:
            print("- FAIL: %s failed, error message: %s" % (job_id, data[u'Oem'][u'Dell'][u'Message']))
            sys.exit()
        
        elif "completed successfully" in data[u'Oem'][u'Dell'][u'Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data[u'Oem'][u'Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", job execution time is \"%s\"" % (data[u'Oem'][u'Dell'][u'Message'], current_time))
            time.sleep(10)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["s"]:
        get_supported_protocols()
    elif args["uri"] and args["t"]:
        install_image_payload()
        check_job_status()
        if args["r"] == "y":
            print("\n- PASS, job ID successfully marked as scheduled, powering on or rebooting the server to apply the update")
            reboot_server()
            loop_check_final_job_status()
        elif args["r"] == "n":
            print("\n- WARNING, user selected to not reboot the server to apply the update. Update job is still scheduled and will be applied on next server reboot")
            sys.exit()
        else:
            print("\n- WARNING, argument -r is missing, update job is scehduled but server did not reboot. To apply the update, reboot the server")
    else:
        print("\n- FAIL, incorrect parameter(s) passed in or missing required parameters")







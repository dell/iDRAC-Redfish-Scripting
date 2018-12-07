#
# DeviceFirmwareSimpleUpdateREDFISH. Python script using Redfish API to update a device firmware with DMTF action SimpleUpdate. Supported file image types are Windows DUPs, d7/d9 image or pm files.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 6.0
#
# Copyright (c) 2018, Dell, Inc.
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

# Code to validate all correct parameters are passed in

parser=argparse.ArgumentParser(description="Python script using Redfish API to update device firmware using DMTF standard action SimpleUpdate from a local directory")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareSimpleUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will return current firmware versions for all devices supported for updates. DeviceFirmwareSimpleUpdateREDFISH.py -ip 192.168.0.120 -u root -p calvin -l C:\Python27 -f BIOS_422T0_WN64_1.4.9.EXE, this example will update BIOS firmware which BIOS DUP is located in C:\Python27 directory') 
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-l', help='Pass in the local directory location of the firmware image', required=False)
parser.add_argument('-f', help='Pass in the firmware image name', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass
    
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
    

def download_image_payload():
    global available_entry
    global http_push_uri
    print("\n- WARNING, downloading \"%s\" image, this may take a few minutes depending on the size of the image" % args["f"])
    req = requests.get('https://%s/redfish/v1/UpdateService/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    http_push_uri = data[u'HttpPushUri']
    req = requests.get('https://%s%s' % (idrac_ip, http_push_uri), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    ImageLocation = args["l"]
    filename = args["f"]
    ImagePath = os.path.join(ImageLocation, filename)
    ETag = req.headers['ETag']
    url = 'https://%s%s' % (idrac_ip, http_push_uri)
    files = {'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    headers = {"if-match": ETag}
    response = requests.post(url, files=files, auth = (idrac_username, idrac_password), verify=False, headers=headers)
    post_command_response_output=response.json()
    if response.status_code == 201:
        print("\n- PASS: POST command passed successfully to download image, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL: POST command failed to download image payload, status code is %s, error is %s" % (response.status_code, response))
        print("\nMore details on status code error: %s " % post_command_response_output)
        sys.exit()
    available_entry = post_command_response_output[u'Id']
    print("- WARNING, AVAILABLE entry created for download image \"%s\" is \"%s\"" % (filename, available_entry))
    

    

def install_image_payload():
    global job_id
    url = 'https://%s/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate' % (idrac_ip)
    payload = {"ImageURI":"%s/%s" % (http_push_uri, available_entry)}
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
    print("- PASS, %s firmware update job ID successfully created" % job_id)


def check_job_status():
    global start_time
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        if data[u"TaskState"] == "Completed":
            print("\n- PASS, job ID %s successfuly marked completed, detailed final job status results:\n" % data[u"Id"])
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
        elif "failed" in data[u'Oem'][u'Dell'][u'Message'] or "completed with errors" in data[u'Oem'][u'Dell'][u'Message'] or "Failed" in data[u'Oem'][u'Dell'][u'Message']:
            print("- FAIL: Job failed, current message is: %s" % data[u"Messages"])
            sys.exit()
        elif "scheduled" in data[u'Oem'][u'Dell'][u'Message']:
            print("\n- PASS, job ID %s successfully marked as scheduled, powering on or rebooting the server to apply the update" % data[u"Id"])
            break
        elif "completed successfully" in data[u'Oem'][u'Dell'][u'Message']:
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data[u"Id"])
            for i in data[u'Oem'][u'Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            if "d9" in args["f"] or "d8" in args["f"] or "d7" in args["f"]:
                print("- Message: Downloading package \"%s\"" % args["f"])
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
        elif "Fail" in data[u'Oem'][u'Dell'][u'Message'] or "fail" in data[u'Oem'][u'Dell'][u'Message']:
            print("- FAIL: %s failed" % job_id)
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
            time.sleep(20)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["l"] and args["f"]:
        download_image_payload()    
        install_image_payload()
        check_job_status()
        reboot_server()
        loop_check_final_job_status()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")







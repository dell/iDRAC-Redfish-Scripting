#
# DeviceFirmwareSimpleUpdateREDFISH. Python script using Redfish API to update a device firmware with DMTF action SimpleUpdate. Supported file image types are Windows DUPs, d7/d9 image or pm files.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 17.0
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

import requests, json, sys, re, time, warnings, argparse, os, subprocess, platform

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
parser.add_argument('-r', help='Reboot the server to apply the update if needed. Pass in \"n\" to reboot the server now to run the update or pass in \"l\" to not reboot the server (job ID will still be in scheduled state and will execute on next manual server reboot. Note: If the update gets applied with no server reboot (Example: iDRAC, DIAGs, Driver pack), you don\'t need to pass in this argument. For more details on which devices update immediately, refer to Lifecycle Controller User Guide Update section.', required=False)
parser.add_argument('-S', help='Shutdown the server once the firmware update completes, pass in \"y\"', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]




def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(1)
    elif response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(1)
    else:
        pass

def get_idrac_version():
    global idrac_fw_version
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, GET request failed to get iDRAC firmware version, error: \n%s" % data)
        sys.exit(1)
    idrac_fw_version = data["FirmwareVersion"].replace(".","")
    
def get_FW_inventory():
    print("\n- INFO, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    installed_devices=[]
    data = req.json()
    for i in data['Members']:
        for ii in i.items():
            if "Installed" in ii[1]:
                installed_devices.append(ii[1])
    for i in installed_devices:
        req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        try:
            updateable_status = data['Updateable']
            version = data['Version']
            device_name = data['Name']
            print("Device Name: %s, Firmware Version: %s, Updatable: %s" % (device_name, version, updateable_status))
        except:
            print("- INFO, unable to get property info for URI: \"%s\"" % i)
    sys.exit(1)
    

def download_image_payload():
    global available_entry
    global http_push_uri
    global start_time
    start_time=datetime.now()
    print("\n- INFO, downloading \"%s\" image, this may take a few minutes depending on the size of the image" % args["f"])
    req = requests.get('https://%s/redfish/v1/UpdateService/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    http_push_uri = data['HttpPushUri']
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
        print("\n- PASS: POST command passed successfully to download image")
    else:
        print("\n- FAIL: POST command failed to download image payload, status code:%s, error:%s" % (response.status_code, response))
        print("\nMore details on status code error: %s " % post_command_response_output)
        sys.exit(1)
    available_entry = post_command_response_output['Id']
    print("- INFO, AVAILABLE entry created for download image \"%s\" is \"%s\"" % (filename, available_entry))
    

    

def install_image_payload():
    global job_id
    url = 'https://%s/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate' % (idrac_ip)
    if args["r"] == "n":
        payload = {"ImageURI":"%s/%s" % (http_push_uri, available_entry),"@Redfish.OperationApplyTime": "Immediate"}
    elif args["r"] == "l":
        payload = {"ImageURI":"%s/%s" % (http_push_uri, available_entry),"@Redfish.OperationApplyTime": "OnReset"}    
    else:
        payload = {"ImageURI":"%s/%s" % (http_push_uri, available_entry)}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
            pass
    else:
        print("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit(1)
    job_id_location = response.headers['Location']
    job_id = re.search("JID_.+",job_id_location).group()
    print("- PASS, %s firmware update job ID successfully created" % job_id)


def check_job_status():
    retry_count = 1
    while True:
        check_idrac_connection()
        if retry_count == 20:
            print("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit()
        try:
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- INFO, GET request failed due to connection error, retry")
            time.sleep(10)
            retry_count+=1
            continue
        statusCode = req.status_code
        data = req.json()
        if "device is already present" in data["Messages"][0]["Message"]:
            print("- WARNING, update job for this device is already present, check iDRAC job queue")
            sys.exit(1)
        if data["TaskStatus"] == "Critical" or data["TaskStatus"] == "Warning":
            print("- WARNING, job completed but failure detected, detailed final job status results:\n%s" % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
        if data["TaskState"] == "Completed":
            print("\n- PASS, job ID successfuly marked completed, detailed final job status results:\n%s " % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            if args["S"]:
                shutdown_server()
                sys.exit()
            else:
                sys.exit()
        current_time = str(datetime.now()-start_time)[0:7]   
        statusCode = req.status_code
        data = req.json()
        message_string=data["Messages"]
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit(1)
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, update job should of already been marked completed. Check the iDRAC job queue and LC logs to debug the issue\n")
            sys.exit(1)
        elif "failed" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Failed" in data['Oem']['Dell']['Message']:
            print("- FAIL: Job failed, current message is: %s" % data["Messages"])
            sys.exit(1)
        elif "scheduled" in data['Oem']['Dell']['Message']:
            print("- PASS, job ID %s successfully marked as scheduled" % data["Id"])
            if not args["r"]:
                print("- WARNING, missing argument -r for rebooting the server. Job is still scheduled and will be applied on next manual server reboot")
                sys.exit()
            elif args["r"] == "l":
                print("- INFO, user selected to not reboot the server now. Update job is still scheduled and will execute on next manual server reboot.")
                sys.exit()
            else:
                pass
            break
        elif "completed successfully" in data['Oem']['Dell']['Message']:
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            break
        else:
            print("- INFO, %s, execution time: %s" % (message_string[0]["Message"].rstrip("."), current_time))
            time.sleep(1)
            continue


def loop_check_final_job_status():
    retry_count = 1
    while True:
        if retry_count == 20:
            print("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit()
        check_idrac_connection()
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- INFO, GET request failed due to connection error, retry")
            time.sleep(10)
            retry_count+=1
            continue
        current_time=str((datetime.now()-start_time))[0:7]
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit(1)
        data = req.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit(1)
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            print("- FAIL: %s failed" % job_id)
            sys.exit(1)
        
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            if args["S"]:
                shutdown_server()
                break
            else:
                break
        else:
            print("- INFO, job ID not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'].rstrip("."), current_time))
            time.sleep(1)

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to gracefully power OFF server")
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code: %s\n" % statusCode)
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
                print("- INFO, unable to graceful shutdown the server, will perform forced shutdown now")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, Command passed to forcefully power OFF server")
                    time.sleep(15)
                    break
                else:
                    print("\n- FAIL, Command failed to gracefully power OFF server, status code: %s\n" % statusCode)
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
            print("- PASS, Command passed to power ON server")
        else:
            print("\n- FAIL, Command failed to power ON server, status code: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server")
        else:
            print("\n- FAIL, Command failed to power ON server, status code: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()

def check_idrac_connection():
    run_network_connection_function = ""
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        print("- FAIL, unable to determine OS type, check iDRAC connection function will not execute")
        run_network_connection_function = "fail"
    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
    if execute_command != 0:
        ping_status = "lost"
    else:
        ping_status = "good"
        pass
    if ping_status == "lost":
            print("- INFO, iDRAC network connection lost due to slow network response, waiting 30 seconds to access iDRAC again")
            time.sleep(60)
            while True:
                if run_network_connection_function == "fail":
                    break
                execute_command=subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
                if execute_command != 0:
                    ping_status = "lost"
                else:
                    ping_status = "good"
                if ping_status == "lost":
                    print("- INFO, unable to ping iDRAC IP, script will wait 30 seconds and try again")
                    time.sleep(30)
                    continue
                else:
                    pass
                    break
            while True:
                try:
                    req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
                except requests.ConnectionError as error_message:
                    print("- INFO, GET request failed due to connection error, retry")
                    time.sleep(10)
                    continue
                break
    else:
        pass

def shutdown_server():
    print("- INFO, argument -S detected to shutdown the server after firmware update completes")
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': 'ForceOff'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("- PASS, POST action passed to power OFF server")
    else:
        print("\n- FAIL, POST action failed to power OFF server, status code: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
        


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["l"] and args["f"]:
        get_idrac_version()
        download_image_payload()
        install_image_payload()
        check_job_status()
        if args["r"] == "n":
            if int(idrac_fw_version[0]) >= 5:
                loop_check_final_job_status()
            else:
                print("- INFO, older iDRAC version detected, execute action ComputerSystem.Reset to reboot the server")
                reboot_server()
                loop_check_final_job_status()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")







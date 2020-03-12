#!/usr/bin/python
# DeviceFirmwareDellUpdateServiceREDFISH. Python script using Redfish API to update a device firmware using OEM action DellUpdateService.Install. Supported file image types are Windows DUPs, d7/d9 image or pm files.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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

import requests, json, sys, re, time, warnings, subprocess, argparse, os, platform


from datetime import datetime

warnings.filterwarnings("ignore")

# Code to validate all correct parameters are passed in

parser=argparse.ArgumentParser(description="Python script using Redfish API to update device firmware using OEM action DellUpdateService.Install from a local directory")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareDellUpdateServiceREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will return current firmware versions for all devices supported for updates. DeviceFirmwareDellUpdateServiceREDFISH.py -ip 192.168.0.120 -u root -p calvin -l C:\Python27\master_scripts_modified -f BIOS_MWY16_WN64_1.6.4.EXE -i NowAndReboot, this example will update BIOS firmware now using BIOS DUP is located in C:\Python27 directory') 
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-l', help='Pass in the local directory location of the firmware image', required=False)
parser.add_argument('-f', help='Pass in the firmware image name', required=False)
parser.add_argument('-i', help='Pass in the install option. Supported values are \"Now\", \"NowAndReboot\", \"NextReboot\". NOTE: If you are updating a device which doesn\'t need a server reboot to apply the update (Example: iDRAC, DIAGS, Driver Pack, ISM, OSC), pass in a value of Now. All other devices which require a server reboot to apply the update (BIOS, CPLD, NIC, PERC, PSU, FC, HDs, Backplane), pass in NowAndReboot or NextReboot', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

if args["l"]:
    firmware_image_location = args["l"]
if args["f"]:
    file_image_name = args["f"]
if args["i"]:
    install_option = args["i"]

start_time=datetime.now()

# Function to check if current iDRAC version supports Redfish firmware features

def check_idrac_fw_support():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 200 or statusCode == 202:
        pass
    else:
        print("\n- WARNING, current server iDRAC version does not support Redfish firmware features. Refer to Dell online Redfish documentation for information on which iDRAC version supports firmware features.")
        sys.exit()

# Function to get current firmware versions

def get_FW_inventory():
    print("\n- WARNING, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 200 or statusCode == 202:
        pass
    else:
        print("- FAIL, GET request failed to get iDRAC firmware inventory")
        sys.exit()
    data = req.json()
    installed_devices=[]
    for i in data['Members']:
        for ii in i.items():
            if "Installed" in ii[1]:
                installed_devices.append(ii[1])
    for i in installed_devices:
        req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        updateable_status = data['Updateable']
        version = data['Version']
        device_name = data['Name']
        print("Device Name: %s, Firmware Version: %s, Updatable: %s" % (device_name, version, updateable_status))
    sys.exit()
    
# Function to download the image payload to the iDRAC

def download_image_payload():
    print("\n- WARNING, downloading \"%s\" image payload to iDRAC" % file_image_name)
    global Location
    global new_FW_version
    global dup_version
    global ETag
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 200 or statusCode == 202:
        pass
    else:
        print("- FAIL, GET request failed to get iDRAC firmware inventory information for downloading payload image")
        sys.exit()
    data = req.json()
    filename = file_image_name
    ImageLocation = firmware_image_location
    ImagePath = os.path.join(ImageLocation, filename)
    ETag = req.headers['ETag']
    url = 'https://%s/redfish/v1/UpdateService/FirmwareInventory' % (idrac_ip)
    files = {'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    headers = {"if-match": ETag}
    try:
        response = requests.post(url, files=files, auth = (idrac_username, idrac_password), verify=False, headers=headers)
    except requests.ConnectionError as error_message:
        print("- WARNING, POST command to download payload failed for connection error")
        sys.exit()
    create_dict = response.__dict__
    string_content=str(create_dict['_content'])
    if response.status_code == 201:
        print("\n- PASS: POST command passed to download image payload to iDRAC, 201 status code returned")
    else:
        print("\n- FAIL: POST command failed to download image payload, error is %s" % response)
        print("\nMore details on status code error: %s " % create_dict['_content'])
        sys.exit()
    #d = response.__dict__
    avilable_entry = re.search("Available.+?,",string_content).group()
    avilable_entry = re.sub('[",]',"",avilable_entry)
    new_FW_version = re.sub('Available','Installed',avilable_entry)
    avilable_entry_strip = avilable_entry.find("-")
    avilable_entry_strip = avilable_entry.find("-",avilable_entry_strip+1)
    dup_version = avilable_entry[avilable_entry_strip+1:]
    print("- Firmware image version of downloaded payload is: %s" % dup_version)
    Location = response.headers['Location']

# Function to install the downloaded image payload and loop checking job status

def install_image_payload():
    global job_id
    print("\n- WARNING, executing POST command to create firmware update job ID")
    url = 'https://%s/redfish/v1/UpdateService/Actions/Oem/DellUpdateService.Install' % (idrac_ip)
    InstallOption = install_option
    payload = "{\"SoftwareIdentityURIs\":[\"" + Location + "\"],\"InstallUpon\":\""+ InstallOption +"\"}"
    headers = {'content-type': 'application/json'}
    try:
        response = requests.post(url, data=payload, auth = (idrac_username, idrac_password), verify=False, headers=headers)
    except requests.ConnectionError as error_message:
        print("- WARNING, POST command to install downloaded payload failed for connection error")
        sys.exit()
    #d=str(response.__dict__)
    job_id_location = response.headers['Location']
    job_id = re.search("JID_.+",job_id_location).group()
    print("- PASS, %s firmware update job ID successfully created" % job_id)
    
# Function to check the new FW version installed

def check_new_FW_version():
    get_remote_service_api_status()
    if ".pm" in file_image_name:
        pass
    else:
        print("\n- WARNING, checking new firmware version installed for updated device")
        while True:
            try:
                req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, new_FW_version), auth=(idrac_username, idrac_password), verify=False)
                break
            except requests.ConnectionError as error_message:
                print("- WARNING, GET request failed due to connection error, retry")
                time.sleep(10)
                continue
        statusCode = req.status_code
        data = req.json()
        if dup_version == data['Version']:
            print("\n- PASS, New installed firmware version is: %s" % data['Version'])
        else:
            print("\n- FAIL, New installed firmware version incorrect, error is: %s" % data)
            sys.exit()


# Function to check network connection for iDRAC update 

def check_idrac_connection():
    #print("- WARNING, executing PING request to validate successful communication with iDRAC")
    if platform.system().lower() == "windows":
        ping_command = "ping -n 3 %s" % idrac_ip
    elif platform.system().lower() == "linux":
        ping_command = "ping -c 3 %s" % idrac_ip
    else:
        print("- FAIL, unable to determine OS type")
        sys.exit()
    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
    if execute_command != 0:
        ping_status = "lost"
    else:
        ping_status = "good"
        #print("- PASS, successful PING request was made to iDRAC")
        pass
    if ping_status == "lost":
            print("- WARNING, iDRAC network connection lost due to slow network response or iDRAC reset to apply firmware update. Waiting 6 minutes to access iDRAC again")
            time.sleep(360)
            while True:
                execute_command=subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
                if execute_command != 0:
                    ping_status = "lost"
                else:
                    ping_status = "good"
                if ping_status == "lost":
                    print("- WARNING, unable to ping iDRAC IP, script will wait 1 minute and try again")
                    time.sleep(60)
                    continue
                else:
                    print("- PASS, successful ping reply to iDRAC IP")
                    break
            while True:
                try:
                    req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
                except requests.ConnectionError as error_message:
                    print("- WARNING, GET request failed due to connection error, retry")
                    time.sleep(10)
                    continue
                break
                
            statusCode = req.status_code
            data = req.json()
            if data["Name"] == "Firmware Update: iDRAC" or data["Name"] == "Firmware Update: iDRAC with Lifecycle Controller" or "iDRAC" in data["Name"]:
                if data["TaskState"] == "Completed":
                    print("\n- PASS, job ID %s successfuly marked completed, detailed final job status results:\n" % data["Id"])
                    for i in data['Oem']['Dell'].items():
                        print("%s: %s" % (i[0],i[1]))
                    check_new_FW_version()
                else:
                    print("\n- FAIL, job ID %s is not marked completed, current job status is: %s" % (job_id, data["TaskState"]))
                sys.exit()
            else:
                pass
    else:
        pass

# Function to check the job status for host reboot needed

def check_job_status_host_reboot():
    start_time=datetime.now()
    print("\n- WARNING, script will now loop checking the job status until marked completed\n")
    while True:
        check_idrac_connection()
        try:
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- WARNING, iDRAC network connection lost due to slow network response or iDRAC reset to apply firmware update. Waiting 6 minutes to access iDRAC again")
            time.sleep(360)
            continue
        current_time = str(datetime.now()-start_time)[0:7]   
        statusCode = req.status_code
        data = req.json()
        message_string=data["Messages"]
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in data["Messages"] or "completed with errors" in data["Messages"] or "Failed" in data["Messages"] or "already present" in data["Messages"]:
            print("- FAIL: Job failed, current message is: %s" % data["Messages"])
            sys.exit()
        elif data["TaskState"] == "Completed" and "already present" in message_string[0]["Message"]:
            print("- FAIL: Job failed, current message is: %s" % message_string[0]["Message"])
            sys.exit()
        elif data["TaskState"] == "Completed":
            print("\n- PASS, job ID %s successfully marked completed, detailed final job status results:\n" % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            if data["Name"] == "Firmware Update: iDRAC" or data["Name"] == "Firmware Update: iDRAC with Lifecycle Controller" or "iDRAC" in data["Name"]:
                print("\n- WARNING, iDRAC update detected. Script will wait 6 minutes for iDRAC to reset and come back up before checking new firmware version")
                time.sleep(360)
                while True:
                    if platform.system().lower() == "windows":
                        ping_command = "ping -n 3 %s" % idrac_ip
                    elif platform.system().lower() == "linux":
                        ping_command = "ping -c 3 %s" % idrac_ip
                    else:
                        print("- FAIL, unable to determine OS type")
                        sys.exit()
                    execute_command = subprocess.call(ping_command, stdout=subprocess.PIPE, shell=True)
                    if execute_command != 0:
                        ping_status = "lost"
                    else:
                        ping_status = "good"
                    if ping_status == "lost":
                        print("- WARNING, unable to ping iDRAC IP, script will wait 1 minute and try again")
                        time.sleep(60)
                        continue
                    else:
                        print("- PASS, successful ping reply to iDRAC IP")
                        return
            else:
                break
        elif data["TaskState"] == "Completed with Errors" or data["TaskState"] == "Failed":
            print("\n- Job ID = "+data["Id"])
            print("- Name = "+data["Name"])
            try:
                print("- Message = "+message_string[0]["Message"])
            except:
                print("- "+data["Messages"][0]["Message"])
            print("- JobStatus = "+data["TaskState"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            if "d9" in file_image_name or "d8" in file_image_name or "d7" in file_image_name:
                print("- Message: Downloading package \"%s\"" % file_image_name)
            else:
                print("- Message: %s, current job execution time is: %s" % (message_string[0]["Message"], current_time))
            if install_option == "NowAndReboot":
                time.sleep(60)
            else:
                time.sleep(1)

# Function to check job status for next manual reboot

def check_job_status():
    print("\n- WARNING, script will now loop checking the job status until either marked completed or scheduled for next manual reboot\n")
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- WARNING, GET request failed for connection error, retry")
            time.sleep(10)
            continue
        statusCode = req.status_code
        data = req.json()
        message_string=data["Messages"]
        current_time=(datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            time.sleep(10)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in data["Messages"] or "completed with errors" in data["Messages"]:
            print("- FAIL: Job failed, current message is: %s" % data["Messages"])
            sys.exit()
        elif data["TaskState"] == "Pending" or data["TaskState"] == "Starting":
            print("- PASS, job ID %s successfully marked as scheduled. Scheduled job completion time: %s" % (job_id, str(current_time)[0:7]))
            print("\n- WARNING, Host manual reboot is now needed to complete the process of applying the firmware image.\n")
            break
        elif data["TaskState"] == "Completed" and "already present" in message_string[0]["Message"]:
            print("- FAIL: Job failed, current message is: %s" % message_string[0]["Message"])
            break    
        elif data["TaskState"] == "Completed with Errors" or data["TaskState"] == "Failed":
            print("\n- Job ID = "+data["Id"])
            print("- Name = "+data["Name"])
            try:
                print("- Message = "+message_string[0]["Message"])
            except:
                print("- "+data["Messages"][0]["Message"])
            print("- JobStatus = "+data["TaskState"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        elif data["TaskState"] == "Completed":
            print("\n- WARNING, device selected is immediate update, incorrect install option passed in.")
            print("- %s still marked completed and firmware updated" % (job_id))
            break
        else:
            print("- Job not marked completed, current status is: %s" % data["TaskState"])
            print("- Message: %s" % message_string[0]["Message"])
            print("- Current job execution time is: %s\n" % str(current_time)[0:7])
            time.sleep(1)
            continue

def get_remote_service_api_status():
    start_time=datetime.now()
    print("\n- WARNING, checking server status")
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- WARNING, GET request failed, check to make sure you passed in correct iDRAC information or you can access the iDRAC")
            sys.exit()
        data = req.json()
        major_number = data['FirmwareVersion'].split(".")[0]
        minor_number = data['FirmwareVersion'].split(".")[1]
        idrac_version_verify = int(major_number+minor_number)
        if idrac_version_verify >= 330:
            while True:
                current_time=(datetime.now()-start_time)
                if str(current_time)[0:7] >= "0:10:00":
                    print("\n-FAIL, Timeout of 10 minutes has been reached before server status is marked as Ready")
                    return
                else:
                    pass
                url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
                method = "GetRemoteServicesAPIStatus"
                headers = {'content-type': 'application/json'}
                payload={}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
                if response.status_code == 200:
                    data=response.json()
                else:
                    print("\n-FAIL, POST command failed for GetRemoteServicesAPIStatus action, status code is %s" % (response.status_code))
                    data = response.json()
                    print("\n-POST command failure results:\n %s" % data)
                    return
                for i in data.items():
                    if i[0] == "Status":
                        if i[1] == "Ready":
                            print("- PASS, server status is ready")
                            return
                        else:
                            print("- WARNING, server status not ready, polling status again")
                            time.sleep(5)
                            continue
        else:
            print("- WARNING, iDRAC version detected does not support checking server status")
            return
        
    


# Run code

if __name__ == "__main__":
    get_remote_service_api_status()
    check_idrac_fw_support()
    if args["g"]:
        get_FW_inventory()
    if args["l"] and args["f"] and args["i"]:
        download_image_payload()
        install_image_payload()
        if install_option == "NowAndReboot" or install_option == "Now":
            check_job_status_host_reboot()
            check_new_FW_version()
        elif install_option == "NextReboot":
            check_job_status()
        else:
            print("- FAIL, invalid value entered for install_option parameter")
            sys.exit()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")



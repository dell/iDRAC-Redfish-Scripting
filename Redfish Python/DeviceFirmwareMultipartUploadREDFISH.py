#
# DeviceFirmwareMultipartUploadREDFISH.py. Python script using Redfish API to update a device firmware with DMTF MultipartUpload. Supported file image types are Windows DUPs, d7/d9 image or pm files.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import requests, json, sys, re, time, warnings, argparse, os, subprocess, platform

from datetime import datetime

warnings.filterwarnings("ignore")



parser=argparse.ArgumentParser(description="Python script using Redfish API to update a device firmware with DMTF MultipartUpload from a local directory")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareMultipartUploadREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get current firmware versions for all devices in the server. DeviceFirmwareMultipartUploadREDFISH.py -ip 192.168.0.120 -u root -p calvin -l C:\\Users\\administrator\\Downloads\\BIOS_8MRPC_C6420_WN64_2.11.2.EXE -r n, this example will reboot the server now to execute BIOS firmware update.') 
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-l', help='Pass in the full directory path location of the firmware image. Make sure to also pass in the name of the Dell Update package (DUP) executable, example: C:\\Users\\admin\\Downloads\\Diagnostics_Application_CH7FG_WN64_4301A42_4301.43.EXE', required=False)
parser.add_argument('-r', help='Pass in value for reboot type. Pass in \"n\" for server to reboot now to apply the update. Pass in \"l\" which will schedule the job but server will not reboot. Update job will get applied on next server manual reboot. Note: For devices that do not need a reboot to apply the firmware update (Examples: iDRAC, DIAGS, Driver Pack), you don\'t need to pass in this agrument(update will happen immediately). See Lifecycle Controller User Guide firmware update section for more details on which devices get applied immediately or need a reboot to get updated', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(1)
    if 'MultipartHttpPushUri' in data.keys():
        pass
    else:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(1)   

def get_idrac_version():
    global idrac_fw_version
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, GET request failed to get iDRAC firmware version, error: \n%s" % data)
        sys.exit(1)
    idrac_fw_version = data["FirmwareVersion"].replace(".","")
    
def get_FW_inventory():
    print("\n- INFO, getting current firmware inventory for iDRAC %s -\n" % idrac_ip)
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



def download_image_create_update_job():
    global job_id
    global start_time
    start_time=datetime.now()
    print("\n- INFO, downloading update package to create update job, this may take a few minutes depending on firmware image size")
    url = "https://%s/redfish/v1/UpdateService/MultipartUpload" % idrac_ip
    if args["r"] == "n":
        payload = {"Targets": [], "@Redfish.OperationApplyTime": "Immediate", "Oem": {}}
    elif args["r"] == "l":
        payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
    else:
        payload = {"Targets": [], "@Redfish.OperationApplyTime": "Immediate", "Oem": {}}
    files = {
         'UpdateParameters': (None, json.dumps(payload), 'application/json'),
         'UpdateFile': (os.path.basename(args["l"]), open(args["l"], 'rb'), 'application/octet-stream')
    }
    response = requests.post(url, files=files, auth = (idrac_username, idrac_password), verify=False)
    if response.status_code == 202:
        pass
    else:
        data = response.json()
        print("- FAIL, status code %s returned, detailed error is: %s" % (response.status_code,data))
        sys.exit(1)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to locate job ID in header")
        sys.exit(1)
    print("- PASS, update job ID %s successfully created, script will now loop polling the job status\n" % job_id)



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
        if data["TaskState"] == "Completed" and data["JobState"] == "Failed":
            print("- WARNING, job completed but failure detected, detailed final job status results:\n%s" % data["Id"])
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        if data["TaskState"] == "Completed":
            print("\n- PASS, job ID successfuly marked completed, detailed final job status results:\n%s " % data["Id"])
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
            print("- Message: %s, execution time: %s" % (message_string[0]["Message"].rstrip("."), current_time))
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
            sys.exit(1)
        else:
            print("- INFO, JobStatus not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'].rstrip("."), current_time))
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
            time.sleep(30)
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


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["l"]:
        get_idrac_version()
        download_image_create_update_job()
        check_job_status()
        if args["r"] == "n":
            print("- INFO, powering on or rebooting server to apply the firmware")
            if int(idrac_fw_version[0]) >= 5:
                loop_check_final_job_status()
            else:
                print("- INFO, older iDRAC version detected, execute action ComputerSystem.Reset to reboot the server")
                reboot_server()
                loop_check_final_job_status()
        elif args["r"] == "l":
            print("- INFO, user selected to not reboot the server now. Update job is marked as scheduled and will be applied on next server reboot")
            sys.exit(1)
    else:
        print("\n- FAIL, incorrect parameter(s) passed in or missing required parameters")







#
# DeviceFirmwareMultipartUploadREDFISH.py. Python script using Redfish API to update a device firmware with DMTF MultipartUpload. Supported file image types are Windows DUPs, d7/d9 image or pm files.
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

import requests, json, sys, re, time, warnings, argparse, os, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")



parser=argparse.ArgumentParser(description="Python script using Redfish API to update a device firmware with DMTF MultipartUpload from a local directory")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='DeviceFirmwareMultipartUploadREDFISH.py -ip 192.168.0.120 -u root -p calvin -l C:\\Users\\admin\\Downloads\\BIOS.EXE -r l, this example will create and schedule BIOS update job but not reboot the server now. DeviceFirmwareMultipartUploadREDFISH.py -ip 192.168.0.120 -u root -p calvin -l C:\\Users\\admin\\Downloads\\NIC.EXE -r n, this example will create and schedule NIC update job, reboot the server now to execute the job.') 
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-l', help='Pass in the full directory path location of the firmware image. Make sure to also pass in the name of the Dell Update package (DUP) executable, example: C:\\Users\\admin\\Downloads\\Diagnostics_Application_CH7FG_WN64_4301A42_4301.43.EXE', required=False)
parser.add_argument('-r', help='Pass in value for reboot type. Pass in \"n\" for server to reboot now to apply the update. Pass in \"l\" which will schedule the job but server will not reboot. Update job will get applied on next server manual reboot.', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/UpdateService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit()
    if 'MultipartHttpPushUri' in data.keys():
        pass
    else:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()   
    
    
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
    payload = {"Targets": [], "@Redfish.OperationApplyTime": "OnReset", "Oem": {}}
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
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to locate job ID in header")
        sys.exit()
    print("- PASS, update job ID %s successfully created, script will now loop polling the job status\n" % job_id)

        

def check_job_status():
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
            print("\n- PASS, job ID %s successfully marked as scheduled" % data["Id"])
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
            print("- Message: %s, current update execution time: %s" % (message_string[0]["Message"], current_time))
            time.sleep(1)
            continue

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s" % data[u'PowerState'])
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
                print("- INFO, unable to graceful shutdown the server, will perform forced shutdown now")
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
    while True:
        check_idrac_connection()
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
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
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- INFO, JobStatus not completed, current status: \"%s\", update execution time: \"%s\"" % (data['Message'], current_time))
            check_idrac_connection()
            time.sleep(5)

def check_idrac_connection():
    count = 0
    ping_command="ping %s -n 5" % idrac_ip
    while True:
        if count == 11:
            print("- WARNING, unable to successfully ping iDRAC IP after 10 attempts, script will exit.")
            sys.exit()
        try:
            ping_output = subprocess.Popen(ping_command, stdout = subprocess.PIPE, shell=True).communicate()[0]
            ping_results = re.search("Lost = .", ping_output).group()
            if ping_results == "Lost = 0":
                break
            else:
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 1 minute")
                time.sleep(60)
                count+=1
        except:
            ping_output = subprocess.run(ping_command,universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if "Lost = 0" in ping_output.stdout:
                break
            else:
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 1 minute")
                time.sleep(60)
                count+=1


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["l"]:
        download_image_create_update_job()
        check_job_status()
        if args["r"] == "n":
            print("- WARNING, powering on or rebooting server to apply the firmware")
            reboot_server()
            loop_check_final_job_status()
        elif args["r"] == "l":
            print("- WARNING, user selected to not reboot the server now. Update job is marked as scheduled and will be applied on next server reboot")
            sys.exit()       
    else:
        print("\n- FAIL, incorrect parameter(s) passed in or missing required parameters")







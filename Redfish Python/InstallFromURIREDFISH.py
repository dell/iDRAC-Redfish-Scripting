#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse, subprocess, platform

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get current firmware inventory versions or update device firmware using supported network share.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-x', help='Get examples of executing the script using supported network share types, pass in \"y\"', required=False)
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware versions, pass in \"y\"', required=False)
parser.add_argument('-n', help='Get current supported network share types, pass in \"y\"', required=False)
parser.add_argument('-t', help='Get current iDRAC time, pass in \"y\"', required=False)
parser.add_argument('-up', help='Pass the update path of the network share which contains the update package. Execute -x argument to see examples of network shares being used for updates', required=False)
parser.add_argument('-S', help='Pass in the start time you want the update job to execute. Pass in a value of \"TIME_NOW\" for the update job to execute immediately or pass in future time for the job to execute. Time format: yyyymmddhhmmss. Note: This is only supported for devices that need server reboot to apply the update. Refer to Lifecycle Controller User Guide for more details on what devices need a reboot to apply the update.', required=False)
parser.add_argument('-U', help='Pass in until time if you want to use a maintenance window. If until time is set, this update job must complete before hitting until time or the job will be marked as failed. Time must be in this format yyyymmddhhmmss. Note: This is only supported for devices that need server reboot to apply the update.', required=False)
parser.add_argument('-r', help='Reboot server to perform the update, pass in \"y\" to reboot the server now or \"n\" to not reboot the server now but update job ID will still be scheduled and execute on next server reboot. NOTE: This argument is only needed for devices which need a server reboot to apply the update. See Lifecycle Controller User Guide Update section for more details.', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, iDRAC version detected does not support this feature, status code %s returned" % response.status_code)
        sys.exit()

def script_examples():
    print("\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -up ftp://192.168.0.130/pub/Diagnostics_Application_3PFTY_WN64_4301A13_4301.14.EXE, this example will install DIAGS from FTP share\n\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -S TIME_NOW -r y -up cifs://cifs_user:cifs_password@192.168.0.130/BIOS_2.10.EXE;mountpoint=cifs_share_vm, this example will install BIOS from a CIFS share and reboot the server now\n\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -up nfs://192.168.0.130/Diagnostics_Application_3PFTY_WN64_4301A13_4301.14.EXE;mountpoint=/nfs_share, this example will install DIAGS from a NFS share\n\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -up tftp://192.168.0.130/Diagnostics_Application_3PFTY_WN64_4301A13_4301.14.EXE, this example will install DIAGS from TFTP network share\n\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -up http://192.168.0.130/updates_http/Diagnostics_Application_3PFTY_WN64_4301A13_4301.14.EXE, this example will update DIAGS from HTTP network share\n\nInstallFromURIREDFISH.py -ip 192.168.0.120 -u root -p calvin -up nfs://192.168.0.130/BIOS_YP88M_WN64_2.9.3_01.EXE;mountpoint=/nfs -S 20210107140000 -U 20210107145000, this example using maintenance window will schedule the BIOS job to be executed during a specific time. Once start time has passed, next server reboot the update job will execute but the server reboot must happen before until time has passed.")
    
def get_FW_inventory():
    print("\n- INFO, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
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

def get_supported_network_share_types():
    print("\n- INFO, current supported network share types -\n")
    req = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    print(data["Actions"]["#DellSoftwareInstallationService.InstallFromRepository"]["ShareType@Redfish.AllowableValues"])

def install_from_uri():
    global job_id
    global start_time
    start_time = datetime.now()
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.InstallFromURI' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"URI":args["up"]}
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    else:
        pass
    print("\n- INFO, arguments and values for %s method\n" % "InstallFromURI")
    for i in payload.items():
        print("%s: %s" % (i[0],i[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed to download firmware image, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, POST command failed to download firmware image, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    job_id = response.headers['Location'].split("/")[-1]
    print("- PASS, job ID %s successfully created" % job_id)
    
def schedule_update_job():
    global payload
    global until_time_flag
    until_time_flag = "no"
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    if req.status_code != 200:
        print("- FAIL, GET command failed to check job ID, error is: %s" % data)
        sys.exit()
    if "Diagnostics" in data['Name'] or "USC" in data['Name'] or "DriverPack" in data['Name'] or "OSCollector" in data['Name'] or "ServiceModule" in data['Name'] or "iDRAC" in data['Name'] or "completed successfully" in data['Message']:
        print("\n- INFO, direct update device detected, no server reboot needed. SetupJobQueue action will not be performed.")
        sys.exit()
    else:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.SetupJobQueue' % idrac_ip
        method = "SetupJobQueue"
        payload = {"JobArray":[job_id]}
        if args["U"]:
            payload["UntilTime"] = args["U"]
        if args["S"]:
            payload["StartTimeInterval"] = args["S"]
        print("\n- INFO, arguments and values for %s action\n" % method)
        for i in payload.items():
              print("%s: %s" % (i[0],i[1]))
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        data = response.json()
        if statusCode == 200:
            print("\n- PASS: Command passed for action %s" % method)
        else:
            print("\n- FAIL, Command failed for action %s, status code is %s. Detailed error message is: %s\n" % (method, statusCode, data))
            sys.exit()
        if args["S"] != "TIME_NOW":
            print("- INFO, update start time not detected as TIME_NOW. Update job will not execute until scheduled start time has passed. Once scheduled start time passes, update job will execute on next server reboot.")
            if "UntilTime" in payload.keys():
                until_time_flag = "yes"
                print("- INFO, until time detected for scheduling update job. If until time passes and server was not rebooted to execute update job, job will be marked as failed")
                req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
                data = req.json()
                print("\n- Current update job information -\n")
                for i in data.items():
                    print("%s: %s" % (i[0], i[1]))
            else:
                pass
            sys.exit()

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_power_state = data['PowerState']
    if current_power_state == "On":
        print("\n- INFO, server in ON state, server will now reboot to apply the update")
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to gracefully shutdown the server, status code is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to gracefully shutdown the server, status code is: %s" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        time.sleep(10)
        count = 1
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_power_state = data['PowerState']
            if current_power_state == "Off":
                print("\n- PASS, verified server gracefully shutdown and server in OFF state")
                payload = {'ResetType': 'On'}
                headers = {'content-type': 'application/json'}
                try:
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                except requests.ConnectionError as error_message:
                    print("- INFO, connection error detected for POST command, retry command in 10 seconds")
                    time.sleep(10)
                    try:
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                    except requests.ConnectionError as error_message:
                        print("- WARNING, connection error still detected, check iDRAC network connection")
                        sys.exit()
                statusCode = response.status_code
                if statusCode == 204:
                    print("\n- PASS, POST command passed to power ON server, code return is %s" % statusCode)
                    time.sleep(10)
                    return
                else:
                    print("\n- FAIL, POST command failed to power ON server, status code is: %s" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
            elif count == 20:
                print("- INFO, unable to gracefully shutdown the server, force off will now be applied to the server")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                try:
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                except requests.ConnectionError as error_message:
                    print("- INFO, connection error detected for POST command, retry command in 10 seconds")
                    time.sleep(10)
                    try:
                        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                    except requests.ConnectionError as error_message:
                        print("- WARNING, connection error still detected, check iDRAC network connection")
                        sys.exit()
                statusCode = response.status_code
                if statusCode == 204:
                    print("\n- PASS, POST command passed to force OFF the server, status code return is %s" % statusCode)
                    time.sleep(5)
                    check_idrac_connection()
                else:
                    print("\n- FAIL, POST command failed to force OFF the server, status code is: %s" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
                while True:
                    try:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
                    except requests.ConnectionError as error_message:
                        print("- INFO, connection error detected for GET command, retry command in 10 seconds")
                        time.sleep(10)
                        continue
                    data = response.json()
                    current_power_state = data['PowerState']
                    if current_power_state == "Off":
                        print("\n- PASS, verified server in OFF state")
                        payload = {'ResetType': 'On'}
                        headers = {'content-type': 'application/json'}
                        try:
                            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                        except requests.ConnectionError as error_message:
                            print("- INFO, connection error detected for POST command, retry command in 10 seconds")
                            time.sleep(10)
                            try:
                                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                            except requests.ConnectionError as error_message:
                                print("- WARNING, connection error still detected, check iDRAC network connection")
                                sys.exit()
                        statusCode = response.status_code
                        if statusCode == 204:
                            print("\n- PASS, POST command passed to power ON server, status code return is %s" % statusCode)
                            time.sleep(10)
                            return
                        else:
                            print("\n- FAIL, POST command failed to power ON server, status code is: %s" % statusCode)
                            print("Extended Info Message: {0}".format(response.json()))
                            sys.exit()
                    else:
                        print("- STATUS, forced shutdown not complete, checking again to verify server in OFF state")
                        time.sleep(5)
                        continue   
            else:
                print("- STATUS, graceful shutdown not complete, checking again to verify server in OFF state")
                time.sleep(5)
                count += 1
                continue
        
    if current_power_state == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        print("\n- INFO, server in OFF state, server will now power ON to perform the update(s)")
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        except requests.ConnectionError as error_message:
            print("- INFO, connection error detected for POST command, retry command in 10 seconds")
            time.sleep(10)
            try:
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
            except requests.ConnectionError as error_message:
                print("- WARNING, connection error still detected, check iDRAC network connection")
                sys.exit()
        statusCode = response.status_code
        if statusCode == 204:
            print("\n- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()

def loop_job_status():
    time.sleep(1)
    while True:
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
        if str(current_time)[0:7] >= "1:00:00":
            print("\n- FAIL: Timeout of 1 hour has been hit, script will stop\n")
            sys.exit()
        elif "Job for this device is already present" in data["Message"]:
            print("- INFO, update job for this device already exists, check overall iDRAC Job Queue")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "invalid" in data['Message'] or "unable" in data['Message'] or "Unable" in data['Message'] or "not" in data['Message'] or "Not" in data['Message']:
            print("- FAIL: Job ID %s failed, detailed error message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif data['JobState'] == "Scheduled" or "Task successfully scheduled" in data["Message"]:
            if "Job for this device is already present" in data["Message"]:
                print("- WARNING, update job for this device already exists, check overall iDRAC Job Queue")
                sys.exit()
            else:
                print("- PASS, %s job id successfully scheduled, script will wait 1 minute to check job state, detect if update can be applied in real time or server reboot needed" % job_id)
                time.sleep(60)
                req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
                data = req.json()
                if data['JobState'] == "Running":
                    print("- INFO, device detected supports updating in realtime, no server rebooted to apply the update.")
                    continue
                else:
                    print("- INFO, server reboot needed to apply the update")
                    break
                
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- INFO, job not completed, status: \"%s\", execution time: \"%s\"" % (data['Message'], current_time))
            time.sleep(5)

def loop_job_status_dowloaded():
    start_time=datetime.now()
    time.sleep(1)
    while True:
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
        elif "Job for this device is already present" in data["Message"]:
            print("- INFO, update job for this device already exists, check overall iDRAC Job Queue")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "invalid" in data['Message'] or "unable" in data['Message'] or "Unable" in data['Message'] or "not" in data['Message'] or "Not" in data['Message']:
            print("- FAIL: Job ID %s failed, detailed error message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif "Package successfully downloaded" in data["Message"] or "successfully downloaded" in data["Message"]:
            if "Job for this device is already present" in data["Message"]:
                print("- INFO, update job for this device already exists, check overall iDRAC Job Queue")
                sys.exit()
            else:
                print("- PASS, %s job id successfully downloaded, job ID will now get scheduled" % job_id)
                time.sleep(10)
                break
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            break
        else:
            print("- INFO, job not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'], current_time))
            time.sleep(5)

def loop_check_final_job_status():
    start_time=datetime.now()
    time.sleep(1)
    count = 1
    while True:
        if count == 20:
            print("- WARNING, GET request retry count has been hit, script will exit")
            sys.exit()
        check_idrac_connection()
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- INFO, connection error detected for GET request, script will wait 1 minute and execute GET request again")
            time.sleep(60)
            count+=1
            continue
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
            print("- INFO, JobStatus not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'], current_time))
            check_idrac_connection()
            time.sleep(5)

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
            print("- INFO, iDRAC network connection lost due to slow network response, waiting 1 minute to access iDRAC again")
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
                    print("- INFO, unable to ping iDRAC IP, script will wait 1 minute and try again")
                    time.sleep(60)
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


def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":True}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed to get current iDRAC time, status code %s returned\n" % response.status_code)
    else:
        print("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["x"]:
        script_examples()
    elif args["t"]:
        get_idrac_time()
    elif args["g"]:
        get_FW_inventory()
    elif args["n"]:
        get_supported_network_share_types()
    elif args["up"]:
        install_from_uri()
        loop_job_status_dowloaded()
        schedule_update_job()
        if "StartTimeInterval" in payload:
            if payload["StartTimeInterval"] != "TIME_NOW":
                print("\n- INFO, job ID %s is scheduled for a time in the future and will perform the update at \"%s\"" % (job_id, payload["StartTimeInterval"]))
                sys.exit()
            else:
                loop_job_status()
                if args["r"] == "y" and args["S"] == "TIME_NOW":
                    reboot_server()
                elif args["r"] == "y" and args["S"] != "TIME_NOW":
                    print("- INFO, user selected to schedule the update at a later time, server will not reboot now. Once the scheduled time has passed, update job will execute on next server reboot.")
                    if until_time_flag == "yes":
                        print("- INFO, until time detected for scheduling update job. If until time passes and server was not rebooted to execute update job, job will be marked as failed")
                        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
                        data = req.json()
                        print("\n- Current update job information -\n")
                        for i in data.items():
                            print("%s: %s" % (i[0], i[1]))
                    else:
                        pass
                    sys.exit()
                elif args["r"] == "n":
                    print("- INFO, user selected to not reboot the server now to apply the update but update job is still scheduled, will be applied on next server reboot.")
                    sys.exit()
                loop_check_final_job_status()
        else:
                loop_job_status()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")
    
    
        
            
        
        

#
# ImportSystemConfigurationLocalFilenameREDFISH. Python script using Redfish API to import system configuration profile attributes locally from a configuration file.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 20.0
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

import requests, json, sys, re, time, warnings, argparse, platform, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to import the host server configuration profile locally from a configuration file.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-np', help='Pass in new iDRAC user password that gets set during SCP import. This will be required to continue to query the job status.', required=False)
parser.add_argument('script_examples',action="store_true",help='ImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -p calvin -t ALL --filename SCP_export_R740, this example is going to import SCP file and apply all attribute changes for all components. \nImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -p calvin -t BIOS --filename R740_scp_file -s Forced, this example is going to only apply BIOS changes from the SCP file along with forcing a server power reboot. ImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -t IDRAC -f 2020-8-5_135318_export.xml -p calvin -np Test1234#, this example uses SCP import to change root user password and will leverage the new user password to continue to query the job status until marked completed')
parser.add_argument('-t', help='Pass in Target value to set component attributes. You can pass in \"ALL" to set all component attributes or pass in a specific component to set only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=True)
parser.add_argument('-s', help='Pass in ShutdownType value. Supported values are Graceful, Forced and NoReboot. If you don\'t use this optional parameter, default value is Graceful. NOTE: If you pass in NoReboot value, configuration changes will not be applied until the next server manual reboot.', required=False)
parser.add_argument('-f', help='Pass in Server Configuration Profile filename', required=True)
parser.add_argument('-e', help='Pass in end HostPowerState value. Supported values are On and Off. If you don\'t use this optional parameter, default value is On', required=False)
args=vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]
filename = args["f"]

def check_supported_idrac_version():
    global get_version
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        data = response.json()
        get_version = data['FirmwareVersion'].split(".")[:2]
        get_version = int("".join(get_version))


def import_SCP_local_filename():
    global job_id
    try:
        open_file = open(filename,"r")
    except:
        print("\n-FAIL, \"%s\" file doesn't exist" % filename)
        sys.exit()
        
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip

    # Code needed to modify the SCP file to one string to pass in for POST command
    modify_file = open_file.read()
    modify_file = re.sub(" \n ","",modify_file)
    modify_file = re.sub(" \n","",modify_file)
    file_string = re.sub("   ","",modify_file)
    open_file.close()

    payload = {"ImportBuffer":"","ShareParameters":{"Target":args["t"]}}
    if args["s"]:
        payload["ShutdownType"] = args["s"]
    if args["e"]:
        payload["HostPowerState"] = args["e"]

    payload["ImportBuffer"] = file_string
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))
    get_dict = str(response.__dict__)

    try:
        get_job_ID_search = re.search("JID_.+?,",get_dict).group()
    except:
        print("\n- FAIL: status code %s returned for ImportSystemConfiguration action" % response.status_code)
        print("- Detailed error information: %s" % get_dict)
        sys.exit()

    job_id = re.sub("[,']","",get_job_ID_search)
    if response.status_code != 202:
        print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code )  
        sys.exit()
    else:
        print("\n- PASS, %s successfully created for ImportSystemConfiguration method\n" % (job_id))


def check_job_status():
    start_job_message = ""
    start_time = datetime.now()
    idrac_ip = args["ip"]
    idrac_username = args["u"]
    idrac_password = args["p"]
    count = 1
    get_job_status_count = 1
    while True:
        check_idrac_connection()
        if count == 10:
            print("- FAIL, 10 attempts at getting job status failed, script will exit")
            sys.exit(0)
        if get_job_status_count == 10:
            print("- INFO, retry count of 10 has been hit for retry job status GET request, script will exit")
            sys.exit(0)
        try:
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
            time.sleep(10)
            print("- INFO, script will now attempt to get job status again")
            count+=1
            continue
        statusCode = req.status_code
        if statusCode == 401 and args["np"]:
            print("- INFO, status code 401 and argument -np detected. Script will now query job status using iDRAC user \"%s\" new password set by SCP import" % idrac_username)
            idrac_password = args["np"]
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
            if req.status_code == 401:
                print("- INFO, new password passed in for argument -np still failed with status code 401 for idrac user \"%s\", unable to check job status" % idrac_username)
                sys.exit()
            else:
                continue
        elif statusCode == 401:
            print("- INFO, status code 401 still detected for iDRAC user \"%s\". Check SCP file to see if iDRAC user \"%s\" password was changed for import" % (idrac_username, idrac_username))
            sys.exit()
        else:
            pass
        data = req.json()
        try:
            current_job_message = data['Oem']['Dell']['Message']
        except:
            print("- INFO, unable to get job ID message string from JSON output, retry")
            count +=1
            continue
        current_time = (datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            pass
        else:
            print("Query job ID command failed, error code: %s, retry" % statusCode)
            count +=1
            time.sleep(5)
            continue
        if "Oem" in data:
            pass
        else:
            print("- INFO, unable to locate OEM data in JSON response, retry")
            get_job_status_count +=1
            time.sleep(5)
            continue
            
        if data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
            print("\n- INFO, job ID %s status marked as \"%s\"" % (job_id, data['Oem']['Dell']['JobState']))
            print("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    for ii in i.items():
                        if ii[0] == "Oem":
                            for iii in ii[1]["Dell"].items():
                                print("%s: %s" % (iii[0], iii[1]))
                        else:
                            if ii[0] == "Severity":
                                pass
                            if get_version < 440:
                                if ii[1] == "Critical":
                                    print("%s: %s" % (ii[0], ii[1]))
                                    print("Status: Failure")
                                elif ii[1] == "OK":
                                    print("%s: %s" % (ii[0], ii[1]))
                                    print("Status: Success")
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                                    
                            else:
                                print("%s: %s" % (ii[0], ii[1]))
                    print("\n")
            except:
                print("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                    
            print("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        elif data['Oem']['Dell']['JobState'] == "Completed":
            if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                print("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
            elif "success" in data['Oem']['Dell']['Message'].lower():
                print("- PASS, job ID %s successfully marked completed\n" % job_id)
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                print("\n- PASS, job ID %s marked completed\n" % job_id)
                print("- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                sys.exit()
            print("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    for ii in i.items():
                        if ii[0] == "Oem":
                            for iii in ii[1]["Dell"].items():
                                print("%s: %s" % (iii[0], iii[1]))
                        else:
                            if ii[0] == "Severity":
                                pass
                            if get_version < 440:
                                if ii[1] == "Critical":
                                    print("%s: %s" % (ii[0], ii[1]))
                                    print("Status: Failure")
                                elif ii[1] == "OK":
                                    print("%s: %s" % (ii[0], ii[1]))
                                    print("Status: Success")
                                else:
                                    print("%s: %s" % (ii[0], ii[1]))
                                    
                            else:
                                print("%s: %s" % (ii[0], ii[1]))
                    print("\n")
            except:
                print("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
                    
            print("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
                
        elif "No reboot Server" in data['Oem']['Dell']['Message']:
            print("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
            print("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            sys.exit()
        else:
            if start_job_message != current_job_message:
                print("- INFO, job not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                start_job_message = current_job_message
                #time.sleep(3)
                continue
            else:
                pass
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


if __name__ == "__main__":
    check_supported_idrac_version()
    import_SCP_local_filename()
    check_job_status()
    

#
# BiosChangePasswordREDFISH. Python script using Redfish API to set / change or delete either BIOS setup or system password
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

import requests, json, sys, re, time, warnings, os, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to set, change or delete either BIOS setup or system password")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -c 1 -o "" -n "p@ssw0rd", this example is setting the BIOS system password. BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -c 1 -o "p@ssw0rd" -n "newpwd", this example is changing the BIOS system password. BiosChangePasswordREDFISH.py -ip 192.168.0.120 -u root -p calvin -c 2 -o "p@ssw0rd" -n "", this example is clearing the BIOS setup password.')
parser.add_argument('-c', help='Set, Change or Delete BIOS password, pass in the type of password you want to change. Pass in \"1\" for System password or \"2" for Setup password', required=False)
parser.add_argument('-o', help='Change BIOS password, pass in the old password. If you are setting new password, pass in \"\" for -o argument', required=False)
parser.add_argument('-n', help='Change BIOS password, pass in the new password. If you are clearing the password, pass in \"\" for -n argument', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def change_bios_password():
    if args["c"] == "1":
        password_name = "SysPassword"
    elif args["c"] == "2":
        password_name = "SetupPassword"
    else:
        print("- FAIL, invalid value passed in for -c option")
        sys.exit()
    url = "https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ChangePassword" % idrac_ip
    if args["n"] == "":
        payload = {"PasswordName":password_name,"OldPassword":args["o"],"NewPassword":""}
        print("- WARNING, clearing BIOS %s" % password_name)
    elif args["o"] == "":
        payload = {"PasswordName":password_name,"":args["o"],"NewPassword":args["n"]}
        print("- WARNING, setting new BIOS %s" % password_name)
    else:
        payload = {"PasswordName":password_name,"OldPassword":args["o"],"NewPassword":args["n"]}
        print("- WARNING, changing BIOS %s" % password_name)
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.__dict__
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS: status code %s returned for POST command to change password" % statusCode)
    else:
        print("\n- FAIL, Command failed, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print detail_message
        sys.exit()
    
def create_bios_config_job():
    global job_id
    global start_time
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("- PASS: POST command passed to create target config job, status code %s returned." % statusCode)
    else:
        print("\n- FAIL, Command failed, status code is %s\n" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    d=str(response.__dict__)
    z=re.search("JID_.+?,",d).group()
    job_id=re.sub("[,']","",z)
    print("- WARNING: %s job ID successfully created" % job_id)
    start_time=datetime.now()

def check_schedule_job_status():
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
        if data[u'Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data[u'Message'])
    
                                                                          
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
            print("- PASS, Command passed to gracefully power OFF server, status code return is %s" % statusCode)
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data[u'PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            else:
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
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


def check_job_status_final():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
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
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data[u'Message'] == "Job completed successfully.":
            print("\n- Final detailed job results -")
            print("\n JobID = "+data[u'Id'])
            print(" Name = "+data[u'Name'])
            print(" Message = "+data[u'Message'])
            print(" PercentComplete = "+str(data[u'PercentComplete'])+"\n")
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"" % data[u'Message'])
            time.sleep(30)



if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        change_bios_password()
        create_bios_config_job()
        check_schedule_job_status()
        reboot_server()
        check_job_status_final()
        
        




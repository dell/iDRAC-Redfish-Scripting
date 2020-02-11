#
# SecureBootResetKeysREDFISH. Python script using Redfish API to either get supported reset key types or reset secure boot keys.
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get supported reset key types or reset secure boot keys. NOTE: To reset secure boot keys, make sure BIOS attribute Secure Boot policy is not set to Standard.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SecureBootResetKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin -k y, this will get current supported reset key type values. SecureBootResetKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get BIOS attribute SecureBootPolicy current value. SecureBootResetKeysREDFISH.py -ip 192.168.0.120 -u root -p calvin -r DeleteAllKeys -b y, this example will execute secure boot reset keys passing in value DeleteAllKeys and reboot the server immediately.')
parser.add_argument('-k', help='Get supported reset key types, pass in \"y\"', required=False)
parser.add_argument('-g', help='Get BIOS secure boot policy setting, pass in \"y\"', required=False)
parser.add_argument('-s', help='Set BIOS attribute Secure Boot Policy to Custom for reset secure boot keys action to execute, pass in \"y\". NOTE: This will create a BIOS config job, reboot the server to apply attribute change.', required=False)
parser.add_argument('-r', help='Reset secure boot keys, pass in the reset key type string value. If needed, execute argument -k to get supported string values. NOTE: Make sure to pass in the exact value as its reported. Example: pass in \"DeletePK\", \"deletepk\" will fail.', required=False)
parser.add_argument('-b', help='Reboot the server to complete the reset key process. Pass in \"y\" if you want to automatically reboot the server now or \"n\" to not reboot. NOTE: Next server manual reboot, the process will be complete.', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "ResetKeys" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_secure_boot_policy_setting():
    print("\n- WARNING, checking if BIOS attribute SecureBootPoicy is set to Standard")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict.items():
        if i[0] == "SecureBootPolicy":
            if i[1] == "Standard":
                print("\n- WARNING, BIOS attribute SecureBootPolicy set to Standard, config job creation needed to set SecureBootPolicy to Custom")
            else:
                print("\n- WARNING, BIOS attribute SecureBootPolicy is not set to Standard, no job creation needed to change current value")

def set_bios_attribute():
    global payload
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % idrac_ip
    payload = {"Attributes":{"SecureBootPolicy":"Custom"}}
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    payload['Attributes'][i[0]] = int(i[1])
    print("\n- WARNING, configuring BIOS attribute -\n")
    for i in payload["Attributes"].items():
        print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS: PATCH command passed to set BIOS attribute pending value, status code %s returned" % statusCode)
    else:
        print("\n- FAIL, PATCH command failed, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    d=str(response.__dict__)

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
        print("\n- FAIL, POST command failed, status code is %s\n" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    d=str(response.__dict__)
    z=re.search("JID_.+?,",d).group()
    job_id=re.sub("[,']","",z)
    print("- WARNING: %s job ID successfully created" % job_id)
    start_time=datetime.now()
        
def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
            #print("- PASS, Command passed to check job status, code 200 returned")
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data['Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data['Message'])

def loop_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
            #print("\n- PASS, Command passed to check job status, code 200 returned\n")
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "error" in data['Message'] or "Error" in data['Message']:
            print("- FAIL: %s failed" % job_id)
            print("\n- Final detailed job results -")
            print("\n JobID = "+data['Id'])
            print(" Name = "+data['Name'])
            print(" Message = "+data['Message'])
            print(" PercentComplete = "+str(data['PercentComplete'])+"\n")
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n- Final detailed job results -")
            print("\n JobID = "+data['Id'])
            print(" Name = "+data['Name'])
            print(" Message = "+data['Message'])
            print(" PercentComplete = "+str(data['PercentComplete'])+"\n")
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"" % data['Message'])
            time.sleep(15)

def get_supported_reset_keys_type():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Supported reset key type values for \"SecureBoot.ResetKeys\" action -\n")
    for i in data['Actions']['#SecureBoot.ResetKeys']['ResetKeysType@Redfish.AllowableValues']:
        print(i)
    
def delete_all_keys():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Actions/SecureBoot.ResetKeys' % idrac_ip
    headers = {'content-type': 'application/json'}
    payload = {"ResetKeysType":args["r"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS, POST command passed for \"SecureBoot.ResetKeys\" action, status code %s returned" % response.status_code)
    else:
        data = response.json()
        print("\n- FAIL, action ResetKeys failed to delete all keys, status code %s returned, detailed error results:\n %s" % (response.status_code,data))
        sys.exit()                                                                       

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data['PowerState'])
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
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            else:
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
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["k"]:
        get_supported_reset_keys_type()
    elif args["g"]:
        get_secure_boot_policy_setting()
    elif args["s"]:
        set_bios_attribute()
        create_bios_config_job()
        get_job_status()
        reboot_server()
        loop_job_status()
    elif args["r"]:
        delete_all_keys()
        if args["b"] == "y":
            print("\n- WARNING, user selected to automatically reboot the server now to complete reset secure boot keys process")
            reboot_server()
        else:
            print("\n- WARNING, server will not automatically reboot. Reset secure boot keys process will be complete on next manual server reboot.")
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
        



        



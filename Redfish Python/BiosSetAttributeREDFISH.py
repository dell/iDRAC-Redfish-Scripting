#
# BiosSetAttributeREDFISH. Python script using Redfish API to set BIOS attribute.
#
# NOTE: For all attributes, supported values, refer to the Dell atttribute registry.
#
# NOTE: Recommended to execute BiosGetAttributesREDFISH script first. This will get all attributes and current values for the server.
#
# NOTE: When passing in attribute name / value, make sure you pass in the exact string. Attribute name / value are case sensitive.
#
# NOTE: If you want to set multiple BIOS attributes, modify the script and pass in each attribute name / value in the payload nested dictionary for PATCH command. Example: payload = {"Attributes":{"MemTest":"Enabled","EmbSata":"RaidMode"}} 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to change one BIOS attribute cuurent value")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-a', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail', required=True)
parser.add_argument('-v', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail', required=True)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
attribute_name = args["a"]
pending_value = args["v"]

### Function to check if current iDRAC version detected is supported by Redfish

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


### Function to get BIOS attribute current value

def get_attribute_current_value():
    global current_value
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data[u'Attributes'].items():
        if i[0] == args["a"]:
            current_value = i[1]
            print("\n- Current value for attribute \"%s\" is \"%s\"" % (args["a"], i[1]))

                    
### Function to set BIOS attribute pending value

def set_bios_attribute():
    print("\n- WARNING: Current value for %s is: %s, setting to: %s" % (attribute_name, current_value, pending_value))
    time.sleep(2)
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % idrac_ip
    payload = {"Attributes":{attribute_name:pending_value}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("- PASS: Command passed to set BIOS attribute %s pending value to %s" % (attribute_name, pending_value))
    else:
        print("\n- FAIL, Command failed, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    d=str(response.__dict__)

### Function to create BIOS target config job

def create_bios_config_job():
    global job_id
    global start_time
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip
    #payload = {"Target":"BIOS.Setup.1-1","RebootJobType":"PowerCycle"}
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("- PASS: Command passed to create target config job, status code 200 returned.")
    else:
        print("\n- FAIL, Command failed, status code is %s\n" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    d=str(response.__dict__)
    z=re.search("JID_.+?,",d).group()
    job_id=re.sub("[,']","",z)
    print("- WARNING: %s job ID successfully created\n" % job_id)
    start_time=datetime.now()
    
### Function to verify job is marked as scheduled before rebooting the server
    
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
        if data[u'Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            #print(" JobID = "+data[u'Id'])
            #print(" Name = "+data[u'Name'])
            #print(" Message = "+data[u'Message'])
            #print(" PercentComplete = "+str(data[u'PercentComplete'])+"\n")
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data[u'Message'])

### Function to reboot the server
                                                                          
def reboot_server():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': 'ForceOff'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("- PASS, Command passed to power OFF server, code return is %s" % statusCode)
    else:
        print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    time.sleep(10)
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

### Function to loop checking the job status until marked completed or failed    

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


### Function to check attribute new current value

def get_new_current_value():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_value_new = data[u'Attributes'][attribute_name]
    if current_value_new == pending_value:
        print("- PASS, BIOS attribute \"%s\" new current value is: %s" % (attribute_name, pending_value))
    else:
        print("n\- FAIL, BIOS attribute \"%s\" attribute not set to: %s" % (attribute_name, current_value))
        sys.exit()


### Run code

if __name__ == "__main__":
    check_supported_idrac_version()
    get_attribute_current_value()
    set_bios_attribute()
    create_bios_config_job()
    get_job_status()
    reboot_server()
    loop_job_status()
    get_new_current_value()



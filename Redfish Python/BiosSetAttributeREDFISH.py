#!/usr/bin/python
# BiosSetAttributeREDFISH. Python script using Redfish API to set one or multiple BIOS attributes.
#
# NOTE: For all attributes, supported values, refer to the Dell atttribute registry.
#
# NOTE: Recommended to execute BiosGetAttributesREDFISH script first. This will get all attributes and current values for the server.
#
# NOTE: When passing in attribute name / value, make sure you pass in the exact string. Attribute name / value are case sensitive.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 8.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to change one or multiple BIOS attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='BiosSetAttributeREDFISH.py -ip 192.168.0.120 -u root -p calvin -a MemTest -v Disabled, this example will set one BIOS attribute. BiosSetAttributeREDFISH.py -ip 192.168.0.120 -u root -p calvin -an LogicalProc,EmbSata -av Disabled,AhciMode, this example is setting multiple BIOS attributes')
parser.add_argument('-an', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name.', required=True)
parser.add_argument('-av', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value.', required=True)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


### Function to check if current iDRAC version detected is supported by Redfish

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

                    
### Function to set BIOS attribute pending value

def set_bios_attribute():
    global payload
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % idrac_ip
    payload = {"Attributes":{}}
    attribute_names = args["an"].split(",")
    attribute_values = args["av"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        payload["Attributes"][i] = ii

    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    payload['Attributes'][i[0]] = int(i[1])
    print("\n- WARNING, script will be setting BIOS attributes -\n")
    for i in payload["Attributes"].items():
        print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
    
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS: PATCH command passed to set BIOS attribute pending values")
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
    print("- WARNING: %s job ID successfully created" % job_id)
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
        if data['Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data['Message'])

### Function to reboot the server                                                                        

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
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "error" in data['Message'] or "Error" in data['Message']:
            print("- FAIL: %s failed" % job_id)
            print("\n- Final detailed job results -")
            print("\n JobID = "+data['Id'])
            print(" Name = "+data['Name'])
            print(" Message = "+data['Message'])
            print(" PercentComplete = "+str(data['PercentComplete'])+"\n")
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n- PASS, final detailed job results -")
            print("\n JobID = "+data['Id'])
            print(" Name = "+data['Name'])
            print(" Message = "+data['Message'])
            print(" PercentComplete = "+str(data['PercentComplete'])+"\n")
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            for i in payload["Attributes"]:
                for ii in data['Attributes'].items():
                    if ii[0] == i:
                        print("- Current value for attribute \"%s\" is \"%s\"" % (i, ii[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"" % data['Message'])
            time.sleep(30)


def get_new_attribute_values():
    print("- WARNING, checking new attribute values - \n")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    new_attributes_dict=data['Attributes']
    new_attribute_values = {"Attributes":{}}
    for i in new_attributes_dict.items():
        for ii in payload["Attributes"].items():
            if i[0] == ii[0]:
                if i[0] == "OneTimeBootMode":
                    print("- PASS, Attribute %s successfully set" % (i[0]))
                else:
                    try:
                        if i[1].lower() == ii[1].lower():
                            print("- PASS, Attribute %s successfully set to \"%s\"" % (i[0],i[1]))
                        else:
                            print("- FAIL, Attribute %s not successfully set. Current value is \"%s\"" % (i[0],i[1]))
                    except:
                        pass
                    try:
                        if int(i[1]) == int(ii[1]):
                            print("- PASS, Attribute %s successfully set to \"%s\"" % (i[0],i[1]))
                        else:
                            print("- FAIL, Attribute %s not successfully set. Current value is \"%s\"" % (i[0],i[1]))
                    except:
                        pass


if __name__ == "__main__":
    check_supported_idrac_version()
    set_bios_attribute()
    create_bios_config_job()
    get_job_status()
    reboot_server()
    loop_job_status()
    #get_new_attribute_values()



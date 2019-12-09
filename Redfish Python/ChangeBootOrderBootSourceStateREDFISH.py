#
# ChangeBiosBootOrderBootSourceStateREDFISH. Python script using Redfish API to get the either change boot order, change boot source state or both.
#
# NOTE: You must execute GetBiosBootOrderBootSourceStateREDFISH script first which will redirect the current boot order and boot source devices into boot_devices.txt file.
#
# To enable a boot device, pass in a value of true for Enabled key. To disable a boot device, pass in a value of false for Enabled key.
# You can do this for one device or all devices in the boot order.
#
# To change the boot order, change the index values for all the devices listed in your boot order.
#
#
# Example below is my current boot order and boot source state from boot_devices.txt file:
#
# [{"Index": 0, "Enabled": false, "Id": "BIOS.Setup.1-1#UefiBootSeq#Floppy.iDRACVirtual.1-1#f64c2e3f049b92a8e71f61cf51fea794", "Name": "Floppy.iDRACVirtual.1-1"},
# {"Index": 1, "Enabled": false, "Id": "BIOS.Setup.1-1#UefiBootSeq#Optical.iDRACVirtual.1-1#375d3ecb49f87dd46ca6c60e34f6155d", "Name": "Optical.iDRACVirtual.1-1"},
# {"Index": 2, "Enabled": false, "Id": "BIOS.Setup.1-1#UefiBootSeq#RAID.Mezzanine.1-1#6f9a42098226e9297f899d1039d4558e", "Name": "RAID.Mezzanine.1-1"}]
# 
# I want to enable all boot devices so i will change all false values to true. I also want RAID.Mezzanine.1-1 as 1st boot device, virtual floppy as 2nd boot device
# and virtual optical as 3rd boot device so i will change the index numbers (Note: index 0 is going to be the first device).
# 
# Example of the edited boot_devices.txt file:
# 
# [{"Index": 1, "Enabled": true, "Id": "BIOS.Setup.1-1#UefiBootSeq#Floppy.iDRACVirtual.1-1#f64c2e3f049b92a8e71f61cf51fea794", "Name": "Floppy.iDRACVirtual.1-1"},
# {"Index": 2, "Enabled": true, "Id": "BIOS.Setup.1-1#UefiBootSeq#Optical.iDRACVirtual.1-1#375d3ecb49f87dd46ca6c60e34f6155d", "Name": "Optical.iDRACVirtual.1-1"},
# {"Index": 0, "Enabled": true, "Id": "BIOS.Setup.1-1#UefiBootSeq#RAID.Mezzanine.1-1#6f9a42098226e9297f899d1039d4558e", "Name": "RAID.Mezzanine.1-1"}]
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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


import requests, json, sys, re, time, warnings, pickle, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either change the boot order or enable /disable boot order devices")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

### Function to check if iDRAC version detected is supported for this feature using Redfish

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

### Function to get BIOS current boot mode

def get_bios_boot_mode():
    global current_boot_mode
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_boot_mode = data[u'Attributes']["BootMode"]
    print("\n- Current boot mode is %s" % current_boot_mode)
                    
### Function to get current boot devices and their boot source state

def get_bios_boot_source_state():
    global boot_seq
    global boot_device_list_from_file
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if data[u'Attributes'] == {}:
        print("\n- WARNING, no %s boot order devices detected for iDRAC IP %s" % (current_boot_mode,idrac_ip))
        sys.exit()
    
    if current_boot_mode == "Uefi":
        boot_seq = "UefiBootSeq"
    else:
        boot_seq = "BootSeq"
    get_boot_devices=data[u'Attributes'][boot_seq]
    print("- Current boot order devices and their boot source state:\n")
    
    with open('boot_devices.txt', 'r') as i:
        boot_device_list_from_file=json.load(i)
    

    for i in get_boot_devices:
        for ii in i.items():
            #print("%s: %s" % (ii[0], ii[1]))
            if ii[0] == "Enabled":
                if ii[1] == True:
                    print("Enabled: true")
                elif ii[1] == False:
                    print("Enabled: false")
            else:
                print("%s: %s" % (ii[0], ii[1]))
            if ii[0] == "Name":
                print("\n")
    time.sleep(3)
    print("\n- WARNING, changing boot devices to these values based off \"boot_devices.txt\" file:\n")


    for i in boot_device_list_from_file:
        for ii in i.items():
            #print("%s: %s" % (ii[0], ii[1]))
            if ii[0] == "Enabled":
                if ii[1] == True:
                    print("Enabled: true")
                elif ii[1] == False:
                    print("Enabled: false")
            else:
                print("%s: %s" % (ii[0], ii[1]))
            if ii[0] == "Name":
                print("\n")
    time.sleep(3)

### Function to set BIOS pending value(s) for either boot order or boot source state

def set_bios_boot_source_state():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/BootSources/Settings' % idrac_ip
    payload = {'Attributes': {boot_seq:boot_device_list_from_file}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data=response.json()
    statusCode = response.status_code
    if statusCode == 200:
        print("- PASS: PATCH command passed to set pending boot device changes.")
    else:
        print("\n- FAIL, PATCH command failed, error code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()

### Function to create BIOS target config job

def create_bios_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    
    if statusCode == 200:
        print("- PASS: POST command passed to create target config job, status code 200 returned.")
    else:
        print("- FAIL, POST command failed to create BIOS config job, status code is %s\n" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    convert_to_string=str(response.__dict__)
    jobid_search=re.search("JID_.+?,",convert_to_string).group()
    job_id=re.sub("[,']","",jobid_search)
    print("- WARNING: %s job ID successfully created\n" % job_id)
    
### Function to verify job is marked as scheduled before rebooting the server
    
def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            print("- PASS, Command passed to check job status, code 200 returned")
            time.sleep(20)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print("- PASS, job id %s successfully scheduled" % job_id)
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data[u'Message'])

### Function to reboot the server
                                                                          
def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data[u'PowerState'])
    if data[u'PowerState'] == "On":
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
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
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

### Function to loop checking the job status until marked completed or failed    

def loop_job_status():
    print("\n- WARNING, script will now poll the job status ever 30 seconds until marked completed\n")
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            print("- PASS, Command passed to check job status, code 200 returned")
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or "error" in data[u'Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data[u'Message'] == "Job completed successfully.":
            print("- PASS, job id %s successfully marked as completed" % job_id)
            print("  Job completed in: %s\n" % str(current_time)[0:7])
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"\n" % data[u'Message'])
            time.sleep(30)


### Function to check boot device boot source state new status

def get_boot_source_new_state():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    get_boot_source_devices=data[u'Attributes'][boot_seq]
    print("- New status of boot order devices and their boot source state:\n")

    for i in get_boot_source_devices:
        for ii in i:
            print("%s : %s" % (ii, i[ii]))
            if ii == "Name":
                print("\n")
    time.sleep(3)


### Run code

if __name__ == "__main__":
    get_bios_boot_mode()
    get_bios_boot_source_state()
    set_bios_boot_source_state()
    create_bios_config_job()
    get_job_status()
    reboot_server()
    loop_job_status()
    get_boot_source_new_state()



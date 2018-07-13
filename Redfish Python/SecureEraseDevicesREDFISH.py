#
# SecureEraseDevicesREDFISH. Python script using Redfish API to either get storage controllers/supported secure erase devices and erase supported devices.
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


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get storage controllers/supported secure erase devices and erase supported devices")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-c', help='Get server storage controllers, pass in \"y\". To get detailed information for the storage controllers, pass in \"yy\"', required=False)
parser.add_argument('-d', help='Get controller drives, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-sd', help='Get supported secure erase devices, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-s', help='Pass in device FQDD for secure erase operation. Supported devices are ISE, SED drives or PCIe SSD devices(drives and cards)', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["d"]:
    controller=args["d"]
elif args["s"]:
    secure_erase_device=args["s"]

    



def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, GET command failed to get storage controllers, error is %s" % data)
        sys.exit()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
        print(i[u'@odata.id'][46:])
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            

def get_controller_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code != 200:
        print("\n- FAIL, either controller not found on server or typo in controller FQDD name")
        sys.exit()
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % controller)
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
            print(i[u'@odata.id'][53:])

def get_secure_erase_devices():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["sd"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code != 200:
        print("\n- FAIL, either controller not found on server or typo in controller FQDD name")
        sys.exit()
        
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["sd"])
        sys.exit()
    else:
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
        secure_erase_devices=[]
        for i in drive_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data.items():
                if ii[1] == "SelfEncryptingDrive":
                    secure_erase_devices.append(i)
        if "PCIe" in args["sd"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_value = data[u'Attributes']['NvmeMode']
            if current_value == "Raid":
                print("\n- WARNING, BIOS attribute NvmeMode set to Raid, erasing PCIe SSD devices not supported")
                sys.exit()
            else:
                print("\n- Supported Secure Erase PCIe SSD Devices Detected -\n")
                for i in drive_list:
                    print(i)
                sys.exit()
        else:
            if secure_erase_devices == []:
                print("\n- FAIL, no supported secure drives detected")
                sys.exit()
            else:
                print("\n- Supported secure erase drives detected for controller %s -\n" % args["sd"])
                for i in secure_erase_devices:
                    print(i)
            sys.exit()
    
    
    
def secure_erase():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s/Actions/Drive.SecureErase' % (idrac_ip, secure_erase_device)
    headers = {'content-type': 'application/json'}
    response = requests.post(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        print("\n- PASS: POST command passed to secure erase drive \"%s\", status code 202 returned" % secure_erase_device)
    else:
        print("\n- FAIL, POST command failed for secure erase, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
        
   
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    if data[u'JobType'] == "RAIDConfiguration":
        job_type="staged"
    elif data[u'JobType'] == "RealTimeNoRebootConfiguration":
        job_type="realtime"
    print("- PASS, \"%s\" %s jid successfully created for secure erase drive \"%s\"" % (job_type, job_id, secure_erase_device))


start_time=datetime.now()

def loop_job_status():
    start_time = datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(datetime.now()-start_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message']:
            print("- FAIL: Job ID \"%s\" failed, detailed error results: %s" % (job_id, data))
            sys.exit()
        elif data[u'Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print "%s: %s" % (i[0],i[1])
            print("- WARNING, job creation to completion time is: %s" % str(datetime.now()-start_time)[0:7])
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", precent completion is: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            print("- WARNING, current job execution time is: %s" % str(datetime.now()-start_time)[0:7])
            time.sleep(1)

def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            time.sleep(5)
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print "- PASS, staged config job marked as scheduled, powering on or rebooting the system"
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", precent completion is: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(5)


                                                                          
def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_power_state = data[u'PowerState']
    if current_power_state == "On":
        print("- WARNING, system power state ON detected, rebooting")
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'ForceOff'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power OFF server, status code is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        time.sleep(10)
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif current_power_state == "Off":
        print("- WARNING, system power state OFF detected, powering ON")
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current host power state")
        sys.exit()
        

if __name__ == "__main__":
    if args["c"]:
        get_storage_controllers()
    elif args["d"]:
        get_controller_disks()
    elif args["sd"]:
        get_secure_erase_devices()
    elif args["s"]:
        secure_erase()
        if job_type == "realtime":
            loop_job_status()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()
        


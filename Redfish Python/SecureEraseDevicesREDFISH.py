#
# SecureEraseDevicesREDFISH. Python script using Redfish API to either get storage controllers/supported secure erase devices and erase supported devices.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 13.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get storage controllers/supported secure erase devices and erase supported devices. NOTE: If erasing SED / ISE drives, make sure these drives are not part of a RAID volume. RAID volume must be deleted first before you can erase the drives. NOTE: If using iDRAC 7/8, only PCIeSSD devices support secure erase feature")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SecureEraseDevicesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1, this example will secure erase disk 1 for RAID.Integrated.1-1 controller.')
parser.add_argument('-c', help='Get server storage controllers, pass in \"y\". To get detailed information for the storage controllers, pass in \"yy\"', required=False)
parser.add_argument('-d', help='Get controller drives, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-sd', help='Get controller SED/ISE drives or PCIe SSD devices only, pass in controller FQDD, Examples "\RAID.Integrated.1-1\", \"PCIeExtender.Slot.7\"', required=False)
parser.add_argument('-s', help='Pass in device FQDD for secure erase operation. Supported devices are ISE, SED drives or PCIe SSD devices(drives and cards). NOTE: If using iDRAC 7/8, only PCIeSSD devices are supported for SecureErase', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
    

    
def get_iDRAC_version():
    global server_model_number
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    server_model_number = int(data["Model"].split(" ")[0].strip("G"))


def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, GET command failed to get storage controllers, error is %s" % data)
        sys.exit()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            

def get_controller_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["d"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code != 200:
        print("\n- FAIL, either controller not found on server or typo in controller FQDD name")
        sys.exit()
    if data['Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["d"])
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % args["d"])
        for i in data['Drives']:
            drive = i['@odata.id'].split("/")[-1]
            print(drive)
            drive_list.append(drive)

def get_secure_erase_devices_iDRAC9():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["sd"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code != 200:
        print("\n- FAIL, either controller not found on server or typo in controller FQDD name")
        sys.exit()
        
    if data['Drives'] == []:
        print("\n- WARNING, no drives detected for controller %s" % args["sd"])
        sys.exit()
    else:
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
        secure_erase_devices=[]
        for i in drive_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data.items():
                if ii[0] == "Oem":
                    try:
                        for iii in ii[1]["Dell"]["DellPhysicalDisk"].items():
                            if iii[0] == "SystemEraseCapability":
                                if iii[1] == "CryptographicErasePD":
                                    secure_erase_devices.append(i)
                    except:
                        for iii in ii[1]["Dell"]["DellPCIeSSD"].items():
                            if iii[0] == "SystemEraseCapability":
                                if iii[1] == "CryptographicErasePD":
                                    secure_erase_devices.append(i)
                        
                                
                else:
                    pass
        if secure_erase_devices == []:
            print("\n- WARNING, no secure erase supported devices detected for controller %s" % args["sd"])
            sys.exit()
        else:
            print("\n- Supported Secure Erase devices detected for controller %s -\n" % args["sd"])
            for i in secure_erase_devices:
                print(i)
        sys.exit()
    

def get_secure_erase_devices_iDRAC8():
    if "PCI" in args["sd"]:
        pass
    else:
        print("\n- FAIL, iDRAC 7/8 only supports secure erase operation for PCIeSSD devices")
        sys.exit()
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["sd"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code != 200:
        print("\n- FAIL, either controller not found on server or typo in controller FQDD name")
        sys.exit()
        
    if data['Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["sd"])
        sys.exit()
    else:
        for i in data[u'Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
        print("\n- WARNING, PCIe SSD devices detected for Secure Erase operation -\n")
        for i in drive_list:
            print(i)

            
def secure_erase():
    global job_id
    global job_type
    secure_erase_device=args["s"]
    controller = args["s"].split(":")[-1]
    if "Enclosure.Internal" in controller:
            controller = "CPU.1"
    else:
        pass
    if server_model_number >= 14:
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Drives/%s/Actions/Drive.SecureErase' % (idrac_ip, controller, secure_erase_device)
    else:
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s/Actions/Drive.SecureErase' % (idrac_ip, secure_erase_device)    
    headers = {'content-type': 'application/json'}
    payload = {}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    except:
        if "Enclosure.Internal.0-1" in controller:
            controller = "CPU.2"
            url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Drives/%s/Actions/Drive.SecureErase' % (idrac_ip, controller, secure_erase_device)
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
        else:
            pass
    if response.status_code == 202:
        print("\n- PASS: POST command passed to secure erase device \"%s\", status code 202 returned" % secure_erase_device)
    else:
        print("\n- FAIL, POST command failed for secure erase, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    location_search = response.headers["Location"]
    try:
        job_id = re.search("JID.+", location_search).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
        
   
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    if data['JobType'] == "RAIDConfiguration":
        job_type="staged"
    elif data['JobType'] == "RealTimeNoRebootConfiguration":
        job_type="realtime"
    print("- PASS, \"%s\" %s jid successfully created for secure erase drive \"%s\"" % (job_type, job_id, secure_erase_device))

start_time=datetime.now()

def loop_job_status():
    count = 0
    start_time = datetime.now()
    time.sleep(3)
    while True:
        if count == 10:
            print("- FAIL, retry GET job status command has reached max count retries, script will exit")
            sys.exit()
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print("- WARNING, GET command failed to get job status, retry")
            time.sleep(10)
            count+=1
            continue
            
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
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            print("- FAIL: Job ID \"%s\" failed, detailed error results: %s" % (job_id, data))
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            print("\n- WARNING, job creation to completion time is: %s" % str(datetime.now()-start_time)[0:7])
            break
        else:
            print("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
            print("- INFO, current job execution time: %s" % str(datetime.now()-start_time)[0:7])
            time.sleep(10)

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
        if data['Message'] == "Task successfully scheduled.":
            print("- PASS, staged config job marked as scheduled, powering on or rebooting the system")
            break
        else:
            print("- INFO, JobStatus not completed, current status: \"%s\"" % (data['Message']))
            print("- INFO, current job execution time: %s" % str(datetime.now()-start_time)[0:7])
            time.sleep(10)


                                                                          
def reboot_server():
    count = 1
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to attempt gracefully power OFF server, status code %s returned" % statusCode)
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            if count == 5:
                print("- WARNING, server still in ON state after 5 minutes, will force OFF server")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, Command passed to force power OFF server, status code %s returned" % statusCode)
                    return
                else:
                    print("\n- FAIL, Command failed to force power OFF server, status code is: %s\n" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
                
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            else:
                print("- WARNING, server power state still ON, will wait for 5 minutes before forcing server power off")
                count+=1
                time.sleep(60)
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code %s returned" % statusCode)
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
    get_iDRAC_version()
    if args["c"]:
        get_storage_controllers()
    elif args["d"]:
        get_controller_disks()
    elif args["sd"]:
        if server_model_number >= 14:
            get_secure_erase_devices_iDRAC9()
        else:
            get_secure_erase_devices_iDRAC8()
            
    elif args["s"]:
        secure_erase()
        if job_type == "realtime":
            loop_job_status()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()
    else:
        print("\n- FAIL, missing argument(s) or incorrect argument(s) passed in")
        


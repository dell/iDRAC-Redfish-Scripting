#
# CheckConsistencyVirtualDiskREDFISH. Python script using Redfish API to either get controllers / current virtual disks or check consistency virtual disk.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / current virtual disks or check consistency virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='CheckConsistencyVirtualDiskREDFISH -ip 192.168.0.120 -u root -p calvin -c y, this example will return storage controller FQDDs detected. CheckConsistencyVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -vv RAID.Mezzanine.1-1, this example will get detailed information for virtual disks behind controller RAID.Mezzanine.1-1. CheckConsistencyVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -cc Disk.Virtual.0:RAID.Mezzanine.1-1, this example will execute check consistency on virtual disk.')
parser.add_argument('-c', help='Get server storage controllers, pass in \"y\". For detailed controller information, pass in \"yy\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disks, pass in storage controller FQDD, Example \"RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disks detailed information, pass in storage controller FQDD, Example \"RAID.Integrated.1-1\"', required=False)
parser.add_argument('-cc', help='Pass in the virtual disk FQDD name to execute check consistency, Example \"Disk.Virtual.0:RAID.Slot.6-1\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["v"]:
    controller=args["v"]
if args["vv"]:
    controller=args["vv"]
if args["cc"]:
    virtual_disk=args["cc"]
    controller=re.search(":.+",virtual_disk).group().strip(":")



def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])
    if args["c"] =="yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                if i[0] == "Oem":
                    for ii in i[1]["Dell"]["DellController"].items():
                        print("%s: %s" % (ii[0], ii[1]))
                elif i[0] == "Status":
                    for ii in i[1].items():
                        print("%s: %s" % (ii[0], ii[1]))
                else:
                    print("%s: %s" % (i[0], i[1]))
                    
            print("\n")
    

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, status code %s returned. Check to make sure you passed in correct controller FQDD string for argument value" % response.status_code)
        sys.exit()
    if data['Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % controller)
        sys.exit()
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    print("\n- Volume(s) detected for %s controller -\n" % controller)
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))
    sys.exit()

def get_virtual_disks_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Volume(s) detected for %s controller -\n" % controller)
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
            print(i['@odata.id'].split("/")[-1])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n- Detailed Volume information for %s -\n" % ii)
        for i in data.items():
            if "@" in str(i[0]):
                pass
            elif i[0] == "Oem":
                for ii in i[1]["Dell"]["DellVirtualDisk"].items():
                    print("%s: %s" % (ii[0], ii[1]))
            elif i[0] == "Actions":
                pass
            elif i[0] == "Status":
                for ii in i[1].items():
                    print("%s: %s" % (ii[0], ii[1]))
            else:
                print("%s: %s" % (i[0], i[1]))
                    
        print("\n")



def check_consistency_vd():
    global job_id
    global job_type
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, virtual_disk),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    payload = {}
    for i in data.items():
        if i[0] == "Operations":
            if i[1] != []:
                for ii in i[1]:
                    print("\n- FAIL, Unable to run Check Consistency due to operation already executing on VD. Current operation executing is: %s, PrecentComplete %s" % (ii['OperationName'],ii['PercentageComplete']))
                    sys.exit()
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s/Actions/Volume.CheckConsistency' % (idrac_ip, virtual_disk)
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        print("\n- PASS: POST command passed to check consistency \"%s\" virtual disk, status code 202 returned" % (virtual_disk))
    else:
        print("\n- FAIL, POST command failed, status code is %s" % response.status_code)
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
    if data['JobType'] == "RAIDConfiguration":
        job_type="staged"
    elif data['JobType'] == "RealTimeNoRebootConfiguration":
        job_type="realtime"
    print("\n- PASS, \"%s\" %s jid successfully created for check consistency virtual disk\n" % (job_type, job_id))


start_time=datetime.now()

def loop_job_status():
    count_number = 0
    start_time=datetime.now()
    try:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    except requests.ConnectionError as error_message:
        print(error_message)
        sys.exit()
    data = req.json()
    if data[u'JobType'] == "RAIDConfiguration":
        print("- PASS, staged job \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
    elif data[u'JobType'] == "RealTimeNoRebootConfiguration":
        print("- PASS, realtime job \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
    print("\n- WARNING, script will now loop polling the job status until marked completed\n")
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
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or data[u'JobState'] == "Failed":
            print("\n- FAIL: job ID %s failed, detail error results: %s" % (job_id, data))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            count_number_now = data[u'PercentComplete']
            if count_number_now > count_number:
                print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
                count_number = count_number_now
                time.sleep(3)
            else:
                time.sleep(3)

def get_job_status():
    count = 0
    while True:
        if count == 5:
            print("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit()
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            print(error_message)
            print("\n- WARNING, GET request will try again to poll job status")
            time.sleep(5)
            count+=1
            continue
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
            print("- WARNING, staged config job marked as scheduled, rebooting the system")
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s\n" % data['Message'])

                                                                          
def reboot_server():
    count = 1
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
    time.sleep(20)

if __name__ == "__main__":
    if args["c"] == "y" or args["c"] =="yy":
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disks_details()
    elif args["cc"]:
        check_consistency_vd()
        if job_type == "realtime":
            loop_job_status()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()
    else:
        print("\n- FAIL, missing argument(s) or incorrect argument(s) passed in")
        


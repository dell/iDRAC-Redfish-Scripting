#
# RenameVdREDFISH. Python script using Redfish API with OEM extension to either get controllers / current virtual disks or rename virtual disk.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get controllers / current virtual disks or rename virtual disk. NOTE: Rename VD name is not supported on SWRAID volumes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='RenameVdREDFISH.py -ip 192.168.0.120 -u root -p calvin -vv Disk.Virtual.0:RAID.Integrated.1-1, this example will get detailed information for VD 0. RenameVdREDFISH.py -ip 192.168.0.120 -u root -p calvin -V Disk.Virtual.0:RAID.Integrated.1-1 -N RAID0, this example will rename VD 0 to \"RAID0\"')
parser.add_argument('-c', help='Get server storage controllers only, pass in \"y\"', required=False)
parser.add_argument('-cc', help='Get detailed information for a storage controller, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get detailed information for a virtual disk, pass in virtual disk FQDD, Example "\Disk.Virtual.0:RAID.Integrated.1-1\"', required=False)
parser.add_argument('-N', help='Pass in the new VD name you want to set. NOTE: If using whitespace in the name, make sure to surround the string value with double quotes', required=False)
parser.add_argument('-V', help='Pass in VD FQDD you want to rename, Example "\Disk.Virtual.0:RAID.Mezzanine.1-1\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["v"]:
    controller=args["v"]
if args["vv"]:
    controller=args["vv"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "RenameVD" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass    



def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_storage_controller_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["cc"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n - Detailed controller information for %s -\n" % args["cc"])
    for i in data.items():
        if i[0] == "Links" or i[0] == "Drives":
            pass
        elif i[0] == "Status":
            for ii in i[1].items():
                print("%s: %s" % (ii[0], ii[1]))
        elif i[0] == "StorageControllers":
            for ii in i[1]:
                for iii in ii.items():
                    print("%s: %s" % (iii[0], iii[1]))
        elif i[0] == "Oem":
            try:
                for ii in i[1]["Dell"]["DellControllerBattery"].items():
                    print("%s: %s" % (ii[0],ii[1]))
            except:
               pass
            try:
                for ii in i[1]["Dell"]["DellController"].items():
                    print("%s: %s" % (ii[0],ii[1]))
            except:
               pass
    
        else:
            print("%s: %s" % (i[0], i[1]))

def get_controller_boot_VD():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["gb"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    count = 0
    if "AHCI" in args["gb"]:
        print("\n- WARNING, AHCI controllers do not support setting boot VD")
        sys.exit()
    else:
        pass
        
    for i in data.items():
        if i[0] == "Oem":
            try:
                print("\n- Current boot VD for controller %s: %s" % (args["gb"],i[1]["Dell"]["DellController"]["BootVirtualDiskFQDD"]))
                count+=1
                return
            except:
               pass
    if count == 0:
        print("\n- FAIL, unable to get current boot VD or controller doesn't support setting boot VD")

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("- FAIL, GET command failed, error is: %s" % data)
        sys.exit()
    vd_list=[]
    if data['Members'] == []:
        print("\n- WARNING, no volumes detected for %s" % controller)
        sys.exit()
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    print("\n- Virtual disk(s) detected for controller %s -" % controller)
    print("\n")
    supported_vds=[]
    volume_type=[]
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                if i[1] != "RawDevice":
                    supported_vds.append(ii)
                    volume_type.append(i[1])
                else:
                    pass
    if supported_vds == []:
        print("- WARNING, no virtual disk(s) detected for controller %s" % controller)
    else:
        for i,ii in zip(supported_vds,volume_type):
            print("%s, Volume Type: %s" % (i, ii))
    sys.exit()

def get_virtual_disks_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, args["vv"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n - Detailed Volume information for %s -\n" % args["vv"]) 
    for i in data.items():
        if i[0] == "Oem":
            for ii in i[1]["Dell"]["DellVirtualDisk"].items():
                print("%s: %s" % (ii[0],ii[1]))
                
            sys.exit()
        if i[0] == "Actions" or i[0] == "@Redfish.Settings":
            pass
        else:
            print("%s: %s" % (i[0],i[1]))

def get_config_job_type():
    global job_type
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['StorageControllers']:
        for ii in i.items():
            if ii[0] == "Model":
                if "BOSS" in ii[1] or "S1" in ii[1]:
                    job_type="staged"
                elif "H3" in ii[1] or "H7" in ii[1] or "H8" in ii[1]:
                    job_type="realtime"

def rename_vd():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.RenameVD' % (idrac_ip)
    payload={"Name":args["N"], "TargetFQDD":args["V"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: POST command passed to rename VD, status code %s returned" % response.status_code)
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
    print("\n- PASS, \"%s\" %s jid successfully created to rename VD\n" % (job_type, job_id))


start_time=datetime.now()

def loop_job_status():
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
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", job execution time: \"%s\"" % (data['Message'],str(current_time)[0:7]))
            time.sleep(5)

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
            print("\n- WARNING, staged config job marked as scheduled, rebooting the system\n")
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", job execution time: \"%s\"" % (data['Message'],str(current_time)[0:7]))
            time.sleep(5)


                                                                          
def reboot_server():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': 'ForceOff'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power OFF server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    time.sleep(10)
    payload = {'ResetType': 'On'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=('root','calvin'))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()

def check_new_vd_name():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, args["V"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if data['Description'] == args["N"]:
        print("\n- PASS, VD name successfully changed to \"%s\"" % args["N"])
    else:
        print("\n- FAIL, VD name not changed to \"%s\", current VD name is \"%s\"" % (args["N"], data['Description']))
        sys.exit()
    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["cc"]:
        get_storage_controller_details()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disks_details()
    elif args["N"] and args["V"]:
        rename_vd()
        if job_type == "realtime":
            loop_job_status()
            check_new_vd_name()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()
            check_new_vd_name()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    

        


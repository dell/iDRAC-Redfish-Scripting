#
# DeleteVirtualDiskREDFISH. Python script using Redfish API to either get controllers / current virtual disks or delete virtual disk.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / current virtual disks or delete virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-cc', help='Get detailed server storage controller information, pass in \"y\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller volumes detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-D', help='Pass in virtual disk FQDD to delete virtual disk, Example "\Disk.Virtual.0:RAID.Mezzanine.1-1\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["v"]:
    controller=args["v"]
elif args["c"]:
    pass
elif args["vv"]:
    controller=args["vv"]
elif args["D"]:
    virtual_disk=args["D"]
    controller=re.search(":.+",virtual_disk).group().strip(":")
else:
    print("- FAIL, you must pass in at least one agrument with -ip, -u and -p")
    sys.exit()

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
        print(i[u'@odata.id'][46:])
    if args["cc"]:
      for i in controller_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          print("\n - Detailed controller information for %s -\n" % i)
          for i in data.items():
                print("%s: %s" % (i[0], i[1]))
    else:
        pass
    

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % controller)
        sys.exit()
    else:
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
    print("\n- Supported virtual disk(s) detected to delete for controller %s -" % controller,)
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
        print("- WARNING, no virtual disk(s) detected to delete for controller %s" % controller)
    else:
        for i,ii in zip(supported_vds,volume_type):
            print("%s, Volume Type: %s" % (i, ii))
    sys.exit()

def get_virtual_disks_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Volume(s) detected for %s controller -\n" % controller)
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
            print(i[u'@odata.id'][54:])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n - Detailed Volume information for %s -\n" % ii)
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))
                
    sys.exit()



def get_config_job_type():
    global job_type
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data[u'StorageControllers']:
        for ii in i.items():
            if ii[0] == "Model":
                if "BOSS" in ii[1] or "S1" in ii[1]:
                    job_type="staged"
                elif "H3" in ii[1] or "H7" in ii[1] or "H8" in ii[1]:
                    job_type="realtime"


def delete_vd():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, virtual_disk)
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        print("\n- PASS: DELETE command passed to delete \"%s\" virtual disk, status code 202 returned" % virtual_disk)
    else:
        print("\n- FAIL, DELETE command failed, status code is %s" % response.status_code)
        data = response.json()
        print("\n- DELETE command failure is:\n %s" % data)
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
    print("\n- PASS, \"%s\" %s jid successfully created for delete virtual disk\n" % (job_type, job_id))


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
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data[u'Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", precent completion is: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            

def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            print("\n- PASS, Command passed to check job status, code 200 returned")
            time.sleep(5)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print("\n- WARNING, staged config job marked as scheduled, rebooting the system\n")
            break
        else:
            print("\n- WARNING: JobStatus not scheduled, current status is: %s\n" % data[u'Message'])

                                                                          
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
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"] or args["cc"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disks_details()
    elif args["D"]:
        delete_vd()
        if job_type == "realtime":
            loop_job_status()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()


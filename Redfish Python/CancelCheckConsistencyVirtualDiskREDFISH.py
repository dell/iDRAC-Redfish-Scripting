#
# CancelCheckConsistencyREDFISH. Python script using Redfish API with OEM extension to cancel check consistency on virtual disk
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
#


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to cancel check consistency on virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='CancelCheckConsistencyVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will return storage controller FQDDs detected. CancelCheckConsistencyVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -cc Disk.Virtual.0:RAID.Mezzanine.1-1, this example will cancel check consistency for this VD.') 
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get detailed information for each virtual disk detected by storage controller, pass in storage controller FQDD, Example \"RAID.Integrated.1-1\"', required=False)
parser.add_argument('-cc', help='Cancel check consistency for storage controller, pass in the virtual disk FQDD, Example \"Disk.Virtual.0:RAID.Mezzanine.1-1\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]



def check_supported_idrac_version():
    supported = "no"
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Actions'].items():
        if "CancelCheckConsistency" in i[1]["target"]:
            supported = "yes"
    if supported == "yes":
        pass
    else:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    
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
        for ii in i.items():
            controller = ii[1].split("/")[-1]
            controller_list.append(controller)
            print(controller)
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
    else:
        pass
    sys.exit()
    

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["v"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["v"])
        sys.exit()
    else:
        for i in data[u'Members']:
            for ii in i.items():
                vd = ii[1].split("/")[-1]
                vd_list.append(vd)
    print("\n- Volume(s) detected for %s controller -\n" % args["v"])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))
    sys.exit()


def get_virtual_disks_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["vv"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["vv"])
        sys.exit()
    else:
        print("\n- Volume(s) detected for %s controller -\n" % args["vv"])
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
        

def cancel_check_consistency():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.CancelCheckConsistency' % (idrac_ip)
    method = "CancelCheckConsistency"
    headers = {'content-type': 'application/json'}
    payload={"TargetFQDD": args["cc"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed to cancel check consistency for virtual disk %s, status code %s returned" % (args["cc"], response.status_code))
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
    else:
        print("\n-FAIL, POST command failed to cancel check consistency for virtual disk %s, status code is %s" % (args["cc"], response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

def loop_job_status():
    count_number = 0
    start_time=datetime.now()
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    if data[u'JobType'] == "RAIDConfiguration":
        print("- PASS, staged jid \"%s\" successfully created. Server will now reboot to apply the configuration changes" % job_id)
    elif data[u'JobType'] == "RealTimeNoRebootConfiguration":
        print("- PASS, realtime jid \"%s\" successfully created. Server will apply the configuration changes in real time, no server reboot needed" % job_id)
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
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
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
            

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disks_details()
    elif args["cc"]:
        cancel_check_consistency()
        loop_job_status()
    else:
        print("\n- FAIL, missing argument(s) or incorrect argument(s) passed in")
    
    
        
            
        
        

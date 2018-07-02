#
# CreateVirtualDiskREDFISH. Python script using Redfish API to either get controllers / disks / virtual disks / supported RAID levels or create virtual disk.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / disks / virtual disks / supported RAID levels or create virtual disk")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-cc', help='Pass in controller FQDD, this argument is used with -s to get support RAID levels for the controller', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disk detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-s', help='Get current supported volume types (RAID levels) for your controller, pass in \"y\". You must use agrument -cc with your controller FQDD', required=False)
parser.add_argument('-C', help='Pass in controller FQDD to create virtual disk, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-D', help='Pass in disk FQDD to create virtual disk, pass in storage disk FQDD, Example \"Disk.Bay.2:Enclosure.Internal.0-1:RAID.Mezzanine.1-1\". You can pass in multiple drives, just use a comma seperator between each disk FQDD string', required=False)
parser.add_argument('-R', help='Pass in the RAID level you want to create. Possible supported values are: 0, 1, 5, 10 and 50. You must also pass in arguments -V, -C and -D', required=False)
parser.add_argument('-V', help='Create virtual disk, pass in \"y\". You must also pass in arguments -C and -D', required=False)
parser.add_argument('--size', help='Pass in the size(CapacityBytes) in bytes for VD creation. This is OPTIONAL, if you don\'t pass in the size, VD creation will use full disk size to create the VD', required=False)
parser.add_argument('--stripesize', help='Pass in the stripesize(OptimumIOSizeBytes) in kilobytes for VD creation. This is OPTIONAL, if you don\'t pass in stripesize, controller will use the default value', required=False)
parser.add_argument('--name', help='Pass in the name for VD creation. This is OPTIONAL, if you don\'t pass in name, controller will use the default value', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["d"]:
    controller=args["d"]
elif args["c"]:
    pass
elif args["dd"]:
    controller=args["dd"]
elif args["v"]:
    controller=args["v"]
elif args["vv"]:
    controller=args["vv"]
elif args["cc"]:
    controller=args["cc"]
elif args["C"] and args["D"] and args["V"] and args["R"]:
    controller=args["C"]
    disks=args["D"]
    raid_levels={"0":"NonRedundant","1":"Mirrored","5":"StripedWithParity","10":"SpannedMirrors","50":"SpannedStripesWithParity"}
    try:
        volume_type=raid_levels[args["R"]]
    except:
        print("\n- FAIL, invalid RAID level value entered")
        sys.exit()
    if args["size"]:
        vd_size=int(args["size"])
    if args["stripesize"]:
        vd_stripesize=int(args["stripesize"])
    if args["name"]:
        vd_name=args["name"]
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

def get_supported_RAID_levels():
    non_supported = ""
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data[u'StorageControllers']:
        for ii in i.items():
            if ii[0] == "Model":
                if "BOSS" in ii[1]:
                    job_type="staged"
                    if args["s"]:
                        print("\nSupported RAID levels for %s controller are: \"Mirrored\" or RAID 1" % (controller))
                    else:
                        pass
                elif "AHCI" in ii[1] or "PCIe" in ii[1] or "HBA" in ii[1]:
                    if args["s"]:
                        print("\nController \"%s\" does not support creating virtual disks" % controller)
                        non_supported = "yes"
                elif "S1" in ii[1]:
                    if args["s"]:
                        print("\nSupported RAID levels for %s controller are:\n\n- \"NonRedundant\" or RAID 0\n- \"Mirrored\" or RAID 1\n- \"StripedWithParity\" or RAID 5\n- \"SpannedMirrors\" or RAID 10" % (controller))
                elif "H3" in ii[1] or "H7" in ii[1] or "H8" in ii[1]:
                    if args["s"]:
                        print("\nSupported RAID levels for %s controller are:\n\n- \"NonRedundant\" or RAID 0\n- \"Mirrored\" or RAID 1\n- \"StripedWithParity\" or RAID 5\n- \"SpannedMirrors\" or RAID 10\n- \"SpannedStripesWithParity\" or RAID 50" % (controller))    
           

    
def get_pdisks():
    disk_used_created_vds=[]
    available_disks=[]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % controller)
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
            print(i[u'@odata.id'][53:])
    if args["dd"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          
          print("\n - Detailed drive information for %s -\n" % i)
          for ii in data.items():
              print("%s: %s" % (ii[0],ii[1]))
              if ii[0] == "Links":
                  print "\n"
                  if ii[1]["Volumes"] != []:
                      disk_used_created_vds.append(i)
                  else:
                      available_disks.append(i) 

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
    print("\n- Volume(s) detected for %s controller -" % controller)
    print("\n")
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))
    sys.exit()

def get_virtual_disk_details():
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
        
    


def create_raid_vd():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, controller)
    disks_list=disks.split(",")
    final_disks_list=[]
    for i in disks_list:
        s="/redfish/v1/Systems/System.Embedded.1/Storage/Drives/"+i
        d={"@odata.id":s}
        final_disks_list.append(d)
    payload = {"VolumeType":volume_type,"Drives":final_disks_list}
    try:
        payload["CapacityBytes"]=vd_size
    except:
        pass
    try:
        payload["OptimumIOSizeBytes"]=vd_stripesize
    except:
        pass
    try:
        payload["Name"]=vd_name
    except:
        pass
    
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202:
        print("\n- PASS: POST command passed to create \"%s\" virtual disk, status code 202 returned" % volume_type)
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
    if data[u'JobType'] == "RAIDConfiguration":
        job_type="staged"
    elif data[u'JobType'] == "RealTimeNoRebootConfiguration":
        job_type="realtime"
    print("\n- PASS, \"%s\" %s jid successfully created for create virtual disk" % (job_type, job_id))
    
start_time=datetime.now()

def loop_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            #print("\n- PASS, Command passed to check job status, code 200 returned")
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
                    print "%s: %s" % (i[0],i[1])
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", precent completion is: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(5)

def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            #print("\n- PASS, Command passed to check job status, code 200 returned")
            time.sleep(5)
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print "\n- WARNING, staged config job marked as scheduled, rebooting the system\n"
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
    if args["c"]:
        get_storage_controllers()
    elif args["d"] or args["dd"]:
        get_pdisks()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disk_details()
    elif args["cc"] and args["s"]:
        get_supported_RAID_levels()
    elif args["C"] and args["D"] and args["V"] and args["R"]:
        create_raid_vd()
        if job_type == "realtime":
            loop_job_status()
        elif job_type == "staged":
            get_job_status()
            reboot_server()
            loop_job_status()
    
        
            
        
        

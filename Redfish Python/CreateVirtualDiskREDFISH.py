#
# CreateVirtualDiskREDFISH. Python script using Redfish API to either get controllers / disks / virtual disks / supported RAID levels or create virtual disk.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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
parser.add_argument('script_examples',action="store_true",help='CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -v RAID.Slot.6-1, this example will get current volumes for RAID controller RAID.Slot.6-1. CreateVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -C RAID.Slot.6-1 -V y -D Disk.Bay.0:Enclosure.Internal.0-1:RAID.Slot.6-1 -R 0, this example will create a one disk RAID 0 volume')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-cc', help='Pass in controller FQDD, this argument is used with -s to get support RAID levels for the controller', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disk detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-e', help='Get current server storage enclosure information, pass in \"y\"', required=False)
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
elif args["e"]:
    pass
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

def get_storage_enclosures():
    response = requests.get('https://%s/redfish/v1/Chassis' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    backplane_uris = []
    if len(data['Members']) == 1:
        print("\n- FAIL, no backplanes detected for server. Either backplane type not supported to get data and server has no backplane")
        sys.exit()
    print("\n - Backplane URIs detected for server -\n")
    for i in data['Members']:
        for ii in i.items():
            if ii[1] == '/redfish/v1/Chassis/System.Embedded.1':
                pass
            else:
                print(ii[1])
                backplane_uris.append(ii[1])
    for i in backplane_uris:
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        print("\n- Detailed information for URI \"%s\" -\n" % i)
        data = response.json()
        for ii in data.items():
            if ii[0] == 'Oem':
                for iii in ii[1]['Dell']['DellEnclosure'].items():
                    print("%s: %s" % (iii[0],iii[1]))
            else:
                print("%s: %s" % (ii[0],ii[1]))
        
        
    sys.exit()

def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
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
                if i[0] == 'Status':
                    pass
                elif "@" in i[0] or "odata" in i[0]:
                    pass
                elif i[0] == 'StorageControllers':
                    for ii in i[1]:
                        for iii in ii.items():
                            if iii[0] == 'Status':
                                for iiii in iii[1].items():
                                    print("%s: %s" % (iiii[0],iiii[1]))
                            else:
                                print("%s: %s" % (iii[0],iii[1]))
                elif i[0] == 'Oem':
                    try:
                        for ii in i[1]['Dell']['DellController'].items():
                            print("%s: %s" % (ii[0],ii[1]))
                    except:
                        for ii in i[1]['Dell'].items():
                            print("%s: %s" % (ii[0],ii[1]))
                    
                else:
                    print("%s: %s" % (i[0], i[1]))
    else:
        pass
    sys.exit()

def get_supported_RAID_levels():
    non_supported = ""
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['StorageControllers']:
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
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("- FAIL, GET command failed, detailed error information: %s" % data)
        sys.exit()
    if data['Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % controller)
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i['@odata.id'].split("/")[-1]),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data['Links']['Volumes'] == []:
                print("Disk: %s, RaidStatus: Disk is not part of a RAID volume" % (i['@odata.id'].split("/")[-1]))
            else:
                print("Disk: %s, RaidStatus: Disk is part of a RAID volume, RAID volume is: %s" % (i['@odata.id'].split("/")[-1],data['Links']['Volumes'][0]['@odata.id'].split("/")[-1] ))
    if args["dd"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          
          print("\n - Detailed drive information for %s -\n" % i)
          for ii in data.items():
              if ii[0] == 'Oem':
                  for iii in ii[1]['Dell']['DellPhysicalDisk'].items():
                      print("%s: %s" % (iii[0],iii[1]))
                  #sys.exit()
              elif ii[0] == 'Status':
                  for iii in ii[1].items():
                      print("%s: %s" % (iii[0],iii[1]))
              #else:
              #    print("%s: %s" % (ii[0],ii[1]))
              elif ii[0] == "Links":
                  if ii[1]["Volumes"] != []:
                      disk_used_created_vds.append(i)
                  else:
                      available_disks.append(i)
              else:
                  print("%s: %s" % (ii[0],ii[1]))

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
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, status code %s returned. Check to make sure you passed in correct controller FQDD string for argument value" % response.status_code)
        sys.exit()
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
        print("\n - Detailed Volume information for %s -\n" % ii)
        for i in data.items():
            if i[0] == 'Oem':
                  for ii in i[1]['Dell']['DellVirtualDisk'].items():
                      print("%s: %s" % (ii[0],ii[1]))
                  
            elif i[0] == 'Status':
                for ii in i[1].items():
                    print("%s: %s" % (ii[0],ii[1]))
            else:
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
    if data['JobType'] == "RAIDConfiguration":
        job_type="staged"
    elif data['JobType'] == "RealTimeNoRebootConfiguration":
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
            print("- WARNING, JobStatus not completed, current status is: \"%s\", percent completion is: \"%s\"" % (data['Message'],data['PercentComplete']))
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
        if data['Message'] == "Task successfully scheduled.":
            print("\n- WARNING, staged config job marked as scheduled, rebooting the system\n")
            break
        else:
            print("\n- WARNING: JobStatus not scheduled, current status is: %s\n" % data['Message'])


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
        count = 0
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            elif count == 20:
                print("- WARNING, unable to graceful shutdown the server, will perform forced shutdown now")
                url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, Command passed to forcefully power OFF server, code return is %s" % statusCode)
                    time.sleep(15)
                    break
                else:
                    print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
                    print("Extended Info Message: {0}".format(response.json()))
                    sys.exit()
                
            else:
                time.sleep(2)
                count+=1
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

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["e"]:
        get_storage_enclosures()
    elif args["d"]:
        get_pdisks()
    elif args["dd"]:
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
    else:
        print("- WARNING, missing or incorrect arguments passed in for executing script")
    
        
            
        
        

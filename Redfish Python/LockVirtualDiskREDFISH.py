#
# LockVirtualDiskREDFISH. Python script using Redfish API with OEM extension to lock a virtual disk.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to lock a virtual disk. Encryption or controller key must already be set on the controller and virtual disk created with SED(self encrypting drive) drives")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -cl RAID.Mezzanine.1-1, this exampe will return current virtual disks detected and their lock status for controller RAID.Mezzanine.1-1. LockVirtualDiskREDFISH.py -ip 192.168.0.120 -u root -p calvin -l Disk.Virtual.0:RAID.Mezzanine.1-1, this example will lock VD 0 on controller RAID.Mezzanine.1-1')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-e', help='Get drive encryption capability, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disk detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-cl', help='Check for current locked virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-l', help='Lock virtual disk, pass in the virtual disk FQDD, Example \"Disk.Virtual.0:RAID.Integrated.1-1\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

if args["d"]:
    controller = args["d"]
if args["dd"]:
    controller = args["dd"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
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
          

def check_drive_capabiity():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["e"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["e"])
        sys.exit()
    else:
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
    print("\n - WARNING, Disk FQDD, encryption ability status for controller %s disk(s)\n" % args["e"])
    for i in drive_list:
      response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
      data = response.json()
      for ii in data.items():
          if ii[0] == "EncryptionAbility":
              print("%s: EncryptionAbility: %s" % (i,ii[1]))
             

def get_virtual_disks():
    test_valid_controller_FQDD_string(args["v"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["v"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["v"])
        sys.exit()
    else:
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
    print("\n- Volume(s) detected for %s controller -\n" % args["v"])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))
    sys.exit()

def get_virtual_disk_details():
    test_valid_controller_FQDD_string(args["vv"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["vv"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["vv"])
        sys.exit()
    else:
        print("\n- Volume(s) detected for %s controller -\n" % args["vv"])
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

def check_lock_VDs():
    test_valid_controller_FQDD_string(args["cl"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["cl"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["cl"])
        sys.exit()
    else:
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
    print("\n- Volume(s) detected for %s controller -\n" % args["cl"])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "Encrypted":
                print("%s, Encrypted(Lock) Status: %s" % (ii, i[1]))
    sys.exit()


def lock_VD():
    global job_id
    method = "LockVirtualDisk"
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.LockVirtualDisk' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"TargetFQDD": args["l"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n-PASS: POST command passed to lock virtual disk \"%s\"" % args["l"])
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
    else:
        print("\n-FAIL, POST command failed to lock virtual disk \"%s\"" % args["l"])
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

def check_vd_lock_status():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, args["l"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data.items():
        if i[0] == "Encrypted":
            if i[1] == True:
                print("\n- PASS, virtual disk %s is now locked and encrypted" % args["l"])
            elif i[1] == False:
                print("\n- FAIL, virtual disk %s is NOT locked and encrypted" % args["l"])

def loop_job_status():
    start_time=datetime.now()
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
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(3)

def test_valid_controller_FQDD_string(x):
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        print("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string value is case sensitive)")
        sys.exit()
    else:
        pass    
    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disk_details()
    elif args["d"] or args["dd"]:
        get_pdisks()
    elif args["e"]:
        check_drive_capabiity()
    elif args["cl"]:
        check_lock_VDs()
    elif args["l"]:
        lock_VD()
        loop_job_status()
        check_vd_lock_status()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
        

    
        
    
    
        
            
        
        

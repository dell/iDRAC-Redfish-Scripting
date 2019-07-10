#
# AssignHotSpareREDFISH. Python script using Redfish API to either assign dedicated or global hot spare
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2019, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to assign either dedicated or global hot spare")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='AssignHotSpareREDFISH.py -ip 192.168.0.120 -u root -p calvin -H RAID.Mezzanine.1-1, this example will get disks and their hotspare status for controller RAID.Mezzanine.1-1. AssignHotSpareREDFISH.py -ip 192.168.0.120 -u root -p calvin -t global -a Disk.Bay.5:Enclosure.Internal.0-1:RAID.Mezzanine.1-1, this example will assign disk 5 as a global hotspare') 
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-H', help='Get current hot spare type for each drive, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disk detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-t', help='Pass in the type of hot spare you want to assign. Supported values are \"dedicated\" and \"global\"', required=False)
parser.add_argument('-a', help='Assign global or dedicated hot spare, pass in disk FQDD, Example \"Disk.Bay.0:Enclosure.Internal.0-1:RAID.Slot.6-1\". Note: You must use -V with -a if you want to assign dedicated hot spare', required=False)
parser.add_argument('-V', help='Pass in virtual disk FQDD you want to assign the dedicated hot spare disk.Note: -a is required along with -V for assign DHS', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["d"]:
    controller=args["d"]
elif args["dd"]:
    controller=args["dd"]
elif args["H"]:
    controller=args["H"]
elif args["c"]:
    pass
elif args["v"]:
    controller=args["v"]

    

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


def get_pdisks():
    disk_used_created_vds=[]
    available_disks=[]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    try:
        if data[u'Drives'] == []:
            print("\n- WARNING, no drives detected for %s" % controller)
            sys.exit()
        else:
            print("\n- Drive(s) detected for %s -\n" % controller)
            for i in data[u'Drives']:
                for ii in i.items():
                    disk = ii[1].split("/")[-1]
                    drive_list.append(disk)
                    print(disk)
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
    except:
        print("\n- FAIL, GET command failed. Check to make sure you passed in correct controller FQDD")


def get_pdisks_hot_spare_type():
    test_valid_controller_FQDD_string(controller)
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % controller)
        sys.exit()
    else:
        for i in data[u'Drives']:
            for ii in i.items():
                disk = ii[1].split("/")[-1]
                drive_list.append(disk)
    print("\n- Drive FQDDs/Hot Spare Type for Controller %s -\n" % controller)
    if args["H"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          for ii in data.items():
              if ii[0] == "HotspareType":
                  print("%s: Hot Spare Type: %s" % (i,ii[1]))  

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
            for ii in i.items():
                vd = ii[1].split("/")[-1]
                vd_list.append(vd)
                print(vd)
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n - Detailed Volume information for %s -\n" % ii)
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))


def assign_spare():
    global job_id
    method = "AssignSpare"
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.AssignSpare' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    if args["t"].lower() == "global":
        payload={"TargetFQDD":args["a"]}
    elif args["t"].lower() == "dedicated":
        payload={"TargetFQDD":args["a"],"VirtualDiskArray":[args["V"]]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n-PASS: POST command passed to set disk \"%s\" as \"%s\" hot spare" % (args["a"], args["t"]))
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method))
    else:
        print("\n-FAIL, POST command failed to set disk %s as %s hot spare" % (args["a"], args["t"]))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

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

def get_pdisk_hot_spare_final_status():
      response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, args["a"]),verify=False,auth=(idrac_username, idrac_password))
      data = response.json()
      for i in data.items():
          if i[0] == "HotspareType":
              if i[1] == args["t"].title():
                  print("\n- PASS, disk \"%s\" successfully set to \"%s\" hotspare" % (args["a"], i[1]))
              else:
                  print("\n- FAIL, disk \"%s\" not set to \"%s\" hotspare, current hot spare status is %s" % (args["a"], args["t"], i[1]))
                  sys.exit()

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["d"] or args["dd"]:
        get_pdisks()
    elif args["H"]:
        get_pdisks_hot_spare_type()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disk_details()
    elif args["a"] or args["V"] and args["t"]:
        assign_spare()
        loop_job_status()
        get_pdisk_hot_spare_final_status()
        
    
    
        
            
        
        

#
# ClearForeignConfigREDFISH. Python script using Redfish API with OEM extension to clear a storage controller foreign configuration
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to clear a storage controller foreign configuration")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ClearForeignConfigREDFISH.py -ip 192.168.0.120 -u root -p calvin -f RAID.Slot.6-1, this example will clear foreign configuration for RAID controller RAID.Slot.6-1')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs and their raid status only (check for foreign disks), pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-f', help='Clear foreign configuration for storage controller, pass in the controller FQDD, Example \"RAID.Slot.6-1\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


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
    


def get_pdisks_check_raidstatus():
    test_valid_controller_FQDD_string(args["d"])
    disk_used_created_vds=[]
    available_disks=[]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["d"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["d"])
        sys.exit()
    else:
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
    print("\n- Drives detected for controller \"%s\" and RaidStatus\n" % args["d"])
    foreign_disks_detected=[]
    for i in drive_list:
      response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
      data = response.json()
      
      print(" - Disk %s, Raidstatus %s" % (i, data[u'Oem'][u'Dell'][u'DellPhysicalDisk'][u'RaidStatus']))
      if data[u'Oem'][u'Dell'][u'DellPhysicalDisk'][u'RaidStatus'] == "Foreign":
          foreign_disks_detected.append(i)
    if foreign_disks_detected != []:
        print("\n- WARNING, foreign configurations detected for controller %s" % args["d"])
        sys.exit()
    else:
        print("\n- WARNING, no foreign configurations detected for controller %s" % args["d"])
        sys.exit()
          
              

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




def clear_foreign_config():
    global job_id
    method = "ClearForeignConfig"
    test_valid_controller_FQDD_string(args["f"])
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ClearForeignConfig' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"TargetFQDD": args["f"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed to clear foreign configuration for controller %s, status code %s returned" % (args["f"], response.status_code))
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created for RAID method \"%s\"" % (job_id, method))
    else:
        print("\n-FAIL, POST command failed to reset storage controller %s, status code is %s" % (args["f"], response.status_code))
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

def check_foreign_cleared():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["f"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("- FAIL, GET command failed, detailed error results: %s" % data)
        sys.exit()
    else:
        pass
    drive_list=[]
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["d"])
        sys.exit()
    else:
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'][53:])
    foreign_disks_detected=[]
    for i in drive_list:
      response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
      data = response.json()
      if data[u'Oem'][u'Dell'][u'DellPhysicalDisk'][u'RaidStatus'] == "Foreign":
          foreign_disks_detected.append(i)
    if foreign_disks_detected != []:
        print("\n- FAIL, foreign configurations still detected for controller %s" % args["f"])
        sys.exit()
    else:
        print("\n- PASS, no foreign configurations detected for controller %s" % args["f"])
        sys.exit()
    
    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["f"]:
        clear_foreign_config()
        loop_job_status()
        check_foreign_cleared()
    elif args["d"]:
        get_pdisks_check_raidstatus()
        
    
    
        
            
        
        

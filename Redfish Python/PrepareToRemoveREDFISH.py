#
# PrepareToRemoveREDFISH. Python script using Redfish API with OEM extension to safely prepare to remove PCIeSSD / NVMe drive.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to execute prepare to remove operation for PCIeSSD/NVMe drive. Executing this operation allows PCIeSSD/NVMe drive to be removed safely. NOTE: iDRAC Service Module (ISM) must be installed and service running in the OS for prepare to remove operation to be supported.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='PrepareToRemoveREDFISH.py -ip 192.168.0.120 -u root -p calvin -d CPU.1, this example will get available PCIeSSD drives for PCIeSSD controller CPU.1. Note: CPU.1 controller is direct attach PCIeSSD configuration. PrepareToRemoveREDFISH.py -ip 192.168.0.120 -u root -p calvin -R Disk.Bay.7:Enclosure.Internal.0-1, this example will perform prepare to remove operation on PCIeSSD disk in bay 7.')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-d', help='Get PCIe SSD disk FQDDs only, pass in PCIeSSD controller FQDD, Example \"CPU.1\"', required=False)
parser.add_argument('-dd', help='Get PCIe SSD disks detailed information, pass in PCIeSSD controller FQDD, Example \"CPU.1\"', required=False)
parser.add_argument('-I', help='Verify if iDRAC Service Module (ISM) is running in the OS, pass in \"y\"', required=False)
parser.add_argument('-R', help='Pass in the PCIeSSD / NVMe drive to perform prepare to remove operation', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

    

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
        if "PrepareToRemove" in i:
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

    
    
def get_pdisks():
    disk_used_created_vds=[]
    available_disks=[]
    if args["d"]:
        controller = args["d"]
    elif args["dd"]:
        controller = args["dd"]
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
        for i in data['Drives']:
            drive_list.append(i['@odata.id'].split("/")[-1])
        available_disks = []
        for i in drive_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if str(data['Oem']['Dell']['DellPhysicalDisk']['RaidStatus']) == "None":
                available_disks.append(i)
            else:
                pass
                
        if available_disks == []:
            print("\n- WARNING, no PCIeSSD drives availabe for prepare to remove operation for controller \"%s\"" % controller)
        else:
             print("\n- PCIeSSD drive(s) available for prepare to remove operation for controller \"%s\" -\n" % controller)
             for i in available_disks:
                 print(i)
        
            
            
    if args["dd"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          
          print("\n - Detailed drive information for %s -\n" % i)
          for ii in data.items():
              if ii[0] == 'Oem':
                  for iii in ii[1]['Dell']['DellPhysicalDisk'].items():
                      print("%s: %s" % (iii[0],iii[1]))
              elif ii[0] == 'Status':
                  for iii in ii[1].items():
                      print("%s: %s" % (iii[0],iii[1]))
              elif ii[0] == "Links":
                  if ii[1]["Volumes"] != []:
                      disk_used_created_vds.append(i)
                  else:
                      available_disks.append(i)
              else:
                  print("%s: %s" % (ii[0],ii[1]))


def get_ISM_status():
    print("\n- WARNING, checking to see if iDRAC Service Module (ISM) is running in the OS\n")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == "ServiceModule.1.ServiceModuleState":
            if attributes_dict[i] == "Running":
                print("- PASS, iDRAC Service Module (ISM) is running in the OS")
                sys.exit()
            else:
                print("- FAIL, iDRAC Service Module (ISM) is not running in the OS. Check the OS to make sure the service is running")
                sys.exit()
        
    print("\n- FAIL, unable to get iDRAC Service Module (ISM) status. Either current iDRAC version installed doesn\'t support this attribute or iDRAC missing required license")
    

def prepare_to_remove():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.PrepareToRemove' % (idrac_ip)
    payload = {"TargetFQDD": args["R"]}
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for prepare to remove operation, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, POST command failed, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    job_id_search=response.headers["Location"]
    try:
        job_id=re.search("JID.+",job_id_search).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
        
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    print("\n- PASS, JID %s successfully created for prepare to remove operation" % (job_id))
    
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
            print("\n- WARNING, PCIeSSD drive \"%s\" is ready to be removed. Drive carrier should now be blinking to identify." % args["R"])
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"" % (data['Message']))
            time.sleep(5)



if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["d"]:
        get_pdisks()
    elif args["dd"]:
        get_pdisks()
    elif args["I"]:
        get_ISM_status()
    elif args["R"]:
        prepare_to_remove()
        loop_job_status()
        
    else:
        print("- WARNING, missing or incorrect arguments passed in for executing script")
    
        
            
        
        

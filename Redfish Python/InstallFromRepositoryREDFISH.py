#!/usr/bin/python
# InstallFromRepositoryREDFISH. Python script using Redfish API with OEM extension to either get firmware version for all devices, get repository update list or install firmware from a repository on a network share.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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


import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get firmware version for all devices, get repository update list or install firmware from a repository on a network share.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate False --sharetype CIFS, this example to going to download the catalog file from the CIFS share repostiory but not install any updates. It\'s recommmended now to execute the script with -r argument to verify the repo update list. InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate True --sharetype CIFS --rebootneeded True, this example is going to install updates from the CIFS share repository and apply them. If updates need a server reboot to apply, it will also reboot the server. InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 143.166.147.76 --sharetype HTTP --applyupdate True --rebootneeded True, this example shows using Dell HTTP downloads repository which is recommended to use. This repository is updated with the latest firmware versions for all devices iDRAC supports for updates.')
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware version, pass in \"y\"', required=False)
parser.add_argument('-r', help='Get repository update list, pass in \"y\". Output will be returned in XML format. You must first execute install from repository but don\'t apply updates to get the repository update list', required=False)
parser.add_argument('-i', help='Install from repository, pass in \"y\"', required=False)
parser.add_argument('-c', help='Get device name and criticality information only from repository update list XML, pass in \"y\". You must first execute install from repository but don\'t apply updates to get the repository update list', required=False)
parser.add_argument('-q', help='Get current job ids in the job queue, pass in a value of \"y\"', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS. NOTE: For HTTP/HTTPS, recommended to use either IIS or Apache.', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--applyupdate', help='Pass in True if you want to apply the updates. Pass in False will not apply updates but you can get the repo update list now. NOTE: This argument is optional. If you don\'t pass in the argument, default value is True.', required=False)
parser.add_argument('--rebootneeded', help='Pass in True to reboot the server to apply updates which need a server reboot. False means the updates will get staged but not get applied until next manual server reboot. NOTE: This argument is optional. If you don\'t pass in this argument, default value is False', required=False)
parser.add_argument('--catalogfile', help='Name of the catalog file on the repository. If the catalog file name is Catalog.xml on the network share, you don\'t need to pass in this argument', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_job_queue_job_ids():
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobid_search=re.findall("JID_.+?'",data)
    if jobid_search == []:
        print("\n- WARNING, job queue empty, no current job IDs detected for iDRAC %s" % idrac_ip)
        sys.exit()
    jobstore=[]
    for i in jobid_search:
        i=i.strip("'")
        jobstore.append(i)
    print("\n- Current job IDs in the job queue for iDRAC %s:\n" % idrac_ip)
    for i in jobstore:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip,i), auth=(idrac_username, idrac_password), verify=False)
        data = req.json()
        print("-" * 80)
        print("Job ID: %s\nJob Type: %s\nJob Message: %s\n" % (i,data['Name'], data['Message']))

def get_FW_inventory():
    print("\n- WARNING, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    installed_devices=[]
    for i in data['Members']:
        for ii in i.items():
            if "Installed" in ii[1]:
                installed_devices.append(ii[1])
    for i in installed_devices:
        req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        updateable_status = data['Updateable']
        version = data['Version']
        device_name = data['Name']
        print("Device Name: %s, Firmware Version: %s, Updatable: %s" % (device_name, version, updateable_status))
    sys.exit()




def get_repo_based_update_list():
    try:
        os.remove("repo_update_list.xml")
    except:
        pass
    f=open("repo_based_update_list.xml","a")
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    headers = {'content-type': 'application/json'}
   
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n-PASS: POST command passed to get repo update list, status code 200 returned")
    else:
        print("\n-FAIL, POST command failed to get repo update list, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    print("\n- Repo Based Update List in XML format\n")
    print(data['PackageList'])
    f.writelines(data['PackageList'])
    f.close()
    print("\n- WARNING, get repo based update list data is also copied to file \"repo_based_update_list.xml\"")
    sys.exit()

def get_device_name_criticality_info():
    print("\n- Device Name and Criticality Details for Updatable Devices -\n")
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    headers = {'content-type': 'application/json'}
   
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    try:
        get_all_devices = re.findall("Criticality.+BaseLocation",data["PackageList"])
    except:
        print("- FAIL, regex was unable to parse the XML to get criticality data")
        sys.exit()
    for i in get_all_devices:
        get_critical_value = re.search("Criticality.+?/",i).group()
        if "1" in get_critical_value:
            critical_string_value = "Criticality = (1)Recommended"
        elif "2" in get_critical_value:
            critical_string_value = "Criticality = (2)Urgent"
        elif "3" in get_critical_value:
            critical_string_value = "Criticality = (3)Optional"
        else:
            critical_string_value = "Criticality = NA"
        try:
            get_display_name = re.search("DisplayName.+?/VALUE",i).group()
            get_display_name = re.sub("DisplayName\" TYPE=\"string\"><VALUE>","",get_display_name)
            get_display_name = re.sub("</VALUE","",get_display_name)
        except:
            print("- FAIL, regex was unable to parse the XML to get device name")
            sys.exit()
        get_display_name = "DeviceName = " + get_display_name
        print(get_display_name)
        print(critical_string_value)
        print("\n")
        
        
    
def install_from_repository():
    global current_jobstore_job_ids
    global repo_job_id
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobid_search=re.findall("JID_.+?'",data)
    current_jobstore_job_ids=[]
    for i in jobid_search:
        i=i.strip("'")
        current_jobstore_job_ids.append(i)
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.InstallFromRepository' % (idrac_ip)
    method = "InstallFromRepository"
    headers = {'content-type': 'application/json'}
    payload={}
    if args["applyupdate"]:
        payload["ApplyUpdate"] = args["applyupdate"]
    if args["rebootneeded"]:
        if args["rebootneeded"] == "true" or args["rebootneeded"] == "True":
            payload["RebootNeeded"] = True
        if args["rebootneeded"] == "false" or args["rebootneeded"] == "False":
            payload["RebootNeeded"] = False
    else:
        args["rebootneeded"] = ""   
    if args["catalogfile"]:
        payload["CatalogFile"] = args["catalogfile"]   
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
        if i[0] == "Password":
            print("Password : ********")
        else:
            print("%s: %s" % (i[0],i[1]))
    
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for method \"%s\", status code %s returned" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for method %s, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    repo_job_id = response.headers['Location'].split("/")[-1]
    print("- PASS, repository job ID %s successfully created" % repo_job_id)


def get_update_job_ids():
    global new_job_ids
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    headers = {'content-type': 'application/json'}
   
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        pass
    else:
        if data['error']['@Message.ExtendedInfo'][0]['Message'] == 'Firmware versions on server match catalog, applicable updates are not present in the repository.':
            print("\n- WARNING, %s" % data['error']['@Message.ExtendedInfo'][0]['Message'])
            sys.exit()
        else:
            print("\n-FAIL, POST command failed to get repo update list, status code is %s" % (response.status_code))
            data = response.json()
            print("\n-POST command failure results:\n %s" % data)
            sys.exit()
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobid_search=re.findall("JID_.+?'",data)
    if jobid_search == []:
        print("\n- WARNING, job queue empty, no current job IDs detected for iDRAC %s" % idrac_ip)
        sys.exit()
    jobstore=[]
    for i in jobid_search:
        i=i.strip("'")
        jobstore.append(i)
    new_job_ids = []
    for i in jobstore:
        for ii in current_jobstore_job_ids:
             if i == ii:
                     break
        else:
            new_job_ids.append(i)
    new_job_ids.remove(repo_job_id)
        

def loop_job_status(x):
    print_message_count = 1
    start_time=datetime.now()
    time.sleep(1)
    while True:
        count = 0
        while count != 5:
            try:
                req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), auth=(idrac_username, idrac_password), verify=False)
                break
            except requests.ConnectionError as error_message:
                print("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
                count+=1
                print("- WARNING, Script will wait 10 seconds and try to check job status again")
                time.sleep(10)
                continue
        if count == 5:
            print("- FAIL, unable to get job status after 5 attempts, script will exit")
            sys.exit()
        else:
            pass
        current_time=str((datetime.now()-start_time))[0:7]
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been reached, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "invalid" in data['Message'] or "unable" in data['Message'] or "Unable" in data['Message'] or "not" in data['Message'] or "cancel" in data['Message'] or "Cancel" in data['Message']:
            print("- FAIL: Job ID %s failed, detailed error message is: %s" % (x, data['Message']))
            break
        elif data['Message'] == "Job for this device is already present.":
            break
        elif "Package successfully downloaded" in data['Message'] and args["rebootneeded"] == "False":
            print("\n- WARNING, repository package successfully downloaded, \"RebootNeeded = False\" detected. Check the overall Job Queue for Scheduled Update Jobs using -q argument. Next server manual reboot, these scheduled update jobs will execute and also mark the Repository Update Job as Completed.\n")
            sys.exit()

        elif "Package successfully downloaded" in data['Message'] and print_message_count == 1:
            print("\n- WARNING, repository package successfully downloaded. If version changed detected for any device, update job ID will get created and execute for that device\n")
            time.sleep(5)
            print_message_count = 2
            
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % x)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n")
            if data['JobType'] == "RepositoryUpdate":
                if args["applyupdate"] == "False":
                    print("\n- WARNING, \"ApplyUpdate = False\" selected, execute script with -r agrument to view the repo update list which will report devices detected for firmware updates")
                    sys.exit()
                else:
                    print("\n- WARNING, repository update job marked completed. Script will now check to see if any update job(s) were created due to different firmware version change detected")
                    break
            else:
                break
        else:
            print("- WARNING, job ID %s not marked completed, current job information:\n" % (x))
            print("* Name: %s" % data['Name'])
            print("* Job Status: %s" % data['Message'])
            print("* Current job execution time: %s\n" % str(current_time)[0:7])
            time.sleep(15)

def check_schedule_update_job():
    count = 0
    for x in new_job_ids:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data['Message'] == "Task successfully scheduled.":
            count+=1
    if count >= 1 and args["rebootneeded"].title() == "True":
        print("\n- WARNING, scheduled update job ID detected, server rebooting to apply the update(s)")
        time.sleep(5)
    elif count >= 1 and args["rebootneeded"].title() == "False" or args["rebootneeded"] == "":
        print("\n- WARNING, scheduled update job ID detected but \"RebootNeeded\" = False or RebootNeeded argument not passed in. Scheduled update jobs will not be applied until next manual server reboot")
        print("\n- Current update jobs created for repo update -\n")
        for x in new_job_ids:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), auth=(idrac_username, idrac_password), verify=False)
            data = req.json()
            print("Job ID: %s, Job Name: %s, Job Message: %s" % (x,data['Name'],data['Message']))
        sys.exit()
    else:
        pass

        
   
           

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["q"]:
        get_job_queue_job_ids()
    elif args["r"]:
        get_repo_based_update_list()
    elif args["c"]:
        get_device_name_criticality_info()
    elif args["i"]:
        install_from_repository()
        loop_job_status(repo_job_id)
        get_update_job_ids()
        check_schedule_update_job()
        for i in new_job_ids:
            loop_job_status(i)
    else:
        print("\n- FAIL, either missing required parameter(s) or incorrect parameter value(s) passed in")
    
    
        
            
        
        

#
# InstallFromRepositoryREDFISH. Python script using Redfish API with OEM extension to either get firmware version for all devices, get repository update list or install firmware from a repository on a network share.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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
parser.add_argument('script_examples',action="store_true",help='InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate False --sharetype CIFS, this example to going to download the catalog file from the CIFS share repository but not install any updates. It\'s recommended now to execute the script with -r argument to verify the repo update list. InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate True --sharetype CIFS --rebootneeded True, this example is going to install updates from the CIFS share repository and apply them. If updates need a server reboot to apply, it will also reboot the server.')
parser.add_argument('-g', help='Get current supported devices for firmware updates and their current firmware version, pass in \"y\"', required=False)
parser.add_argument('-r', help='Get repository update list, pass in \"y\". Output will be returned in XML format. You must first execute install from repository but don\'t apply updates to get the repository update list', required=False)
parser.add_argument('-i', help='Install from repository, pass in \"y\"', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS.', required=False)
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

def script_examples():
    print("\n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo_old --username administrator --password password --applyupdate False --sharetype CIFS, this example to going to download the catalog file from the CIFS share repository but not install any updates. I would now execute the script with -r argument to verify the repo update list.\n\n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y --ipaddress 192.168.0.130 --sharename cifs_share_vm\R740xd_repo_old --username administrator --password password --applyupdate True --sharetype CIFS --rebootneeded True, this example is going to install update from the CIFS share repository and apply them. If updates need a server reboot to apply, it will also reboot the server\n")  


def get_FW_inventory():
    print("\n- WARNING, current devices detected with firmware version and updateable status -\n")
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    installed_devices=[]
    for i in data[u'Members']:
        for ii in i.items():
            if "Installed" in ii[1]:
                installed_devices.append(ii[1])
    for i in installed_devices:
        req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        updateable_status = data[u'Updateable']
        version = data[u'Version']
        device_name = data[u'Name']
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
    print(data[u'PackageList'])
    f.writelines(data[u'PackageList'])
    f.close()
    print("\n- WARNING, get repo based update list data is also copied to file \"repo_based_update_list.xml\"")
    sys.exit()
    
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
    print("- PASS, job ID %s successfully created" % repo_job_id)


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
        if data[u'error'][u'@Message.ExtendedInfo'][0][u'Message'] == u'Firmware versions on server match catalog, applicable updates are not present in the repository.':
            print("\n- WARNING, %s" % data[u'error'][u'@Message.ExtendedInfo'][0][u'Message'])
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
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), auth=(idrac_username, idrac_password), verify=False)
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
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or "invalid" in data[u'Message'] or "unable" in data[u'Message'] or "Unable" in data[u'Message'] or "not" in data[u'Message'] or "cancel" in data[u'Message'] or "Cancel" in data[u'Message']:
            print("- FAIL: Job ID %s failed, detailed error message is: %s" % (x, data[u'Message']))
            sys.exit()
        elif data[u'Message'] == "Job for this device is already present.":
            break
        
        elif "completed successfully" in data[u'Message']:
            print("\n- PASS, job ID %s successfully marked completed" % x)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n")
            if data['JobType'] == "RepositoryUpdate":
                if args["applyupdate"] == "False":
                    print("\n- WARNING, \"ApplyUpdate = False\" selected, execute script with -r argument to view the repo update list which will report devices detected for firmware updates")
                    sys.exit()
                else:
                    print("\n- WARNING, repository update job marked completed. Checking now to see if any update jobs were created due to different firmware versions detected")
                    break
            else:
                break
        else:
            print("- WARNING, Job ID %s not marked completed, current status: \"%s\", job polling time: \"%s\"" % (x, data[u'Message'], current_time))
            time.sleep(5)

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
        if data[u'Message'] == "Task successfully scheduled.":
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
            print("Job ID: %s, Job Name: %s, Job Message: %s" % (x,data[u'Name'],data[u'Message']))
        sys.exit()
    else:
        pass

        
   
           

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_FW_inventory()
    elif args["r"]:
        get_repo_based_update_list()
    elif args["i"]:
        install_from_repository()
        loop_job_status(repo_job_id)
        get_update_job_ids()
        check_schedule_update_job()
        for i in new_job_ids:
            loop_job_status(i)
    else:
        print("\n- FAIL, either missing required parameter(s) or incorrect parameter value(s) passed in")
    
    
        
            
        
        

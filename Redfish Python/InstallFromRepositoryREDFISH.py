#!/usr/bin/python3
#
# InstallFromRepositoryREDFISH. Python script using Redfish API with OEM extension to either get firmware version for all devices, get repository update list or install firmware from a repository on a network share.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 17.0
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

import argparse
import getpass
import json
import logging
import os
import platform
import re
import requests
import subprocess
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get firmware version for all devices, get repository update list or install firmware from a repository on a network share. Note: Order repository update performs the updates: Immediate updates first (examples: DIAGS, Driver Pack, excluding iDRAC), staged updates second which require a server reboot to apply (examples: BIOS, NIC, RAID) and iDRAC update last.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-firmware', help='Get current supported devices for firmware updates and their current firmware version.', action="store_true", dest="get_firmware", required=False)
parser.add_argument('--get-repo-list', help='Get repository update list. Output will be returned in XML format. You must first execute install from repository but don\'t apply updates to get the repository update list', dest="get_repo_list", action="store_true", required=False)
parser.add_argument('--install', help='Perform install from repository operation.', action="store_true", required=False)
parser.add_argument('--get-critical-info', help='Get device name and criticality information only from repository update list XML. You must first execute install from repository but don\'t apply updates to get the repository update list', action="store_true", dest="get_critical_info", required=False)
parser.add_argument('--get-jobqueue', help='Get current job ids in the job queue.', action="store_true", dest="get_jobqueue", required=False)
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS. NOTE: For HTTP/HTTPS, recommended to use either IIS or Apache.', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the auth username for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled', required=False)
parser.add_argument('--password', help='Pass in the auth username password for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--applyupdate', help='Pass in True if you want to apply the updates. Pass in False will not apply updates but you can get the repo update list now. NOTE: This argument is optional. If you don\'t pass in the argument, default value is True.', required=False)
parser.add_argument('--rebootneeded', help='Pass in True to reboot the server to apply updates which need a server reboot. False means the updates will get staged but not get applied until next manual server reboot. NOTE: This argument is optional. If you don\'t pass in this argument, default value is False', required=False)
parser.add_argument('--catalogfile', help='Name of the catalog file on the repository. If the catalog file name is Catalog.xml on the network share, you don\'t need to pass in this argument', required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-firmware, this example will get current firmware versions for devices installed.
    \n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-repo-list, this example will get repo update list details.
    \n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-critical-info, this example will get critical information from repo update list. 
    \n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --install --shareip 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate False --sharetype CIFS, this example to going to download the catalog file from the CIFS share repostiory but not install any updates. It\'s recommmended now to execute the script with --get-repo-list argument to verify the repo update list.
    \n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --install --shareip 192.168.0.130 --sharename cifs_share_vm\R740xd_repo --username administrator --password password --applyupdate True --sharetype CIFS --rebootneeded True, this example is going to install updates from the CIFS share repository and apply them. If updates need a server reboot to apply, it will also reboot the server.
    \n- InstallFromRepositoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --install --shareip downloads.dell.com --sharetype HTTPS --applyupdate True --rebootneeded True, this example shows using Dell HTTPS downloads repository which is recommended to use. This repository is updated with the latest firmware versions for all devices iDRAC supports for updates.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0) 

def get_job_queue_job_ids():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get job queue jobs, error: \n%s" % data)
        sys.exit(0)
    for i in data.items():
        pprint(i)

def get_FW_inventory():
    logging.info("\n- INFO, getting current firmware inventory for iDRAC %s -\n" % idrac_ip)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET request failed to get firmware inventory, error: \n%s" % data)
        sys.exit(0)
    installed_devices = []
    for i in data['Members']:
        pprint(i)
        print("\n")  

def get_repo_based_update_list():
    try:
        os.remove("repo_based_update_list.xml")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step to delete" % "repo_based_update_list.xml")
    open_file = open("repo_based_update_list.xml","w")
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed to get repo update list, status code 200 returned")
    else:
        logging.error("\n- FAIL, POST command failed to get repo update list, status code is %s" % (response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("\n- Repo Based Update List in XML format\n")
    logging.info(data['PackageList'])
    open_file.writelines(data['PackageList'])
    open_file.close()
    logging.info("\n- INFO, get repo based update list data is also copied to file \"repo_based_update_list.xml\"")
    sys.exit(0)

def get_device_name_criticality_info():
    logging.info("\n- Device Name and Criticality Details for Updatable Devices -\n")
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, POST command failed to get repo update list, status code is %s" % (response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    try:
        get_all_devices = re.findall("Criticality.+BaseLocation",data["PackageList"])
    except:
        logging.error("- FAIL, regex was unable to parse the XML to get criticality data")
        sys.exit(0)
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
            logging.error("- FAIL, regex was unable to parse the XML to get device name")
            sys.exit(0)
        get_display_name = "DeviceName = " + get_display_name
        print(get_display_name)
        print(critical_string_value)
        print("\n")
        
def install_from_repository():
    global current_jobstore_job_ids
    global repo_job_id
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = str(response.json())
    jobid_search = re.findall("JID_.+?'",data)
    current_jobstore_job_ids = []
    for i in jobid_search:
        i = i.strip("'")
        current_jobstore_job_ids.append(i)
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.InstallFromRepository' % (idrac_ip)
    method = "InstallFromRepository"
    payload = {}
    if args["applyupdate"]:
        payload["ApplyUpdate"] = args["applyupdate"]
    if args["rebootneeded"]:
        if args["rebootneeded"].lower() == "true":
            payload["RebootNeeded"] = True
        if args["rebootneeded"].lower() == "false":
            payload["RebootNeeded"] = False
    else:
        args["rebootneeded"] = ""   
    if args["catalogfile"]:
        payload["CatalogFile"] = args["catalogfile"]   
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"].upper()
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
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        logging.info("\n- PASS, POST command passed for method \"%s\", status code %s returned" % (method, response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed for method %s, status code is %s" % (method, response.status_code))
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    repo_job_id = response.headers['Location'].split("/")[-1]
    logging.info("- PASS, repository job ID %s successfully created" % repo_job_id)

def get_update_job_ids():
    global new_job_ids
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList' % (idrac_ip)
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        if data['error']['@Message.ExtendedInfo'][0]['Message'] == 'Firmware versions on server match catalog, applicable updates are not present in the repository.' or "not found" in data['error']['@Message.ExtendedInfo'][0]['Message']:
            logging.error("\n- INFO, %s" % data['error']['@Message.ExtendedInfo'][0]['Message'])
            sys.exit(0)
        else:
            logging.error("\n- FAIL, POST command failed to get repo update list, status code is %s" % (response.status_code))
            data = response.json()
            logging.error("\n- POST command failure results:\n %s" % data)
            sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = str(response.json())
    jobid_search = re.findall("JID_.+?'",data)
    if jobid_search == []:
        logging.warning("\n- WARNING, job queue empty, no current job IDs detected for iDRAC %s" % idrac_ip)
        sys.exit(0)
    jobstore = []
    for i in jobid_search:
        i = i.strip("'")
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
    start_time = datetime.now()
    time.sleep(1)
    while True:
        count = 0
        while count != 5:
            try:
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, auth=(idrac_username, idrac_password))
                break
            except requests.ConnectionError as error_message:
                logging.error("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
                count += 1
                logging.info("- INFO, Script will wait 10 seconds and try to check job status again")
                time.sleep(10)
                continue
        if count == 5:
            logging.error("- FAIL, unable to get job status after 5 attempts, script will exit")
            sys.exit(0)
        current_time = str((datetime.now()-start_time))[0:7]
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been reached, script stopped\n")
            sys.exit(0)
        elif "completed successfully" in data['Message']:
            logging.info("\n- INFO, job ID %s successfully marked completed" % x)
            logging.info("\n- Final detailed job results -\n")
            for i in data.items():
                pprint(i)
            print("\n")
            if data['JobType'] == "RepositoryUpdate":
                if args["applyupdate"] == "False":
                    logging.info("\n- INFO, \"ApplyUpdate = False\" selected, execute script with argument --get-repo-list to view the repo update list which will report devices detected for firmware updates")
                    sys.exit(0)   
                else:
                    if args["rebootneeded"] == "False" or not args["rebootneeded"]:
                        logging.info("\n- INFO, \"RebootNeeded = False\" detected or argument not passed in. Check the overall Job Queue for update jobs using --get-jobqueue argument. Next server manual reboot, any scheduled update job(s) will execute.\n")
                        sys.exit(0)
                    else:
                        logging.info("\n- INFO, repository update job marked completed. Script will now check to see if any update job(s) were created due to different firmware version change detected")
                        return
            else:
                break
        elif "fail" in data['Message'].lower() or "invalid" in data['Message'].lower() or "unable" in data['Message'].lower() or "not" in data['Message'].lower() or "cancel" in data['Message'].lower():
            logging.error("- FAIL: Job ID %s failed, detailed error message: %s" % (x, data['Message']))
            break
        elif data['Message'] == "Job for this device is already present.":
            break
        elif "Package successfully downloaded" in data['Message'] and args["rebootneeded"] == "False" or not args["rebootneeded"]:
            logging.info("\n- INFO, repository package successfully downloaded, \"RebootNeeded = False\" detected or argument not passed in. Check the overall Job Queue for update jobs using --get-jobqueue argument. Next server manual reboot, any scheduled update job(s) will execute.\n")
            logging.info("\n- INFO, if iDRAC update is detected, this update job will not get created and execute until all scheduled update jobs have been completed")
            sys.exit(0)
        elif "Package successfully downloaded" in data['Message'] and print_message_count == 1:
            logging.info("\n- INFO, repository package successfully downloaded. If version changed detected for any device, update job ID will get created and execute for that device\n")
            time.sleep(5)
            print_message_count = 2
        else:
            logging.info("- INFO, %s, %s execution time: %s" % (data['Message'].rstrip("."), x, str(current_time)[0:7]))
            if "idrac" in data['Name'].lower() or "idrac" in data['Message'].lower():
                time.sleep(1)
            else:
                time.sleep(15)

def check_schedule_update_job():
    count = 0
    for x in new_job_ids:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, auth=(idrac_username, idrac_password))
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            count += 1
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "invalid" in data['Message'] or "unable" in data['Message'] or "Unable" in data['Message'] or "not" in data['Message'] or "cancel" in data['Message'] or "Cancel" in data['Message'] or "already present" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: Job ID %s failed, detailed error message: %s" % (x, data['Message']))
    if count >= 1 and args["rebootneeded"].title() == "True":
        logging.info("\n- INFO, scheduled update job ID detected, server rebooting to apply the update(s)")
        time.sleep(5)
    elif count >= 1 and args["rebootneeded"].title() == "False" or not args["rebootneeded"]:
        logging.info("\n- INFO, scheduled update job ID detected but \"RebootNeeded\" = False or RebootNeeded argument not passed in. Check the overall Job Queue for Update Jobs using -q argument. Next server manual reboot, any scheduled update job(s) will execute.")
        time.sleep(15)
        if new_job_ids == []:
            logging.info("- INFO, no update job IDs detected, check iDRAC Lifecycle Logs for more details")
            sys.exit(0)
        logging.info("\n- Current update jobs created for repo update -\n")
        for x in new_job_ids:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, x), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            logging.info("Job ID: %s, Job Name: %s, Job Message: %s" % (x, data['Name'], data['Message']))
        sys.exit(0)
    
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- Argument -p not detected, pass in iDRAC user %s password: " % args["u"])
        if args["ssl"]:
            if args["ssl"].lower() == "true":
                verify_cert = True
            elif args["ssl"].lower() == "false":
                verify_cert = False
            else:
                verify_cert = False
        else:
            verify_cert = False
        check_supported_idrac_version()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get_firmware"]:
        get_FW_inventory()
    elif args["get_jobqueue"]:
        get_job_queue_job_ids()
    elif args["get_repo_list"]:
        get_repo_based_update_list()
    elif args["get_critical_info"]:
        get_device_name_criticality_info()
    elif args["install"] and args["shareip"] and args["sharetype"]:
        install_from_repository()
        logging.info("- INFO, script will now loop checking the repo update job status")
        loop_job_status(repo_job_id)
        get_update_job_ids()
        check_schedule_update_job()
        for i in new_job_ids:
            loop_job_status(i)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

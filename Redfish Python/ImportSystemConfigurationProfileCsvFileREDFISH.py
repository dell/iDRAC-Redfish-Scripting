#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2024, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
#
# Edited CSV file examples leveraging 'iDRAC_details_SCP_import_example.csv' file from GitHub:
#
# Current iDRAC IP	Current iDRAC Root Password	New iDRAC Root Password	  New iDRAC Static IP	 New iDRAC Static Subnet  New iDRAC Static Gateway
# 192.168.0.120	        calvin				
# 192.168.0.130	        calvin
#
# In this example the script will NOT modify the SCP file first and only attempt to apply all configuration changes detected in the SCP file to each iDRAC listed in the CSV file.
#
#
# Current iDRAC IP	Current iDRAC Root Password	New iDRAC Root Password	  New iDRAC Static IP	 New iDRAC Static Subnet  New iDRAC Static Gateway
# 192.168.0.120	        calvin				Test1234#
# 192.168.0.130	        calvin                          Test6789!
#
# In this example the script will first modify the SCP file to set new value for root password, then apply all configuration changes detected in the SCP file to each iDRAC listed in the CSV file.
#
#
# Current iDRAC IP	Current iDRAC Root Password	New iDRAC Root Password	  New iDRAC Static IP	 New iDRAC Static Subnet  New iDRAC Static Gateway
# 192.168.0.120	        calvin				Test1234#                 192.168.0.10           255.255.255.0            192.168.0.254
# 192.168.0.130	        calvin                          Test6789!                 192.168.0.20           255.255.255.0            192.168.0.254
#
# In this example the script will first modify the SCP file to set new value for root password, set disable DHCP and set new values for static network settings, then apply all configuration changes detected in the SCP file to each iDRAC listed in the CSV file.
#
# Script pseudo code workflow:
#
# 1. Import SCP job will get created for each iDRAC detected in CSV file
# 2. Once all SCP import jobs are created script will sleep for 60 seconds. This sleep is needed due to iDRAC network settings changes getting applied (also all other iDRAC config changes detected will also get applied). 
# 3. If BIOS, storage or network changes are detected in the SCP file, server will now reboot to apply those changes. 
# 4. After 60 seconds script will now loop checking the job status for one import job. Once that job ID is marked completed it will loop checking the next job ID created and continue running this part of the code until all job IDs have been validated.
# 5. Final SCP import job results will also report all the configuration changes applied to each iDRAC.


import argparse
import csv
import getpass
import json
import logging
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to apply configuration changes using Server Configuration Profile (SCP) feature for multiple iDRACs using CSV file. CSV file can change only settings in SCP file, change root password and/or network settings from DHCP to static. NOTE: View comments in script to see CSV file examples for different workflow scenarios.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('-ip',help='Pass in iDRAC IP address. Note this argument is required and supported for export only', required=False)
parser.add_argument('-u', help='Pass in iDRAC username. Note this argument is required and supported for export only', required=False)
parser.add_argument('-p', help='Pass in iDRAC password. Note this argument is required and supported for export only', required=False)
parser.add_argument('--export', help='Create SCP file by exporting attributes in XML file format.', action="store_true", required=False)
parser.add_argument('--import', help='Import attribute changes using SCP file which must be in XML format. Note this script does not support JSON format.', action="store_true", required=False)
parser.add_argument('--target', help='Pass in target value to either export or import component attributes. You can pass in \"ALL" to set all component attributes or pass in a specific component to set only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=False)
parser.add_argument('--shutdown-type', help='Pass in server shutdown type value. Supported values are Graceful and Forced. If you don\'t use this optional argument default value is Graceful.', dest="shutdown_type", required=False)
parser.add_argument('--scp-filename', help='Pass in Server Configuration Profile filename for import', dest="scp_filename", required=False)
parser.add_argument('--csv-filename', help='Pass in CSV filename which contains iDRAC username, password and network details', dest="csv_filename", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ImportSystemConfigurationProfileCsvFileREDFISH.py --export --target idrac,bios -ip 192.168.0.120 -u root -p calvin, this example will generate SCP file containing only BIOS and iDRAC attributes.
    \n- ImportSystemConfigurationProfileCsvFileREDFISH.py --import --target ALL --scp-filename 2024-1-3_144317_export.xml --csv-filename iDRAC_details.csv, this example will first read the CSV file to get root password and network settings changes, modify the SCP file and then apply the configuration changes.""")
    sys.exit(0)

def get_server_generation():
    global idrac_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if "12" in data["Model"] or "13" in data["Model"]:
        idrac_version = 8
    elif "14" in data["Model"] or "15" in data["Model"] or "16" in data["Model"]:
        idrac_version = 9
    else:
        idrac_version = 10

def export_scp_file_locally():
    # Function to generate SCP file locally in the same directory you run the script from in XML format. 
    if idrac_version >= 10:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/OemManager.ExportSystemConfiguration' % idrac_ip
    else:    
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip  
    payload = {"ExportFormat":"XML","ShareParameters":{"Target":[args["target"]]}}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        logging.error("- FAIL, POST command failed to export system configuration, status code %s returned" % response.status_code)
        logging.error("- Error details: %s" % response.__dict__)
        sys.exit(0) 
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("\n- Job ID \"%s\" successfully created for ExportSystemConfiguration method\n" % job_id)
    start_time = datetime.now()
    while True:
        current_time = (datetime.now()-start_time)
        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
        dict_output = response.__dict__
        if "<SystemConfiguration Model" in str(dict_output):
            logging.info("\n- INFO, SCP export job ID %s successfully completed\n" % job_id)
            regex_search = re.search("<SystemConfiguration.+</SystemConfiguration>",str(dict_output)).group()
            try:
                security_string = re.search('<Attribute Name="GUI.1#SecurityPolicyMessage">.+?>', regex_search).group()
            except:
                logging.debug("- FAIL, unable to locate attribute GUI.1#SecurityPolicyMessage")         
            #Below code is needed to parse the string to set up XML in pretty format
            replace_variable = regex_search.replace("\\n"," ")
            replace_variable = replace_variable.replace("<!--  ","<!--")
            replace_variable = replace_variable.replace(" -->","-->")
            del_attribute = '<Attribute Name="SerialRedirection.1#QuitKey">^\\\\</Attribute>'
            try:
                replace_variable = replace_variable.replace(del_attribute,"")
            except:
                logging.debug("- FAIL, replace operation failed")
            try:
                replace_variable = replace_variable.replace(security_string,"")
            except:
                logging.debug("- FAIL, replace operation failed")
            create_list = replace_variable.split("> ")
            export_xml = []
            for i in create_list:
                create_string = i+">"
                export_xml.append(create_string)
            export_xml[-1] = "</SystemConfiguration>"
            get_date_info = datetime.now()
            filename = "%s-%s-%s_%s%s%s_export.xml"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
            open_file = open(filename,"w")
            for i in export_xml:
                open_file.writelines("%s \n" % i)
            open_file.close()
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
            data = response.json()
            logging.info("- INFO, exported attributes saved to file: %s" % filename)
            return
        data = response.json()
        try:
            message_string = data["Messages"]
        except:
            logging.error("- FAIL, unable to locate message string in JSON output")
            sys.exit(0)
        current_time = (datetime.now()-start_time)
        if response.status_code == 202 or response.status_code == 200:
            time.sleep(1)
        else:
            logging.error("- ERROR:, GET job ID details failed, error code: %s" % response.status_code)
            logging.error(data)
            sys.exit(0)
        if str(current_time)[0:7] >= "0:10:00":
            logging.error("\n- FAIL, Timeout of 10 minutes has been reached before marking the job completed.")
            sys.exit(0)
        else:
            try:
                logging.info("- INFO, \"%s\", percent complete: %s" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                time.sleep(1)
            except:
                logging.info("- INFO, unable to print job status message, trying again")
                time.sleep(1)
            continue

def import_SCP_local_filename(idrac_dict_name, current_idrac_ip, current_idrac_password, new_idrac_password, new_idrac_static_ip, new_idrac_static_subnet, new_idrac_static_gateway):
    # Function to import SCP file for multiple iDRACs using CSV to get iDRAC details. 
    logging.info("\n- INFO, applying configuration changes for current iDRAC IP %s -" % current_idrac_ip) 
    try:
        open_file = open(args["scp_filename"],"r")
    except:
        logging.error("\n- FAIL, \"%s\" file doesn't exist" % args["scp_filename"])
        sys.exit(0)    
    if idrac_version >= 10:
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/OemManager.ImportSystemConfiguration' % current_idrac_ip
    else:    
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % current_idrac_ip
    # Code needed to modify the SCP file to one string to pass in for POST command
    modify_file = open_file.read()
    modify_file = re.sub(" \n ","",modify_file)
    modify_file = re.sub(" \n","",modify_file)
    file_string = re.sub("   ","",modify_file)
    open_file.close()
    if new_idrac_password != "":
        try:
            file_string = file_string.replace("<!-- <Attribute Name=\"Users.2#Password\">******</Attribute>-->","<Attribute Name=\"Users.2#Password\">%s</Attribute>" % new_idrac_password)
        except:
            logging.error("- FAIL, unable to locate attribute \"Users.2#Password\" in SCP file, script will not create SCP import job for this iDRAC")
            return
    if new_idrac_static_ip != "":
        file_string = file_string.replace("<Attribute Name=\"IPv4.1#DHCPEnable\">Enabled</Attribute>","<Attribute Name=\"IPv4.1#DHCPEnable\">Disabled</Attribute>")
        file_string = re.sub("<!-- <Attribute Name=\"IPv4Static.1#Address\">[\\w.]+</Attribute>-->","<Attribute Name=\"IPv4Static.1#Address\">%s</Attribute>" % new_idrac_static_ip, file_string)
        file_string = re.sub("<Attribute Name=\"IPv4Static.1#Netmask\">[\\w.]+</Attribute>","<Attribute Name=\"IPv4Static.1#Netmask\">%s</Attribute>" % new_idrac_static_subnet, file_string)
        file_string = re.sub("<Attribute Name=\"IPv4Static.1#Gateway\">[\\w.]+</Attribute>","<Attribute Name=\"IPv4Static.1#Gateway\">%s</Attribute>" % new_idrac_static_gateway, file_string)
    payload = {"ImportBuffer":"","ShareParameters":{"Target":[args["target"]]}}
    if args["shutdown_type"]:
        payload["ShutdownType"] = args["shutdown_type"].title()
    payload["ImportBuffer"] = file_string
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, current_idrac_password))
    if response.status_code != 202:
        logging.error("\n- FAIL, POST command failed for import system configuration, status code %s returned" % response.status_code)
        logging.error(response.json())
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("\n- PASS, %s job ID successfully created for ImportSystemConfiguration method" % (job_id))
    idrac_job_ids_dict[idrac_dict_name] = {"job_id":job_id, "current_idrac_ip":current_idrac_ip, "current_idrac_password":current_idrac_password, "new_idrac_password":new_idrac_password, "new_idrac_static_ip":new_idrac_static_ip, "new_idrac_static_subnet":new_idrac_static_subnet, "new_idrac_static_gateway":new_idrac_static_gateway}
    time.sleep(1)

def loop_job_id(job_id, idrac_ip, idrac_password):
    # Function to loop checking final job status for SCP import job ID. The function will loop and check the job status for each iDRAC job created.
    logging.info("- INFO, loop checking %s job ID until marked completed" % job_id)
    start_time = datetime.now()
    time.sleep(10)
    start_job_message = ""
    count = 1
    get_job_status_count = 1
    while True:
        current_time = (datetime.now()-start_time)
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: timeout of 2 hours has been hit for querying job status. Manually check the server to debug the issue, check iDRAC job queue and LC logs.\n")
            return
        if count == 10:
            logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
            sys.exit(0)
        if get_job_status_count == 10:
            logging.warning("- WARNING, retry count of 10 has been hit for retry job status GET request, script will exit")
            sys.exit(0)
        try:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.warning("- WARNING, requests command failed to GET job status, detailed error information: \n%s" % error_message)
            logging.info("- INFO, script will attempt to get job status again")
            time.sleep(10)
            count += 1
            continue
        data = response.json()
        try:
            current_job_message = data['Oem']['Dell']['Message']
        except:
            logging.info("- INFO, unable to get job ID message string from JSON output, retry")
            count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code == 202 or response.status_code == 200:
            time.sleep(1)
        else:
            logging.info("- INFO, GET command failed to get job ID details, error code: %s, retry" % response.status_code)
            count += 1
            time.sleep(5)
            continue
        if "Oem" not in data:
            logging.info("- INFO, unable to locate OEM data in JSON response, retry")
            get_job_status_count += 1
            time.sleep(5)
            continue
        elif "No reboot Server" in data['Oem']['Dell']['Message']:
            logging.info("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
            logging.info("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            return
        elif data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
            logging.info("\n- INFO, job ID %s status marked as \"%s\" for iDRAC IP %s" % (job_id, data['Oem']['Dell']['JobState'], idrac_ip))
            logging.info("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
            logging.debug("\n- %s completed in: %s\n" % (job_id, str(current_time)[0:7]))
            return
        elif data['Oem']['Dell']['JobState'] == "Completed":
            if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                logging.error("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
            elif "success" in data['Oem']['Dell']['Message'].lower():
                logging.info("- PASS, job ID %s successfully marked completed for iDRAC %s\n" % (job_id, idrac_ip))
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- PASS, job ID %s marked completed for iDRAC IP %s\n" % (job_id, idrac_ip))
                logging.info("- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    pprint(i)
                print("\n")
                return
            logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    pprint(i)
            logging.debug("\n- %s completed in: %s\n" % (job_id, str(current_time)[0:7]))
            return
        else:
            if start_job_message != current_job_message:
                logging.info("- INFO, \"%s\", percent complete: %s" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                start_job_message = current_job_message
                continue
            
if __name__ == "__main__":
    get_server_generation()
    if args["script_examples"]:
        script_examples()
    if args["target"] and args["export"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        idrac_password = args["p"]
        export_scp_file_locally()
    elif args["target"] and args["import"]:
        idrac_username = "root"
        idrac_job_ids_dict = {}
        file_path = args["csv_filename"]
        count = 1
        # Code to read CSV file 
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if row[0] == "Current iDRAC IP" or row[0] == "":
                    continue
                else:
                    current_idrac_ip = row[0]
                    current_idrac_password = row[1]
                    new_idrac_password = row[2]
                    new_idrac_static_ip = row[3]
                    new_idrac_static_subnet = row[4]
                    new_idrac_static_gateway = row[5]
                    idrac_dict_name = "idrac%s" % count
                    count += 1
                import_SCP_local_filename(idrac_dict_name, current_idrac_ip, current_idrac_password, new_idrac_password, new_idrac_static_ip, new_idrac_static_subnet, new_idrac_static_gateway)
        if new_idrac_password == "" and new_idrac_static_ip == "":
            logging.info("\n- INFO, script will now loop checking job status for each SCP import job ID created\n")
            for i in idrac_job_ids_dict.items():
                loop_job_id(i[1]["job_id"], i[1]["current_idrac_ip"], i[1]["current_idrac_password"])
        elif new_idrac_password != "" and new_idrac_static_ip == "":
            logging.info("\n- INFO, script will now loop checking job status for each SCP import job ID created using new root password\n")
            time.sleep(5)
            for i in idrac_job_ids_dict.items():
                loop_job_id(i[1]["job_id"], i[1]["current_idrac_ip"], i[1]["new_idrac_password"])
        elif new_idrac_password != "" and new_idrac_static_ip != "":
            if idrac_job_ids_dict == {}:
                sys.exit(0)
            else:
                logging.info("- INFO, script will wait for 60 seconds before validating job status using new iDRAC user password and/or network settings\n")
                time.sleep(60)
                for i in idrac_job_ids_dict.items():
                    loop_job_id(i[1]["job_id"], i[1]["new_idrac_static_ip"], i[1]["new_idrac_password"])
        else:
            logging.error("- FAIL, unable to determine which password or IP to use to query job status, please manually check the iDRAC job queue for final job status details")
            sys.exit(0)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2023, Dell, Inc.
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to allow the user to set custom default iDRAC settings using Server Configuration Profile (SCP) file and store them in iDRAC. These custom default settings can be applied at a later time as needed.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--create', help='Create server configuration profile (SCP) template containing current iDRAC settings.', action="store_true", required=False)
parser.add_argument('--set-custom', help='Set custom default iDRAC settings pass in SCP filename', dest="set_custom", required=False)
parser.add_argument('--download-custom', help='Download a copy of custom iDRAC settings already stored in iDRAC memory', action="store_true", dest="download_custom", required=False)
parser.add_argument('--reset-custom', help='Reset iDRAC to custom default settings stored in iDRAC memory', action="store_true", required=False)
parser.add_argument('--directory-path', help='Pass in directory path where you want the SCP file saved to. If you don\'t pass in this argument SCP file will be saved to the directory you are executing the script from.', dest="directory_path", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- IdracCustomDefaultsREDFISH.py -ip 192.168.0.120 -u root -p calvin --create, this example will create SCP file for current iDRAC settings.
    \n- IdracCustomDefaultsREDFISH.py -ip 192.168.0.120 -u root -p calvin --set-custom 2023-6-15_18611_export.xml, this example will set custom default iDRAC settings using SCP file.
    \n- IdracCustomDefaultsREDFISH.py -ip 192.168.0.120 -u root -p calvin --download-custom, this example will download a copy of custom default iDRAC settings stord in iDRAC memory.
    \n- IdracCustomDefaultsREDFISH.py -ip 192.168.0.120 -u root -p calvin --reset-custom, this example will reset iDRAC to custom default settings.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)



def create_scp_file():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    format_type = "XML"
    payload = {"ExportFormat":"XML", "IncludeInExport":"IncludePasswordHashValues", "ShareParameters":{"Target":"IDRAC"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
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
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        dict_output = response.__dict__
        if format_type == "XML":
            if "<SystemConfiguration Model" in str(dict_output):
                logging.info("\n- Export locally job ID %s successfully completed. Attributes exported:\n" % job_id)
                regex_search = re.search("<SystemConfiguration.+</SystemConfiguration>",str(dict_output)).group()
                try:
                    security_string = re.search('<Attribute Name="GUI.1#SecurityPolicyMessage">.+?>', regex_search).group()
                except:
                    pass          
                #Below code is needed to parse the string to set up in pretty XML format
                replace_variable = regex_search.replace("\\n"," ")
                replace_variable = replace_variable.replace("<!--  ","<!--")
                replace_variable = replace_variable.replace(" -->","-->")
                del_attribute = '<Attribute Name="SerialRedirection.1#QuitKey">^\\\\</Attribute>'
                try:
                    replace_variable = replace_variable.replace(del_attribute,"")
                except:
                    pass
                try:
                    replace_variable = replace_variable.replace(security_string,"")
                except:
                    pass
                create_list = replace_variable.split("> ")
                export_xml = []
                for i in create_list:
                    create_string = i+">"
                    export_xml.append(create_string)
                export_xml[-1] = "</SystemConfiguration>"
                get_date_info = datetime.now()
                if args["directory_path"]:
                    filename = "%s\%s-%s-%s_%s%s%s_export.xml"% (args["directory_path"],get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                else:
                    filename = "%s-%s-%s_%s%s%s_export.xml"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                open_file = open(filename,"w")
                for i in export_xml:
                    open_file.writelines("%s \n" % i)
                open_file.close()
                for i in export_xml:
                    print(i)
                print("\n")
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
                data = response.json()
                print("\n- PASS, final detailed job status results for job ID %s -\n" % job_id)
                for i in data.items():
                    pprint(i)
                logging.info("\n- Exported attributes also saved in file: %s" % filename)
                sys.exit(0)
        elif format_type == "JSON":
            if "SystemConfiguration" in str(dict_output):
                data = response.json()
                json_format = json.dumps(data)
                get_date_info = datetime.now()
                if args["directory_path"]:
                    filename = "%s\%s-%s-%s_%s%s%s_export.json"% (args["directory_path"],get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                else:
                    filename = "%s-%s-%s_%s%s%s_export.json"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
                open_file = open(filename,"w")
                open_file.write(json.dumps(json.loads(json_format), indent=4))
                open_file.close()
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
                else:
                    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
                data = response.json()
                logging.info("\n- PASS, final detailed job status results for job ID %s -\n" % job_id)
                for i in data.items():
                    pprint(i)
                logging.info("\n- Exported attributes saved to file: %s" % filename)
                sys.exit(0)
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

def set_custom_defaults():
    try:
        open_file = open(args["set_custom"],"r")
    except:
        logging.error("\n- FAIL, \"%s\" file doesn't exist" % args["set_custom"])
        sys.exit(0)    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.SetCustomDefaults' % idrac_ip
    # Code needed to modify the SCP file to one string to pass in for POST command
    modify_file = open_file.read()
    modify_file = re.sub(" \n ","",modify_file)
    modify_file = re.sub(" \n","",modify_file)
    file_string = re.sub("   ","",modify_file)
    open_file.close()
    payload = {"CustomDefaults":file_string}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username, args["p"]))
    if response.status_code != 202:
        logging.error("\n- FAIL, POST command failed for import system configuration, status code %s returned" % response.status_code)
        logging.error(response.json())
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("\n- PASS, %s successfully created for DellManager.SetCustomDefaults method\n" % (job_id))
    start_job_message = ""
    start_time = datetime.now()
    count = 1
    get_job_status_count = 1
    while True:
        if count == 10:
            logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
            sys.exit(0)
        if get_job_status_count == 10:
            logging.warning("- WARNING, retry count of 10 has been hit for retry job status GET request, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, args["p"]))
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
        if data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
            logging.info("\n- INFO, job ID %s status marked as \"%s\"" % (job_id, data['Oem']['Dell']['JobState']))
            logging.info("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
            logging.info("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit(0)
        elif data['Oem']['Dell']['JobState'] == "Completed":
            if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                logging.error("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
            elif "success" in data['Oem']['Dell']['Message'].lower():
                logging.info("- PASS, job ID %s successfully marked completed\n" % job_id)
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- PASS, job ID %s marked completed\n" % job_id)
                logging.info("- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    pprint(i)
                sys.exit(0)
            logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    pprint(i)
            logging.info("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit(0)
        else:
            if start_job_message != current_job_message:
                logging.info("- INFO, \"%s\", percent complete: %s" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
                start_job_message = current_job_message
                continue

def download_custom_defaults():
    logging.info("\n- INFO, downloading custom defaults, this may take a few seconds to complete")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/CustomDefaultsDownloadURI' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/CustomDefaultsDownloadURI' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, command failed to download custom defaults stored in iDRAC, status code %s returned" % response.status_code)
        data = response.json()
        print(data)
        sys.exit(0)
    dict_output = response.__dict__
    regex_search = re.search("<SystemConfiguration.+</SystemConfiguration>",str(dict_output)).group()
    try:
        security_string = re.search('<Attribute Name="GUI.1#SecurityPolicyMessage">.+?>', regex_search).group()
    except:
        logging.debug("- INFO, unable to run regex check")         
    #Below code is needed to parse the string to set up in pretty XML format
    replace_variable = regex_search.replace("\\n"," ")
    replace_variable = replace_variable.replace("<!--  ","<!--")
    replace_variable = replace_variable.replace(" -->","-->")
    del_attribute = '<Attribute Name="SerialRedirection.1#QuitKey">^\\\\</Attribute>'
    try:
        replace_variable = replace_variable.replace(del_attribute,"")
    except:
        logging.debug("- INFO, unable to replace variable")
    try:
        replace_variable = replace_variable.replace(security_string,"")
    except:
        logging.debug("- INFO, unable to replace variable")
    create_list = replace_variable.split("> ")
    export_xml = []
    for i in create_list:
        create_string = i+">"
        export_xml.append(create_string)
    export_xml[-1] = "</SystemConfiguration>"
    get_date_info = datetime.now()
    filename = "%s-%s-%s_%s%s%s_custom_defaults.xml"% (get_date_info.year,get_date_info.month,get_date_info.day,get_date_info.hour,get_date_info.minute,get_date_info.second)
    open_file = open(filename,"w")
    for i in export_xml:
        open_file.writelines("%s \n" % i)
    open_file.close()
    logging.info("- INFO, custom default iDRAC settings filename \"%s\"" % filename)

def reset_to_custom():
    logging.info("\n- INFO, reset iDRAC to custom default settings, this may take a few seconds to complete")
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults' % idrac_ip
    payload = {"ResetType": "CustomDefaults"}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code != 200:
        logging.error("- FAIL, POST command failed to reset iDRAC to default custom settings, status code %s returned" % response.status_code)
        logging.error("- Error details: %s" % response.__dict__)
        sys.exit(0) 
    logging.info("- PASS, POST command passed to reset iDRAC to default custom settings. iDRAC will now reboot and be back up within a few minutes")

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
    if args["create"]:
        create_scp_file()
    elif args["set_custom"]:
        set_custom_defaults()
    elif args["download_custom"]:
        download_custom_defaults()
    elif args["reset_custom"]:
        reset_to_custom()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

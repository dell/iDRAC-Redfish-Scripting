#!/usr/bin/python3
#
# ExportServerConfigurationLocalREDFISH. Python script using Redfish API with OEM extension to export the system configuration locally. By default, POST command print all attributes to the screen. This script will also capture these attributes into a file.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
#
# Copyright (c) 2017, Dell, Inc.
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export the host server configuration profile locally in either XML or JSON format.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-target-values', help='Get supported values for --target argument', action="store_true", dest="get_target_values", required=False)
parser.add_argument('--target', help='Pass in Target value to get component attributes. You can pass in \"ALL" to get all component attributes or pass in specific component(s) to get only those attributes. If you pass in multiple values use a comma separator. To get all supported values, use argument --get-target-values', required=False)
parser.add_argument('--export-use', help='Pass in ExportUse value. Supported values are Default, Clone and Replace. If you don\'t use this parameter, default setting is Default or Normal export.', dest="export_use", required=False)
parser.add_argument('--include', help='Pass in IncludeInExport value. Supported values are 1 for \"Default\", 2 for \"IncludeReadOnly\", 3 for \"IncludePasswordHashValues\" 4 for \"IncludeReadOnly,IncludePasswordHashValues\" or 5 for \"IncludeCustomTelemetry\". If you don\'t use this parameter, default setting is Default for IncludeInExport.', required=False)
parser.add_argument('--format-type', help='Pass in Export format type, either \"XML\" or \"JSON\". Note, If you don\'t pass in this argument, default setting is XML', dest="format_type", required=False)
parser.add_argument('--directory-path', help='Pass in directory path where you want the SCP file saved to. If you don\'t pass in this argument, SCP file will be saved to the directory you are executing the script from.', dest="directory_path", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- ExportSystemConfigurationLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --target ALL, this example will export all components locally in XML format.
    \n- ExportSystemConfigurationLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-target-values, this example will return supported values to pass in for --target argument.
    \n- ExportSystemConfigurationLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --target BIOS --format-type JSON, this example will export only BIOS attributes in JSON format.
    \n- ExportSystemConfigurationLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --target IDRAC,BIOS --format-type JSON --include 2, this example will only export iDRAC, BIOS attributes and also read only attributes for these components in JSON format.""")
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

def get_target_values():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to get supported target values, status code %s returned" % response.status_code)
        print(data)
        sys.exit(0)
    logging.info("\n- INFO, supported values for --target argument\n")
    for i in data["Actions"]["Oem"]["#OemManager.v1_4_0.OemManager#OemManager.ExportSystemConfiguration"]["ShareParameters"]["Target@Redfish.AllowableValues"]:
        print(i)

def export_scp_file_locally():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    if not args["format_type"]:
        args["format_type"]="XML"    
    payload = {"ExportFormat":args["format_type"].upper(),"ShareParameters":{"Target":args["target"]}}
    if args["export_use"]:
        payload["ExportUse"] = args["export_use"]
    if args["include"]:
        if args["include"] == "1":
            payload["IncludeInExport"] = "Default"
        if args["include"] == "2":
            payload["IncludeInExport"] = "IncludeReadOnly"
        if args["include"] == "3":
            payload["IncludeInExport"] = "IncludePasswordHashValues"
        if args["include"] == "4":
            payload["IncludeInExport"] = "IncludeReadOnly,IncludePasswordHashValues"
        if args["include"] == "5":
            payload["IncludeInExport"] = "IncludeCustomTelemetry"
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
        if args["format_type"] == "XML":
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
        elif args["format_type"] == "JSON":
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
    if args["get_target_values"]:
        get_target_values()
    elif args["target"]:
        export_scp_file_locally()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

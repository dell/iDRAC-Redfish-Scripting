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
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform iDRAC quick alert configuration, same behavior as iDRAC GUI quick alert configuration page. NOTE: This script only supports quick configuration which applies bulk alert updates, not supported is setting an individual alert type for a specific category (example: only configure Health category Amperage alert for Redfish).")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--category', help='Select the categories you want to receive alerts on. Supported possible values: health, storage, configuration, audit, updates or all. Note: If passing in multiple values use a comma separator.', required=False)
parser.add_argument('--severity', help='Select the issue severity that you want to receive notification on. Supported possible values: critical, warning, informational or all. Note: If passing in multiple values use a comma separator.', required=False)
parser.add_argument('--receive', help='Select where you want to receive the notifications. Supported possible values: email, snmp, ipmi, syslog, wsevent, oslog, redfish or all. Note: If passing in multiple values use a comma separator.', required=False)
parser.add_argument('--setting', help='Select to enable or disable alerts for an alert category. Supported possible values: enabled, disabled', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- QuickAlertConfigurationREDFISH.py -ip 192.168.0.120 -u root -p calvin --category updates --severity critical --receive syslog --setting Enabled, this example will enable all critical alerts for updates category sent to syslog location.
    \n- QuickAlertConfigurationREDFISH.py -ip 192.168.0.120 -u root -p calvin --category updates,health --severity informational,warning --receive email,redfish --setting Enabled, this example will enable all critical, informational alerts for updates, health categories sent to email, redfish locations.
    \n- QuickAlertConfigurationREDFISH.py -ip 192.168.0.120 -u root -p calvin --category configuration --severity all --receive oslog --setting Enabled, this example will enable all informational, warning and critical alerts for configuration category sent to oslog location.
    \n- QuickAlertConfigurationREDFISH.py -ip 192.168.0.120 -u root -p calvin --category all --severity all --receive all --setting Enabled, this example will enable all informational, warning and critical alerts for health, storage, configuration, audit and updates categories sent to email, snmp, ipmi, syslog, wsevent, oslog and redfish locations.
    \n- QuickAlertConfigurationREDFISH.py -ip 192.168.0.120 -u root -p calvin --category configuration --severity warning --receive syslog --setting Disabled, this example will disable all warning alerts for configuration category sent to syslog location.""")
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

def enable_global_alert_setting():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"IPMILan.1.AlertEnable":"Enabled"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.debug("- PASS, PATCH command passed to successfully set IPMI alert enable attribute")
        if "error" in data.keys():
            logging.warning("- WARNING, error detected for one or more of the attribute(s) being set, detailed error results:\n\n %s" % data["error"])
            logging.info("\n- INFO, for attributes that detected no error, these will still get applied")
    else:
        logging.error("\n- FAIL, PATCH command failed to set IPMI alert enable attribute, status code %s returned" % response.status_code)
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)

def generate_import_buffer_string_for_SCP_import(alert_target):
    global import_buffer_string
    logging.info("\n- INFO, applying quick alert settings for \"%s\", this may take up to 30 seconds to complete depending on the number of alerts being configured" % alert_target)
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    payload = {"ExportFormat":"XML","ShareParameters":{"Target":alert_target}}
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
    logging.debug("\n- Job ID \"%s\" successfully created for ExportSystemConfiguration method\n" % job_id)
    start_time = datetime.now()
    while True:
        current_time = (datetime.now()-start_time)
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        dict_output = response.__dict__
        if "<SystemConfiguration Model" in str(dict_output):
            import_buffer_string = dict_output["_content"].decode("utf-8") 
            if "," in args["severity"]:
                severity_list = args["severity"].split(",")
            elif "all" in args["severity"].lower():
                severity_list = ["informational", "warning", "critical"]    
            else:
                severity_list = [args["severity"]]
            if "all" in args["receive"].lower():
                args["receive"] = "email, snmp, ipmi, syslog, wsevent, oslog, redfish"
            for i in severity_list:
                if i == "informational".lower():
                    severity_index = "3"
                elif i == "warning".lower():
                    severity_index = "2"
                elif i == "critical".lower():
                    severity_index = "1"
                else:
                    logging.error("\n- WARNING, invalid value passed in for argument --severity")
                    sys.exit(0)
                if args["setting"].lower() == "enabled":
                    old_setting_value = "Disabled"
                    new_setting_value = "Enabled"
                elif args["setting"].lower() == "disabled":
                    old_setting_value = "Enabled"
                    new_setting_value = "Disabled"
                else:
                    logging.warning("- WARNING, invalid value passed in for argument --setting")
                    sys.exit(0)
                if "email" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#Email\">%s" % (severity_index, old_setting_value),"%s#Alert#Email\">%s" % (severity_index, new_setting_value))
                if "snmp" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#SNMP\">%s" % (severity_index, old_setting_value),"%s#Alert#SNMP\">%s" % (severity_index, new_setting_value))
                if "ipmi" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#IPMI\">%s" % (severity_index, old_setting_value),"%s#Alert#IPMI\">%s" % (severity_index, new_setting_value))
                if "syslog" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#SysLog\">%s" % (severity_index, old_setting_value),"%s#Alert#SysLog\">%s" % (severity_index, new_setting_value))
                if "wsevent" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#WSEventing\">%s" % (severity_index, old_setting_value),"%s#Alert#WSEventing\">%s" % (severity_index, new_setting_value))
                if "oslog" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#OSLog\">%s" % (severity_index, old_setting_value),"%s#Alert#OSLog\">%s" % (severity_index, new_setting_value))
                if "redfish" in args["receive"].lower():
                    import_buffer_string = import_buffer_string.replace("%s#Alert#RedfishEventing\">%s" % (severity_index, old_setting_value),"%s#Alert#RedfishEventing\">%s" % (severity_index, new_setting_value))
            delete_jobID(job_id)
            time.sleep(5)
            break
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
            continue

def delete_jobID(job_id_string):
    url = "https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % idrac_ip
    payload = {"JobID":job_id_string}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.debug("\n- PASS: DeleteJobQueue action passed to clear job ID, status code 200 returned")
    else:
        logging.error("\n- FAIL, DeleteJobQueue action failed, status code %s returned" % (response.status_code))
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    
def scp_import_local():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    #payload = {"ShareParameters":{"Target":"ALL"},"ImportBuffer":scp_file_string}
    payload = {"ShareParameters":{"Target":"ALL"},"ImportBuffer":import_buffer_string}
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
    logging.debug("\n- PASS, %s successfully created for ImportSystemConfiguration method\n" % (job_id))
    start_job_message = ""
    start_time = datetime.now()
    count = 1
    get_job_status_count = 1
    new_password_set = "no"
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
        if data['Oem']['Dell']['JobState'] == "Failed":
            logging.error("\n- FAIL, quick alert configuration failed to apply, check iDRAC LC logs for more details")
            delete_jobID(job_id)
            break
        elif data['Oem']['Dell']['JobState'] == "Completed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
            if "success" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- PASS, quick alert settings successfully applied")
                delete_jobID(job_id)
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- INFO, no quick alert changes applied, either current configuration matched or severity/receive not supported for the category.")
                delete_jobID(job_id)
            break
        else:
            if start_job_message != current_job_message:
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
            args["p"] = idrac_password
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
    if args["category"] and args["severity"] and args["receive"] and args["setting"]:
        enable_global_alert_setting()
        generate_target_fqdd_list = []
        if "health" in args["category"]:
            generate_target_fqdd_list.append("EventFilters.SystemHealth.1")
        if "storage" in args["category"]:
            generate_target_fqdd_list.append("EventFilters.Storage.1")
        if "configuration" in args["category"]:
            generate_target_fqdd_list.append("EventFilters.Configuration.1")
        if "audit" in args["category"]:
            generate_target_fqdd_list.append("EventFilters.Audit.1")
        if "updates" in args["category"]:
            generate_target_fqdd_list.append("EventFilters.Updates.1")
        if "all" in args["category"]:
            generate_target_fqdd_list = ["EventFilters.SystemHealth.1", "EventFilters.Storage.1", "EventFilters.Configuration.1", "EventFilters.Audit.1", "EventFilters.Updates.1"]
        for i in generate_target_fqdd_list:
            generate_import_buffer_string_for_SCP_import(i)
            scp_import_local()
            time.sleep(5)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)

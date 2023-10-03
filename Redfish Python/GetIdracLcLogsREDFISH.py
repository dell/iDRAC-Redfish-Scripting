#!/usr/bin/python3
#
# GetIdracLcLogsREDFISH. Python script using Redfish API to get iDRAC LC logs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 12.0
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
import re
import requests
import shutil
import sys
import time
import warnings

from pprint import pprint
from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to get iDRAC Lifecycle Controller(LC) logs, see script help for different options when collecting LC log entries.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-all', help='Get all iDRAC LC logs', action="store_true", dest="get_all", required=False)
parser.add_argument('--get-severity', help='Get only specific severity entries from LC logs. Supported values: informational, warning or critical', dest="get_severity", required=False)
parser.add_argument('--get-category', help='Get only specific category entries from LC logs. Supported values: audit, configuration, updates, systemhealth or storage', dest="get_category", required=False)
parser.add_argument('--get-date-range', help='Get only specific entries within a given date range from LC logs. You must also use arguments --start-date and --end-date to create the filter date range', dest="get_date_range", action="store_true", required=False)
parser.add_argument('--start-date', help='Pass in the start date for the date range of LC log entries. Value must be in this format: YYYY-MM-DDTHH:MM:SS-offset (example: 2023-03-14T10:10:10-05:00). Note: If needed run --get-all argument to dump all LC logs, look at Created property to get your date time format.', dest="start_date", required=False)
parser.add_argument('--end-date', help='Pass in the end date for the date range of LC log entries. Value must be in this format: YYYY-MM-DDTHH:MM:SS-offset (example: 2023-03-15T14:55:10-05:00)', dest="end_date", required=False)
parser.add_argument('--get-fail', help='Get only failed entries from LC logs (searches for keywords unable, error, fault or fail',  action="store_true", dest="get_fail", required=False)
parser.add_argument('--get-message-id', help='Get only entries for a specific message ID. To get the correct message ID string format to pass in use argument --get-all to return complete LC logs. Examples of correct message string ID value to pass in: IDRAC.2.9.PDR1001, IDRAC.2.9.LC011. Note: You can also pass in an abbreviated message ID value, example: IDRAC.2.9.LC which will return any message ID that starts with LC.', dest="get_message_id", required=False)
parser.add_argument('--dump-to-json-file', help='Pass in this argument to dump LC log entries to JSON file(s) which you can then parse the JSON output. Note: Multiple JSON files may be created due to the LC logs file size since Redfish can only report 50 entries at a time.', dest="dump_to_json_file", action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all, this example will get complete iDRAC LC logs.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-fail, this example will only return LC log events where the message string contains keywords unable, error, fault or fail.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-message-id IDRAC.2.9.PDR1001, this example will get only entries with message ID 'IDRAC.2.9.PDR1001'.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-severity critical, this example will return only critical entries detected.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-severity warning, this example will return only warning entries detected and also redirect output in JSON format to a directory folder created by the script.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-category systemhealth, this example will return only system health category entries detected.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-date-range --start-date 2023-03-15T14:55:10-05:00 --end-date 2023-03-15T14:57:07-05:00, this example will return only LC Log entries within this start and date range.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_iDRAC_version():
    global iDRAC_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        return
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if int(data["FirmwareVersion"].replace(".","")) >= 6000000:
        iDRAC_version = "new"
    else:
        iDRAC_version = "old"

def get_specific_severity_logs():
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size")
    if args["get_severity"].lower() == "informational":
        filter_uri = "redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$filter=Severity eq 'OK'"
    elif args["get_severity"].lower() == "critical":
        filter_uri = "redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$filter=Severity eq 'Critical'"
    elif args["get_severity"].lower() == "warning":
        filter_uri = "redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$filter=Severity eq 'Warning'"
    else:
        logging.error("\n- WARNING, invalid value passed in for argument --get-severity")
        sys.exit(0)
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, filter_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, filter_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    lc_logs_list = []
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    elif "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    elif data["Members"] == []:
        logging.info("\n- WARNING, no \"%s\" severity entries detected in iDRAC LC logs" % args["get_severity"])
        sys.exit(0)
    else:
        lc_logs_list.append(data)
        if args["dump_to_json_file"]:
            filename = directory_name + "/lclog_entries_1.json"
            open_file = open(filename,"w")
            json.dump(data, open_file)
            open_file.close()
            file_count = 2
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.debug("-WARNING, 'Members' key not detected in JSON response, script will exit loop for skip query")
                break
            if response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            lc_logs_list.append(data)
            if args["dump_to_json_file"]:
                filename = directory_name + "/lclog_entries_%s.json" % file_count
                open_file = open(filename, "w")
                json.dump(data, open_file)
                open_file.close()
                file_count += 1
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)

def get_date_range():
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size")
    date_range_uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries?$filter=Created ge '%s' and Created le '%s'" % (args["start_date"], args["end_date"])
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, date_range_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    lc_logs_list = []
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    elif "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    elif data["Members"] == []:
        logging.info("- WARNING, no iDRAC LC logs detected within the date range specified")
        sys.exit(0)
    else:
        lc_logs_list.append(data)
        if args["dump_to_json_file"]:
            filename = directory_name + "/lclog_entries_1.json"
            open_file = open(filename,"w")
            json.dump(data, open_file)
            open_file.close()
            file_count = 2
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.debug("- WARNING, 'Members' key not detected in JSON response, script will exit skip query loop.")
                break
            elif response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            lc_logs_list.append(data)
            if args["dump_to_json_file"]:
                filename = directory_name + "/lclog_entries_%s.json" % file_count
                open_file = open(filename, "w")
                json.dump(data, open_file)
                open_file.close()
                file_count += 1
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)

        
def get_LC_logs():
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size")
    uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries"
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    lc_logs_list = []
    data = response.json()
    if "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    elif response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    elif data["Members"] == []:
        logging.info("\n- WARNING, 'Members' collection is empty, no LC logs detected, script will exit")
        sys.exit(0)
    else:
        lc_logs_list.append(data)
        if args["dump_to_json_file"]:
            filename = directory_name + "/lclog_entries_1.json"
            open_file = open(filename,"w")
            json.dump(data, open_file)
            open_file.close()
            file_count = 2
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.debug("- WARNING, 'Members' key not detected in JSON response, script will exit looping skip query")
                break
            elif response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            lc_logs_list.append(data)
            if args["dump_to_json_file"]:
                filename = directory_name + "/lclog_entries_%s.json" % file_count
                open_file = open(filename, "w")
                json.dump(data, open_file)
                open_file.close()
                file_count += 1
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)      

def get_LC_log_failures():
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size\n")
    uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries"
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    lc_logs_list = []
    if "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    for i in data['Members']:
        if "unable" in i["Message"].lower() or "fail" in i["Message"].lower() or "error" in i["Message"].lower() or "fault" in i["Message"].lower():
            lc_logs_list.append(i)
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.debug("- WARNING, 'Members' key not detected in JSON response, script will exit loop skip query")
                sys.exit(0)
            elif response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            for i in data['Members']:
                if "unable" in i["Message"].lower() or "fail" in i["Message"].lower() or "fail" in i["Message"].lower() or "error" in i["Message"].lower():
                    lc_logs_list.append(i)
    if lc_logs_list == []:
        logging.warning("\n- WARNING, no LC log events detected with keywords unable, fail or error in message string")
        sys.exit(0)
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        filename = directory_name + "/lclog_entries_1.json"
        open_file = open(filename,"w")
        json.dump(lc_logs_list, open_file)
        open_file.close()
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)      

def get_message_id():
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size\n")
    uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries?$filter=MessageId eq '%s'" % (args["get_message_id"])
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    lc_logs_list = []
    if "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    elif response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
    elif data["Members"] == []:
        logging.info("- WARNING, no iDRAC LC logs detected with message ID %s" % args["get_message_id"])
        sys.exit(0)
    else:
        lc_logs_list.append(data)
        if args["dump_to_json_file"]:
            filename = directory_name + "/lclog_entries_1.json"
            open_file = open(filename,"w")
            json.dump(data, open_file)
            open_file.close()
            file_count = 2
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.debug("- WARNING, 'Members' key not detected in JSON response, script will exit loop skip query")
                break
            elif response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            lc_logs_list.append(data)
            if args["dump_to_json_file"]:
                filename = directory_name + "/lclog_entries_%s.json" % file_count
                open_file = open(filename, "w")
                json.dump(data, open_file)
                open_file.close()
                file_count += 1
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)    

def get_category_entries():
    if args["get_category"].lower() not in ["audit", "configuration", "updates", "systemhealth", "storage"]:
        logging.info("\n- WARNING, invalid value entered for argument --get-category, see help text for supported values")
        sys.exit(0)
    if args["dump_to_json_file"]:
        try:
            shutil.rmtree("%s_LC_log_JSON_files" % idrac_ip)
        except:
            logging.debug("- INFO, directory does not exist, skipping")
        directory_name = "%s_LC_log_JSON_files" % idrac_ip
        directory_path = os.mkdir(directory_name)
    logging.info("\n- INFO, this may take 30 seconds to 1 minute to collect all iDRAC LC logs depending on log file size\n")
    uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries"
    if args["x"]:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    lc_logs_list = []
    if "Members" not in data.keys():
        logging.warning("- WARNING, 'Members' key not detected in JSON response, unable to get LC logs. Manually check iDRAC interfaces to confirm you can view LC logs")
        sys.exit(0)
    for i in data['Members']:
        if i["Oem"]["Dell"]["Category"].lower() == args["get_category"].lower():
            lc_logs_list.append(i)
    if "Members@odata.nextLink" in data.keys():
        skip_uri = data["Members@odata.nextLink"]
        number_list = [i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            skip_uri = re.sub("skip=.*","skip=%s" % seq, skip_uri)
            if args["x"]:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s%s' % (idrac_ip, skip_uri), verify=verify_cert, auth=(idrac_username, idrac_password))
            data = response.json()
            if "Members" not in data.keys():
                logging.warning("- WARNING, 'Members' key not detected in JSON response, script will exit loop skip query")
                break
            elif response.status_code == 500:
                break
            elif response.status_code != 200:
                if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                    break
                else:
                    logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                    sys.exit(0)
            elif "Members" in data.keys():
                if data["Members"] == []:
                    break
            for i in data['Members']:
                if i["Oem"]["Dell"]["Category"].lower() == args["get_category"].lower():
                    lc_logs_list.append(i)
    if lc_logs_list == []:
        logging.warning("\n- WARNING, no LC log events detected for category %s" % args["get_category"])
        sys.exit(0)
    pprint(lc_logs_list)
    if args["dump_to_json_file"]:
        filename = directory_name + "/lclog_entries_1.json"
        open_file = open(filename,"w")
        json.dump(lc_logs_list, open_file)
        open_file.close()
        logging.info("\n- INFO, JSON dump log files copied to directory %s" % directory_name)
        

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip=args["ip"]
        idrac_username=args["u"]
        if args["p"]:
            idrac_password=args["p"]
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
        get_iDRAC_version()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get_fail"]:
        get_LC_log_failures()
    elif args["get_date_range"] and args["start_date"] and args["end_date"]:
        get_date_range()    
    elif args["get_severity"]:
        get_specific_severity_logs()
    elif args["get_all"]:
        get_LC_logs()
    elif args["get_message_id"]:
        get_message_id()
    elif args["get_category"]:
        get_category_entries()    
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

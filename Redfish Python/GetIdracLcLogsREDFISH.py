#!/usr/bin/python
#!/usr/bin/python3
#
# GetIdracLcLogsREDFISH. Python script using Redfish API to get iDRAC LC logs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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
import sys
import time
import warnings

from pprint import pprint
from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to get iDRAC Lifecycle Controller(LC) logs, either latest 50 entries, all entries or failed entries.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-all', help='Get all iDRAC LC logs', action="store_true", dest="get_all", required=False)
parser.add_argument('--get-fail', help='Get only failed entries from LC logs (searches for keywords unable, error and fail',  action="store_true", dest="get_fail", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-all, this example will get complete iDRAC LC logs.
    \n- GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-fail, this example will get only failed entries from LC logs.""")
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
        
def get_LC_logs():
    try:
        os.remove("lc_logs.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step to delete" % "lc_logs.txt")
    open_file = open("lc_logs.txt","w")
    current_timestamp = datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (current_timestamp.month, current_timestamp.day, current_timestamp.year, current_timestamp.hour, current_timestamp.minute, current_timestamp.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get iDRAC LC logs, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    for i in data['Members']:
        pprint(i), print("\n")
        for ii in i.items():
            lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
            open_file.writelines("%s\n" % lc_log_entry)
        open_file.writelines("\n")
    number_list = [i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code == 500:
            open_file.close()
            logging.info("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
            sys.exit(0)
        if response.status_code != 200:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                open_file.close()
                logging.info("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
                sys.exit(0)
            else:
                logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                sys.exit(0)
        if "Members" not in data or data["Members"] == [] or response.status_code == 400:
            break
        for i in data['Members']:
            pprint(i), print("\n")
            for ii in i.items():
                lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                open_file.writelines("%s\n" % lc_log_entry)
            open_file.writelines("\n")
    logging.info("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
    open_file.close()

def get_LC_log_failures():
    count = 0
    try:
        os.remove("lc_log_failures.txt")
    except:
        logging.info("- INFO, unable to locate file %s, skipping step to delete" % "lc_logs.txt")
    logging.info("\n- INFO, checking iDRAC LC logs for failed entries, this may take awhile to complete depending on log size -\n")
    time.sleep(2)
    open_file = open("lc_log_failures.txt","w")
    current_timestamp = datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (current_timestamp.month, current_timestamp.day, current_timestamp.year, current_timestamp.hour, current_timestamp.minute, current_timestamp.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            if ii[0] == "Message":
                if "unable" in ii[1].lower() or "fail" in ii[1].lower() or "fail" in ii[1].lower() or "error" in ii[1].lower():
                    count += 1
                    for ii in i.items():
                        pprint(ii)
                        lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                        open_file.writelines("%s\n" % lc_log_entry)
                    print("\n")
                    open_file.writelines("\n")
    number_list = [i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code == 500:
            open_file.close()
            logging.info("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
            sys.exit(0)
        if response.status_code != 200:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"] or "internal error" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                open_file.close()
                logging.info("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
                sys.exit(0)
            else:
                logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code, data))    
                sys.exit(0)
        if "Members" not in data or data["Members"] == [] or response.status_code == 400 or response.status_code == 500:
            break
        for i in data['Members']:
            for ii in i.items():
                if ii[0] == "Message":
                    if "unable" in ii[1].lower() or "fail" in ii[1].lower() or "fail" in ii[1].lower() or "error" in ii[1].lower():
                        count += 1
                        for ii in i.items():
                            lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                            pprint(ii)
                            open_file.writelines("%s\n" % lc_log_entry)
                        print("\n")
                        open_file.writelines("\n")
    if count == 0:
        logging.info("- INFO, no failed entries detected in LC logs")
        try:
            os.remove("lc_log_failures.txt")
        except:
            logging.info("- INFO, unable to locate file %s, skipping step to delete" % "lc_logs.txt")
        sys.exit(0)
    else:
        logging.info("\n- INFO, Lifecycle logs also captured in \"lc_log_failures.txt\" file")
        open_file.close()



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
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get_fail"]:
        get_LC_log_failures()
    elif args["get_all"]:
        get_LC_logs()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        



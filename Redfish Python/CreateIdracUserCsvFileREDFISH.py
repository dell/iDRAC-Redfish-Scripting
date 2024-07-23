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
# Edited CSV file example (make sure to name your column headers the same as listed in this example:
#
# iDRAC IP	        Root Password	New User ID     New Username   New Password    Privilege Level
# 192.168.0.120	        calvin1234      10		user10         test1234#       Operator
# 192.168.0.130	        calvin8888      11              user11         Test789!        Administrator
#

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

parser = argparse.ArgumentParser(description='Python script using Redfish API to create a new iDRAC user for multiple iDRACs leveraging a CSV file.')
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--csv-filename', help='Pass in name of csv file which contains all details for creating new iDRAC user, see script comments for CSV content example. For Privilege Level supported values are Administrator, Operator, ReadOnly or None', dest="csv_filename", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- CreateIdracUserCsvFileREDFISH..py -ip 192.168.0.120 -u root -p calvin --csv-filename create_idrac_users.csv, this example will create a new iDRAC user per iDRAC listed in the csv file""")
    sys.exit(0)

def create_idrac_user_password(idrac_ip, root_password, user_id, new_username, new_user_password, privilege_level):    
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, user_id)
    logging.info("\n- INFO creating new user \"%s\" for iDRAC %s" % (new_username, idrac_ip))
    payload = {"UserName":new_username, "Password":new_user_password, "RoleId":privilege_level, "Enabled":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=("root",root_password))
    if "error" in response.json().keys():
        logging.error("- FAIL, PATCH command failed, detailed error results: \n%s" % response.json()["error"])
        sys.exit(0)
    if response.status_code == 200:
        logging.info("\n- PASS, status code %s returned for PATCH command to create iDRAC user \"%s\"" % (response.status_code, new_username))
    else:
        logging.error("\n- FAIL, status code %s returned, password was not changed" % response.status_code)

        
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    elif args["csv_filename"]:
        idrac_details_dict = {}
        file_path = args["csv_filename"]
        count = 1
        # Get contents from CSV file 
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if "iDRAC IP" in row[0]:
                    continue
                else:
                    idrac_dict_name = "idrac%s" % count
                    idrac_details_dict[idrac_dict_name]= row
                    count += 1
        for i in idrac_details_dict.items():
            create_idrac_user_password(i[1][0], i[1][1], i[1][2], i[1][3], i[1][4], i[1][5])
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# IdracRecurringJobOemREDFISH. Python script using Redfish API with OEM to create recurring job for iDRAC or storage operation.
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2020, Dell, Inc.
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM to create recurring job for iDRAC or storage operation. Once the recurring job has executed and marked completed and 10 minutes have elapsed, the next recurring job will get automatically created and scheduled.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-idrac-time', help='Get current iDRAC date/time', action="store_true", dest="get_idrac_time", required=False)
parser.add_argument('--get-actions', help='Get supported actions for recurring job creation', action="store_true", dest="get_actions", required=False)
parser.add_argument('--get-controllers', help='Get server storage controller FQDDs', action="store_true", dest="get_controllers", required=False)
parser.add_argument('--get-recurring-jobs', help='Get current recurring job(s)', action="store_true", dest="get_recurring_jobs", required=False)
parser.add_argument('--delete-recurring-job', help='Delete recurring job, pass in recurring auto job ID URI. If needed, use argument --get-recurring-jobs to get this URI information', dest="delete_recurring_job", required=False)
parser.add_argument('--get-virtualdisks', help='Get current server storage controller virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', dest="get_virtualdisks", required=False)
parser.add_argument('--create', help='Create recurring job, pass in action type. Pass in 1 for \"ComputerSystem.Reset\", 2 for \"Manager.Reset\", 3 for \"Volume.CheckConsistency\", 4 for \"LogService.ClearLog\". Note: Only other required argument needed to create recurring job is argument -s', required=False)
parser.add_argument('--vd-fqdd', help='Pass in the virtual disk FQDD if you are creating a recurring job for storage check consistency', dest="vd_fqdd", required=False)
parser.add_argument('--starttime', help='Pass in the initial start time/date for the recurring job to execute. Format is in UTC time. Example: 2020-02-05T04:51:28-06:00.Note: If needed, use argument -t to get current iDRAC date/time which returns the value in UTC format.', required=False)
parser.add_argument('--max', help='Max occurrences, pass in an integer value, how many times you want this recurring job to be executed. Note: This argument is optional for create recurring job', required=False)
parser.add_argument('--enable-days-week', help='Enable days of the week you want the recurring job to execute. Supported values are: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday or Every. Every value means it will enable all days of the week. If you pass in multiple string values, make sure to use comma separator. Note: This argument is optional for recurring job', dest="enable_days_week", required=False)
parser.add_argument('--enable-days-month', help='Enable days of the month you want the recurring job to execute, pass in integer value 1 to 31. If you pass in multiple integer values, make sure to use comma separator. If you pass in a value of 0, this will enable all days of the month. Note: This argument is optional for recurring job', dest="enable_days_month", required=False)
parser.add_argument('--recurrence', help='Recurrence interval, distance until the next occurrence job type executes. Pass in an integer value. Example: I want the next recurring job to execute 90 days apart, pass in a value of 90. Note: This argument is optional for recurring job', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-actions, this example will get supported actions for creating recurring jobs.
    \n- IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-idrac-time, this example will get current iDRAC time which is helpful for scheduling reccurring jobs.
    \n- IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-recurring-jobs, this example will get current recurring auto job IDs and associated job ID(s).
    \n- IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete-recurring-job /redfish/v1/JobService/Jobs/Auto32d880d7, this example will delete auto recurring job ID.
    \n- IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin --create 1 --starttime 2020-02-14T14:48:00-06:00 --max 5 --enable-days-week Monday, this example will create recurring job rebooting the server for the next 5 Mondays at 14:48.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/JobService/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/JobService/Jobs' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- FAIL, status code %s detected, incorrect iDRAC credentials detected" % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- FAIL, GET request failed to validate JobService is supported, status code %s returned. Error:\n%s" % (response.status_code, data))
        sys.exit(0)

def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    payload={"GetRequest":True}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- Current iDRAC time -\n")
    else:
        logging.error("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        logging.error("\n- Failure results:\n %s" % data)
        sys.exit(0)
    for i in data.items():
        if i[0] !="@Message.ExtendedInfo":
            print("%s: %s" % (i[0], i[1]))

def get_storage_controllers():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Server controller(s) detected -\n")
    controller_list = []
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_virtual_disks():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["get_virtualdisks"]),verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        logging.warning("\n- WARNING, no volume(s) detected for %s" % args["get_virtualdisks"])
        sys.exit(0)
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    logging.info("\n- Volume(s) detected for %s controller -\n" % args["get_virtualdisks"])
    for ii in vd_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))

def get_recurring_jobs():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/JobService/Jobs' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/JobService/Jobs' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- FAIL, GET command failed to get JobService details, status code %s returned. Error:\n%s" % (response.status_code, data))
        sys.exit(0)
    recurring_jobs_list = []
    for i in data["Members"]:
        for ii in i.items():
            if "Auto" in ii[1]:
                recurring_jobs_list.append(ii[1])
    if recurring_jobs_list == []:
        logging.warning("\n- WARNING, no recurring jobs detected")
    else:
        count = 0
        for i in recurring_jobs_list:
            logging.info("\n- Recurring auto job URI \"%s\" -\n" % i)
            if args["x"]:
                response = requests.get('https://%s%s/Steps' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s%s/Steps' % (idrac_ip, i), verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            for i in data["Members"]:
                for ii in i.items():
                    logging.info("\n- Associated schedule job ID URI \"%s\" details -\n" % ii[1])
                    if args["x"]:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s%s' % (idrac_ip, ii[1]), verify=verify_cert,auth=(idrac_username, idrac_password))
                    data = response.json()
                    for iii in data.items():
                        pprint(iii)

def get_recurring_job_types():
    logging.info("\n- Supported actions for recurring job types -\n")
    job_types = {"ComputerSystem.Reset":"Perform server reboot", "Manager.Reset":"Perform iDRAC reboot", "Volume.CheckConsistency":"Check consistency on a RAID volume", "LogService.ClearLog":"Clear iDRAC system event logs"}
    for i in job_types.items():
        print("%s: %s" % (i[0],i[1]))

def delete_recurring_job():
    url = "https://%s%s" % (idrac_ip, args["delete_recurring_job"])
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        logging.info("\n- PASS, recurring URI \"%s\" successfully deleted" % args["delete_recurring_job"])
    else:
        data = response.json()
        logging.error("\n- FAIL, recurring URI not successfully deleted, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    
def create_recurring_job():
    url = "https://%s/redfish/v1/JobService/Jobs" % idrac_ip
    payload = {"Payload":{},"Schedule":{"InitialStartTime":args["starttime"]}}
    if args["create"] == "1":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    elif args["create"] == "2":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset"
    elif args["create"] == "3" and args["vd_fqdd"]:
        payload["Payload"]["TargetUri"] = "/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s/Actions/Volume.CheckConsistency" % (args["vd_fqdd"])
    elif args["create"] == "4":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Actions/LogService.ClearLog"
    else:
        logging.error("- FAIL, invalid value entered for --create argument")
        sys.exit(0)
    if args["max"]:
        payload["Schedule"]["MaxOccurrences"] = int(args["max"])
    if args["enable_days_week"]:
        if "," in args["enable_days_week"]:
            split_string = args["enable_days_week"].split(",")
            payload["Schedule"]["EnabledDaysOfWeek"] = split_string
        else:
            payload["Schedule"]["EnabledDaysOfWeek"] = [args["enable_days_week"]]
    if args["enable_days_month"]:
        if "," in args["enable_days_month"]:
            split_string = args["enable_days_month"].split(",")
            create_int_list = []
            for i in split_string:
                create_int_list.append(int(i))
            payload["Schedule"]["EnabledDaysOfMonth"] = create_int_list
        else:
            payload["Schedule"]["EnabledDaysOfMonth"] = ([int(args["enable_days_month"])])
    if args["recurrence"]:
        payload["Schedule"]["RecurrenceInterval"] = "P%sD" % args["recurrence"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))    
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS, POST command passed to create recurring job for URI \"%s\", status code %s returned" % (payload["Payload"]["TargetUri"], response.status_code))
    else:
        logging.error("\n- FAIL, POST command failed, status code %s returned\n" % response.status_code)
        print(response.json())
        sys.exit(0)

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    if args["get_recurring_jobs"]:
        get_recurring_jobs()
    elif args["get_actions"]:
        get_recurring_job_types()
    elif args["create"] and args["starttime"]:
        create_recurring_job()
    elif args["get_controllers"]:
        get_storage_controllers()
    elif args["get_virtualdisks"]:
        get_virtual_disks()
    elif args["get_idrac_time"]:
        get_idrac_time()
    elif args["get_recurring_jobs"]:
        get_recurring_jobs()
    elif args["delete_recurring_job"]:
        delete_recurring_job()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

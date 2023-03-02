#!/usr/bin/python3
#
# SupportAssistCollectionLocalREDFISH. Python script using Redfish API with OEM extension to perform Support Assist operations.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 16.0
#
# Copyright (c) 2020, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import argparse
import getpass
import json
import logging
import re
import requests
import sys
import time
import urllib.parse
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform Support Assist(SA) operations. These include export SA report locally, accept End User License Agreement(EULA) or register SA for iDRAC.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--export', help='Export support assist collection locally. You must also use agrument --data for export SA collection.', action="store_true", required=False)
parser.add_argument('--accept', help='Accept support assist end user license agreement (EULA)', action="store_true", required=False)
parser.add_argument('--get', help='Get support assist end user license agreement (EULA)', action="store_true", required=False)
parser.add_argument('--register', help='Register SupportAssist for iDRAC. NOTE: You must also pass in city, company name, country, email, first name, last name, phone number, street, state and zip arguments to register. NOTE: ISM must be installed and running on the operating system before you register SA.', action="store_true", required=False)
parser.add_argument('--city', help='Pass in city name to register Support Assist', required=False)
parser.add_argument('--companyname', help='Pass in company name to register Support Assist', required=False)
parser.add_argument('--country', help='Pass in country to register Support Assist', required=False)
parser.add_argument('--first-email', help='Pass in primary (first) email address to register Support Assist', dest="first_email", required=False)
parser.add_argument('--firstname', help='Pass in firstname to register Support Assist', required=False)
parser.add_argument('--lastname', help='Pass in lastname to register Support Assist', required=False)
parser.add_argument('--phonenumber', help='Pass in phone number to register Support Assist', required=False)
parser.add_argument('--second-firstname', help='Pass in firstname of the secondary contact to register Support Assist', dest="second_firstname", required=False)
parser.add_argument('--second-lastname', help='Pass in lastname of the secondary contact to register Support Assist', dest="second_lastname", required=False)
parser.add_argument('--second-phonenumber', help='Pass in phone number of the secondary contact to register Support Assist', dest="second_phonenumber", required=False)
parser.add_argument('--second-email', help='Pass in email address of the secondary contact to register Support Assist', dest="second_email", required=False)
parser.add_argument('--street', help='Pass in street name to register Support Assist', required=False)
parser.add_argument('--state', help='Pass in state to register Support Assist', required=False)
parser.add_argument('--zip', help='Pass in zipcode to register Support Assist', required=False)
parser.add_argument('--data', help='Pass in a value for the type of data you want to collect for Support Assist collection. Supported values are: pass in 0 for \"DebugLogs\", pass in 1 for "HWData\", pass in 2 for \"OSAppData\", pass in 3 for \"TTYLogs(storage logs)\", pass in 4 for \"TelemetryReports\". Note: If you do not pass in this argument, default settings will collect HWData. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values (Example: 0,3)', required=False)
parser.add_argument('--filter', help='Filter personal identification information (PII) for Support Assist collection. Supported values are: 0 for \"No\" and 1 for \"Yes\". NOTE: If you don\'t pass in this argument, no filtering is performed for the collection.', required=False)
parser.add_argument('--filename', help='Change default filename for SupportAssist collection file. Default filename: sacollect.zip. NOTE: If using this argument make sure to give the filename .zip extension', required=False, default='sacollect.zip')

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get SA EULA current status.
    \n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root --accept, this example will first prompt to enter iDRAC user password, then accept SA EULA.
    \n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -x bd48034369f6e5f7424e9aea88f94123 --export --data 0,3, this example using X-auth token session will export SA logs locally. The SA log will only include debug and TTY logs.
    \n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --register --city Austin --state Texas --zip 78665 --companyname Dell --country US --firstname test --lastname tester --phonenumber "512-123-4567" --first-email \"tester1@yahoo.com\" --second-email \"tester2@gmail.com\" --street \"1234 One Dell Way\", this example shows registering SupportAssist.
    \n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --export --data 1, this example will export SA collection locally which contains only hardware data. Once th job ID is marked completed, SA collection will be saved locally to default filename sacollect.zip.
    \n- SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin --accept --export --data 1 --filename R640_SA_collection.zip, this example will first attempt to accept EULA, then export SA collection and saved locally to a custom file named R640_SA_collection.zip""")
    sys.exit(0)

def check_supported_idrac_version():
    supported = ""
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        logging.error("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(0)
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "SupportAssistCollection" in i:
            supported = "yes"
    if supported == "no":
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def support_assist_collection():
    global job_id
    global start_time
    start_time = datetime.now()
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection' % (idrac_ip)
    method = "SupportAssistCollection"
    payload = {"ShareType":"Local"}
    if args["filter"]:
        if args["filter"] == "0":
            payload["Filter"] = "No"
        elif args["filter"] == "1":
            payload["Filter"] = "Yes"
    if args["data"]:
        data_selector_values=[]
        if "," in args["data"]:
            data_selector = [i for i in args["data"].split(",")]
            if "0" in data_selector:
                data_selector_values.append("DebugLogs")
            if "1" in data_selector:
                data_selector_values.append("HWData")
            if "2" in data_selector:
                data_selector_values.append("OSAppData")
            if "3" in data_selector:
                data_selector_values.append("TTYLogs")
            if "4" in data_selector:
                data_selector_values.append("TelemetryReports")
            payload["DataSelectorArrayIn"] = data_selector_values
        else:
            if args["data"] == "0":
                data_selector_values.append("DebugLogs")
            if args["data"] == "1":
                data_selector_values.append("HWData")
            if args["data"] == "2":
                data_selector_values.append("OSAppData")
            if args["data"] == "3":
                data_selector_values.append("TTYLogs")
            if args["data"] == "4":
                data_selector_values.append("TelemetryReports")
            payload["DataSelectorArrayIn"] = data_selector_values
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code != 202:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("\n- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))

def support_assist_accept_EULA():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistAcceptEULA' % (idrac_ip)
    method = "SupportAssistAcceptEULA"
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.debug("- PASS, POST command passed to accept EULA")
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit(0)
    logging.info("\n- PASS, %s method passed and End User License Agreement (EULA) has been accepted" % method)
    return

def support_assist_get_EULA_status():
    global accept_interface
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (idrac_ip)
    method = "SupportAssistGetEULAStatus"
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if args["accept"]:
        accept_interface = data["Interface"]
    else:
        logging.info("\n- Current Support Assist End User License Agreement Information -\n")
        for i in data.items():
            if not "ExtendedInfo" in i[0]:
                print("%s: %s" % (i[0],i[1]))
    

def support_assist_register():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"OS-BMC.1.AdminState":"Enabled"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    data = response.json()
    if statusCode != 200:
        logging.error("\n- FAIL, Command failed for action %s, status code is: %s\n" % (args["s"].upper(),statusCode))
        logging.error("Extended Info Message: {0}".format(response.json()))
        sys.exit(0)
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistRegister' % (idrac_ip)
    method = "SupportAssistRegister"
    payload = {"City": args["city"], "CompanyName": args["companyname"], "Country":args["country"], "PrimaryFirstName":args["firstname"],"PrimaryLastName":args["lastname"], "PrimaryPhoneNumber":args["phonenumber"], "State":args["state"], "Street1": args["street"],"Zip":args["zip"]}
    if args["first_email"]:
        payload["PrimaryEmail"] = args["first_email"]
    if args["second_email"]:
        payload["SecondaryEmail"] = args["second_email"]
    if args["second_firstname"]:
        payload["SecondaryFirstName"] = args["second_firstname"]
    if args["second_lastname"]:
        payload["SecondaryLastName"] = args["second_lastname"]
    if args["second_phonenumber"]:
        payload["SecondaryPhoneNumber"] = args["second_phonenumber"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS, SupportAssistRegister action passed, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, SupportAssistRegister action failed, status code %s returned. Detailed error results:\n" % response.status_code)
        data = response.__dict__
        print(data["_content"])
        sys.exit(0)
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (idrac_ip)
    method = "SupportAssistGetEULAStatus"
    payload = {}
    logging.info("- INFO, validating if Support Assist is registered for iDRAC")
    time.sleep(15)
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if data["IsRegistered"] == "Registered":
        logging.info("\n- PASS, Support Assist verified as registered")
    else:
        logging.error("\n- FAIL, Support Assist not registered, current status is: %s" % data["IsRegistered"])
        sys.exit(0)

def loop_job_status():
    loop_count = 0
    while True:
        if loop_count == 20:
            logging.info("- INFO, retry count for GET request has been elapsed, script will exit. Manually check the job queue for final job status results")
            sys.exit(0)
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
             response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        data = response.json()
        if response.status_code != 200:
            logging.error("- FAIL, status code %s returned, GET command will retry" % statusCode)
            time.sleep(10)
            loop_count += 1
            continue
        try:
            if response.headers['Location'] == "/redfish/v1/Dell/sacollect.zip" or response.headers['Location'] == "/redfish/v1/Oem/Dell/sacollect.zip":
                logging.info("- PASS, job ID %s successfully marked completed" % job_id)
                if args["x"]:
                    response = requests.get('https://%s%s' % (idrac_ip, response.headers['Location']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s%s' % (idrac_ip, response.headers['Location']), verify=verify_cert,auth=(idrac_username, idrac_password))
                if args["filename"]:
                    SA_export_filename = args["filename"]
                else:
                    SA_export_filename = "sacollect.zip"    
                with open(SA_export_filename, "wb") as output:
                    output.write(response.content)
                logging.info("\n- INFO, check your local directory for SupportAssist collection zip file \"%s\"" % SA_export_filename)
                sys.exit(0)
            else:
                data = response.json()
                logging.error("- ERROR, unable to locate SA collection URI in headers output, JSON response: \n%s" % data)
                sys.exit(0)
        except:
            if str(current_time)[0:7] >= "0:30:00":
                logging.error("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
                sys.exit(0)
            elif data['JobState'] == "CompletedWithErrors":
                logging.info("\n- INFO, SA collection completed with errors, please check iDRAC Lifecycle Logs for more details")
                sys.exit(0)
            elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "error" in data['Message'] or "Error" in data['Message']:
                logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                sys.exit(0)
            elif data['JobState'] == "Completed" or "complete" in data['Message'].lower():
                if "local path" in data['Message']:
                    logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
                else:
                    logging.warning("- WARNING, unable to detect final job status message. Manually run GET on URI \"%s\" using browser to see if SA zip collection is available to download." % response.headers['Location'])
                    sys.exit(0)
                for i in data.items():
                    pprint(i)
                break
            else:
                logging.info("- INFO, Job status not marked completed, polling job status again, execution time: %s" % str(current_time)[0:7])
                time.sleep(5)
            

    

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- INFO, argument -p not detected, pass in iDRAC user %s password: " % args["u"])
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
    if args["accept"]:
        support_assist_get_EULA_status()
        if accept_interface is None:
            support_assist_accept_EULA()
        else:
            logging.info("\n- WARNING, SupportAssist EULA has already been accepted")
        if not args["export"]:
            sys.exit(0)
    if args["export"] and args["data"]:
        support_assist_collection()
        loop_job_status()
        sys.exit(0)
    if args["get"]:
        support_assist_get_EULA_status()
        sys.exit(0)
    if args["register"] and args["city"] and args["companyname"] and args["country"] and args["firstname"] and args["lastname"] and args["phonenumber"] and args["state"] and args["street"] and args["zip"]:
        support_assist_register()
        sys.exit(0)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

    
    
        
            
        
        

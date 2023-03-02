#!/usr/bin/python3
#
# SupportAssistCollectionNetworkShareREDFISH. Python script using Redfish API with OEM extension to export Support Assist collection to a network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 11.0
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

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either export support assist (SA) collection to a network share or get/accept/register End User license agreement (EULA). NOTE: the SA file copied to your network share will be in ZIP format using your server service tag in the name. Example of SA report file name \"TSR20200122131132_M538C3S.zip\"")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--accept', help='Accept support assist end user license agreement (EULA)', action="store_true", required=False)
parser.add_argument('--get', help='Get support assist end user license agreement (EULA)', action="store_true", required=False)
parser.add_argument('--register', help='Register Support Assist for iDRAC. NOTE: You must also pass in city, company name, country, first name, first email, last name, phone number, street, state and zip arguments to register. NOTE: ISM must be installed and running on the operating system before you register SA.', action="store_true", required=False)
parser.add_argument('--export-network', help='Export Support Assist collection to network share. NOTE: Make sure you also use arguments ipaddress, sharetype, sharename and dataselectorarrayin for export to network share. If using CIFS, you need to also use username and password arguments.', dest="export_network", action="store_true", required=False)
parser.add_argument('--export-last', help='Export Support Assist last collection stored on iDRAC to network share. NOTE: Make sure you also use arguments --shareip, --sharetype and --sharename.', dest="export_last", action="store_true", required=False)
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
parser.add_argument('--shareip', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS, FTP, TFTP', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in network share username if auth is configured (this is required for CIFS, optional for HTTP and HTTPS)', required=False)
parser.add_argument('--password', help='Pass in network share username password if auth is configured (this is required for CIFS, optional for HTTP and HTTPS)', required=False)
parser.add_argument('--data', help='Pass in a value for the type of data you want to collect. Supported values are: pass in 0 for \"DebugLogs\", pass in 1 for "HWData\", pass in 2 for \"OSAppData\", pass in 3 for \"TTYLogs\", pass in 4 for \"TelemetryReports\". Note: If you do not pass in this argument, default settings will collect HWData. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values (Example: 0,3)', required=False)
parser.add_argument('--filter', help='Filter personal identification information (PII) for Support Assist collection. Supported values are: 0 for \"No\" and 1 for \"Yes\". NOTE: If you don\'t pass in this argument, no filtering is performed for the collection.', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get SA EULA current status.
    \n- SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --accept, this example will accept SA EULA.
    \n- SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --register --city Austin --state Texas --zip 78665 --companyname Dell --country US --firstname test --lastname tester --phonenumber "512-123-4567" --first-email \"tester1@yahoo.com\" --second-email \"tester2@gmail.com\" --street \"1234 One Dell Way\", this example shows registering SupportAssist.
    \n- SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --export-network --shareip 192.168.0.130 --sharetype HTTP --sharename http_share --data 3, this example wil export SA collection for storage TTYlogs only to HTTP share.
    \n- SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin --export-last --shareip 192.168.0.130 --sharetype HTTP --sharename http_share, this example will export last cached SupportAssist collection to network share.""")
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

def support_assist_get_EULA_status():
    logging.info("\n- Current Support Assist End User License Agreement Information -\n")
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

def export_support_assist_colection_network_share():
    global job_id
    if args["export_network"]:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection' % (idrac_ip)
        method = "SupportAssistCollection"
    elif args["export_last"]:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistExportLastCollection' % (idrac_ip)
        method = "SupportAssistExportLastCollection"  
    payload = {}
    if args["filter"]:
        if args["filter"] == "0":
            payload["Filter"] = "No"
        elif args["filter"] == "1":
            payload["Filter"] = "Yes"
    if args["shareip"]:
        payload["IPAddress"] = args["shareip"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
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
    data = response.json()
    if response.status_code != 202:
        logging.error("\n- FAIL, status code %s returned, POST command failure results:\n %s" % (response.status_code, data))
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit(0)
    logging.info("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))

def loop_job_status():
    start_time = datetime.now()
    count_number = 0
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        data = response.json()
        if str(current_time)[0:7] >= "1:00:00":
            logging.error("\n- FAIL: Timeout of 1 hour has been hit, script stopped\n")
            sys.exit(0)
        elif data['JobState'] == "CompletedWithErrors":
                logging.info("\n- INFO, SA collection completed with errors, please check iDRAC Lifecycle Logs for more details")
                sys.exit(0)
        elif "fail" in data['Message'].lower() or "error" in data['Message'].lower():
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit(0)
        elif data['JobState'] == "Completed":
            if data['Message'] == "The SupportAssist Collection and Transmission Operation is completed successfully.":
                logging.info("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                logging.error("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                    pprint(i)
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            service_tag = data['Oem']['Dell']['DellSystem']['NodeID']
            logging.info("\n- SA exported log file located on your network share should be in ZIP format with server service tag \"%s\" in the file name" % service_tag)
            break
        else:
            count_number_now = data['PercentComplete']
            if count_number_now > count_number:
                logging.info("- INFO, %s, percent complete: %s" % (data['Message'].strip("."), data['PercentComplete']))
                count_number = count_number_now
            else:
                continue
            
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
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
    if args["export_network"] or args["export_last"]:
        export_support_assist_colection_network_share()
        loop_job_status()
    elif args["accept"]:
        support_assist_accept_EULA()
    elif args["get"]:
        support_assist_get_EULA_status()
    elif args["register"] and args["city"] and args["companyname"] and args["country"] and args["email"] and args["firstname"] and args["lastname"] and args["phonenumber"] and args["state"] and args["street"] and args["zip"]:
        support_assist_register()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

#!/usr/bin/python3
#
# SubscriptionManagementREDFISH. Python script using Redfish API to either get event service properties, get event
# subscriptions, create / delete subscriptions or submit test event.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2022, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import json
import getpass
import logging
import os
import platform
import re
import requests
import sys
import time
import warnings

from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to either get event service properties, get event subscriptions, create / delete subscriptions or submit test event.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-event-properties', help='Get event service properties for EventService URI.', required=False, dest='get_event_properties', action="store_true")
parser.add_argument('--get-subscriptions', help='Get current subscription details', required=False, dest='get_subscriptions', action="store_true")
parser.add_argument('--create-subscription', action="store_true", help='Create a new subscription', required=False, dest='create_subscription')
parser.add_argument('--test-event', action="store_true", help='Submit test event', required=False, dest='test_event')
parser.add_argument('--destination-uri', help='Pass in destination HTTPS URI path for either create subscription or send test event', required=False, dest='destination_uri')
parser.add_argument('--format-type', help='Pass in Event Format Type for creating a subscription. Supported values: Event, MetricReport or None', required=False, dest='format_type')
parser.add_argument('--event-type', help='The EventType value for either create subscription or send test event. Supported values: StatusChange, ResourceUpdated, ResourceAdded, ResourceRemoved, Alert or MetricReport.', required=False, dest='event_type')
parser.add_argument('--message-id', help='Pass in MessageID for sending test event. Example: TMP0118', required=False, dest='message_id')
parser.add_argument('--delete', help='Pass in complete service subscription URI to delete. Execute --get-subscriptions argument if needed to get subscription URIs', required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-subscriptions, this example will get current subscription URIs and details.
    \n- SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --create-subscription --destination-uri https://192.168.0.130 --event-type Alert --format-type MetricReport, this example will create a MetricReport subscription for alert events which will use 192.168.0.130 Redfish event listener.
    \n- SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root --delete /redfish/v1/EventService/Subscriptions/c1a71140-ba1d-11e9-842f-d094662a05e6, this example will first prompt to enter iDRAC user password, then delete a subscription.
    \n- SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --test-event --destination-uri https://192.168.0.130 --event-type Alert --message-id CPU0001, this example shows submitting test event to subscription destination.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/EventService/Subscriptions' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/EventService/Subscriptions' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_event_service_properties():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/EventService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/EventService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- INFO, GET command output for EventService URI\n")
    for i in data.items():
        pprint(i)

def get_event_service_subscriptions():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/EventService/Subscriptions?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/EventService/Subscriptions?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if data["Members"] == []:
        logging.warning("\n- WARNING, no subscriptions detected for iDRAC %s" % idrac_ip)
        sys.exit(0)
    else:
        logging.info("\n- INFO, subscriptions detected for iDRAC ip %s\n" % idrac_ip)
    for i in data["Members"]:
        pprint(i)
        print("\n")

def delete_subscriptions():
    url = "https://%s%s" % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.__dict__["status_code"] == 200:
        logging.info("\n- PASS, DELETE command passed to delete subscription %s" % args["delete"])
    else:
        logging.error("\n- FAIL, DELETE command failed and returned status code %s, error: %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit(0)

def scp_set_idrac_attribute():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    payload = {"ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"IPMILan.1#AlertEnable\">Enabled</Attribute></Component></SystemConfiguration>","ShareParameters":{"Target":"All"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    get_dict = str(response.__dict__)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)   
    if response.status_code != 202:
        logging.error("\n- FAIL, POST command failed to set attributes using SCP feature, status code %s returned" % response.status_code)
        logging.error(get_dict)
        sys.exit(0)
    else:
        logging.info("- %s successfully created for ImportSystemConfiguration method\n" % (job_id))
    while True:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        message_string = data["Messages"]
        final_message_string = str(message_string)
        if response.status_code == 202 or response.status_code == 200:
            time.sleep(1)
        else:
            print("- FAIL, GET job ID details failed, error code %s returned" % response.status_code)
            sys.exit(0)
        if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string:
            logging.error("\n- FAIL, detailed job message: %s" % data["Messages"])
            sys.exit(0)
        elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully imported" in final_message_string:
            logging.info("- Job ID = "+data["Id"])
            logging.info("- Name = "+data["Name"])
            try:
                logging.info("- Message = \n" + message_string[0]["Message"])
            except:
                logging.info("- Message = %s\n" % message_string[len(message_string)-1]["Message"])
            break
        elif "No changes" in final_message_string:
            logging.info("- Job ID = "+data["Id"])
            logging.info("- Name = "+data["Name"])
            try:
                logging.info("- Message = " + message_string[0]["Message"])
            except:
                logging.info("- Message = %s" % message_string[len(message_string)-1]["Message"])
                sys.exit(0)
            break
        else:
            logging.info("- INFO, job not marked completed, current status: %s" % data["TaskState"])
            logging.info("- Message: %s\n" % message_string[0]["Message"])
            time.sleep(1)
            continue
    
def get_set_ipmi_alert_iDRAC_setting():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    while True:
        try:
            attributes_dict=data['Attributes']
        except:
            logging.warning("\n- WARNING, iDRAC version detected does not support PATCH to set iDRAC attributes, executing Server Configuration Profile feature set iDRAC attribute \"IPMILan.1#AlertEnable\" locally\n")
            scp_set_idrac_attribute()
            break
        logging.info("- INFO, checking current value for iDRAC attribute \"IPMILan.1.AlertEnable\"")
        if attributes_dict["IPMILan.1.AlertEnable"] == "Disabled":
            logging.info("- INFO, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" is set to Disabled, setting value to Enabled")
            payload = {"Attributes":{"IPMILan.1.AlertEnable":"Enabled"}}
            url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
            if args["x"]:
                headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
            else:
                headers = {'content-type': 'application/json'}
                response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
            if response.status_code == 200:
                logging.info("- PASS, PATCH command passed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                break
            else:
                logging.error("- FAIL, PATCH command failed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                sys.exit(0)
        else:
            logging.info("- INFO, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" already set to Enabled, ignore PATCH command")
            break

def create_subscription():
    url = "https://%s/redfish/v1/EventService/Subscriptions" % idrac_ip
    payload = {"Destination": args["destination_uri"],"EventTypes": [args["event_type"]],"Context": "root","Protocol": "Redfish", "EventFormatType":args["format_type"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 201:
        logging.info("\n- PASS, POST command passed to create new subscription, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed to create new subscription, status code %s returned, error: %s" % (response.status_code, response.__dict__["_content"]))
        sys.exit(0)
    
def submit_test_event():
    payload = {"Destination": args["destination_uri"],"EventTypes": args["event_type"],"Context": "Root","Protocol": "Redfish","MessageId": args["message_id"]}
    url = "https://%s/redfish/v1/EventService/Actions/EventService.SubmitTestEvent" % idrac_ip
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 204:
        logging.info("\n- PASS, POST command passed to submit test event, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed to submit test event, status code %s returned, error: %s" % (response.status_code, response.__dict__["_content"]))
        sys.exit(0)
    
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
    if args["get_event_properties"]:
        get_event_service_properties()
    elif args["get_subscriptions"]:
        get_event_service_subscriptions()
    elif args["create_subscription"] and args["destination_uri"] and args["event_type"] and args["format_type"]:
        get_set_ipmi_alert_iDRAC_setting()
        create_subscription()
    elif args["test_event"] and args["destination_uri"] and args["event_type"] and args["message_id"]:
        submit_test_event()
    elif args["delete"]:
        delete_subscriptions()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

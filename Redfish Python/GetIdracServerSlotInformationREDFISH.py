#!/usr/bin/python3
#
# GetIdracServerSlotInformationREDFISH. Python script using Redfish API with OEM extension to get iDRAC server slot information.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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
import os
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get server slot information. Slot information includes: Fan, CPU, DIMM, PCI, Backplane, PSU")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get-text', help='Get all server slot information and echo output to the terminal, also redirect output to text file', dest="get_text", action="store_true", required=False)
parser.add_argument('--get-xml', help='Get all server slot information and redirect to XML file. NOTE: This argument will not echo slot information to the terminal.', dest="get_xml", action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetIdracServerSlotInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-text, this example will get slot information for all server devices and redirect output to text file.
    \n- GetIdracServerSlotInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-xml, this example will get slot information for all server devices and redirect output to XML file.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_server_slot_info():
    try:
        os.remove(idrac_ip + "_server_slot_info.txt")
    except:
        pass
    open_file = open("%s_server_slot_info.txt" % idrac_ip,"w")
    get_datetime = datetime.now()
    current_date_time = "- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (get_datetime.month, get_datetime.day, get_datetime.year, get_datetime.hour, get_datetime.minute, get_datetime.second)
    open_file.writelines(current_date_time)
    open_file.writelines("\n\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET request failed, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))
        sys.exit(0)
    if data['Members'] == []:
        logging.error("- FAIL, no data detected for Members property. Manually execute GET on URI 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' in browser to check. If no data detected, reboot server and run Collecting Inventory to refresh the configuration database for iDRAC, try GET again." % idrac_ip)
        sys.exit(0)
    for i in data['Members']:
        pprint(i), print("\n")
        for ii in i.items():
            server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
            open_file.writelines("%s\n" % server_slot_entry)
        open_file.writelines("\n")
    number_list = [i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                open_file.close()
                logging.info("\n- INFO, iDRAC Server Slot Information also captured in \"%s_server_slot_info.txt\" file" % idrac_ip)
                sys.exit(0)
            else:
                logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                sys.exit(0)
        if "Members" not in data or data["Members"] == [] or response.status_code == 400:
            break
        for i in data['Members']:
            pprint(i), print("\n")
            for ii in i.items():
                server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
                open_file.writelines("%s\n" % server_slot_entry)
            open_file.writelines("\n")
    logging.info("\n- INFO, iDRAC Server Slot Information also captured in \"%s_server_slot_info.txt\" file" % idrac_ip)
    open_file.close()

def get_server_slot_info_xml():
    logging.info("\n- INFO, collecting server slot information and converting to XML format, copy to XML file")
    try:
        os.remove(idrac_ip+"_server_slot_info.xml")
    except:
        pass
    open_file = open("%s_server_slot_info.xml" % idrac_ip,"a")
    open_file.writelines("<CIM>\n")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET request failed, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))
        sys.exit(0)
    if data['Members'] == []:
        logging.error("- FAIL, no data detected for Members property. Manually execute GET on URI 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' in browser to check. if no data detected, reboot server and run Collecting Inventory to refresh the configuration database for iDRAC" % idrac_ip)
        sys.exit(0)
    for i in data['Members']:
        create_dict = {}
        for ii in i.items():
            if ii[0] == "Id":
                create_dict[ii[0]] = str(ii[1])
            elif ii[0] == "EmptySlot":
                create_dict[ii[0]] = str(ii[1])
            elif ii[0] == "NumberDescription":
                if ii[1] == "":
                    create_dict["Slot Number"] = "NA"
                else:
                    create_dict["Slot Number"] = str(ii[1])
        create_string = "<VALUE.NAMEDINSTANCE>\n<INSTANCENAME DEVICENAME=\""+create_dict["Id"]+"\">\n<KEYBINDING PROPERTY=\"Slot Number\">\n<VALUE>"+create_dict["Slot Number"]+"</VALUE>\n</KEYBINDING>\n</INSTANCENAME>\n<PROPERTY PROPERTY=\"EmptySlot\">\n<VALUE>"+create_dict["EmptySlot"]+"</VALUE>\n</PROPERTY>\n</VALUE.NAMEDINSTANCE>"  
        open_file.writelines(create_string)
    number_list = [i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        if args["x"]:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
        else:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq), verify=verify_cert,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                open_file.writelines("\n</CIM>")
                open_file.close()
                logging.info("\n- PASS, iDRAC Server Slot Information captured in \"%s_server_slot_info.xml\" file" % idrac_ip)
                sys.exit(0)
            else:
                logging.error("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                sys.exit(0)
        if "Members" not in data or data["Members"] == [] or response.status_code == 400:
            break
        if data['Members'] == []:
            logging.error("- FAIL, no data detected for Members property. Manually execute GET on URI 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' in browser to check. If no data detected, reboot server and run Collecting Inventory to refresh the configuration database for iDRAC, try GET again." % idrac_ip)
            sys.exit(0)
        for i in data['Members']:
            create_dict = {}
            for ii in i.items():
                if ii[0] == "Id":
                    create_dict[ii[0]] = str(ii[1])
                elif ii[0] == "EmptySlot":
                    create_dict[ii[0]] = str(ii[1])
                elif ii[0] == "NumberDescription":
                    create_dict["Slot Number"] = str(ii[1])
            create_string = "<VALUE.NAMEDINSTANCE>\n<INSTANCENAME DEVICENAME=\""+create_dict["Id"]+"\">\n<KEYBINDING PROPERTY=\"Slot Number\">\n<VALUE>"+create_dict["Slot Number"]+"</VALUE>\n</KEYBINDING>\n</INSTANCENAME>\n<PROPERTY PROPERTY=\"EmptySlot\">\n<VALUE>"+create_dict["EmptySlot"]+"</VALUE>\n</PROPERTY>\n</VALUE.NAMEDINSTANCE>"  
            open_file.writelines(create_string)
    logging.info("\n- INFO, iDRAC Server Slot Information captured in \"%s_server_slot_info.xml\" file" % idrac_ip)
    open_file.writelines("\n</CIM>")
    open_file.close()
    
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
    if args["get_text"]:
        get_server_slot_info()
    elif args["get_xml"]:
        get_server_slot_info_xml()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

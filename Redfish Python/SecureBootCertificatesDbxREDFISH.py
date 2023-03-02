#!/usr/bin/python3
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
import os
import re
import requests
import shutil
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to manage BIOS DBX certificates.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get', help='Get all DBX cert URIs detected', action="store_true", required=False)
parser.add_argument('--get-specific', help='Get specific DBX cert only, pass in URI', dest="get_specific", required=False)
parser.add_argument('--export-filename', help='Export DBX cert, pass in unique filename to create and make sure to pass in .hsh file extension. Argument --export-uri is also required for export.', dest="export_filename", required=False)
parser.add_argument('--export-uri', help='Export DBX cert, pass in the DBX URI.', required=False)
parser.add_argument('--import-filename', help='Import DBX cert, pass in filename. Arguments --dir-location and --hashtype are also required when importing. Supported filename extensions are .hsh or .efi', dest="import_filename", required=False)
parser.add_argument('--dir-location', help='Import DBX cert, pass in filename directory location', dest="dir_location", required=False)
parser.add_argument('--hashtype', help='Import DBX cert, pass in the hash type. Supported values are SHA256, SHA384 and SHA512', required=False)
parser.add_argument('--delete', help='Delete DBX cert, pass in URI', required=False)
parser.add_argument('--reboot', help='Reboot server to apply delete or import cert changes. Note: server reboot is needed to apply the changes.', action="store_true", required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get all DBX certs.
    \n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-specific /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84, this example will only return data for this DBX cert.
    \n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --export-uri /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84 --export-filename dbx_84_cert.hsh, this example will export DBX cert 84.
    \n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84, this example deletes DBX cert 84.
    \n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --reboot, this example reboots the server. Reboot the server is required after delete or import DBX cert for the changes to be applied.
    \n- SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin --import-filename dbx_84_cert.hsh --dir-location C:\Python38-32 --hashtype SHA256, this example will import DBX cert.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET command failed to check supported iDRAC version, status code %s returned" % response.status_code)
        sys.exit(0)

def reboot_server():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, POST command passed to gracefully power OFF server")
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        while True:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
            else:
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                if args["x"]:
                    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("- PASS, POST command passed to perform forced shutdown, status code return is %s" % response.status_code)
                    time.sleep(15)
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        logging.info("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        logging.error("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit(0)    
            else:
                continue 
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, command passed to power ON server")
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        if args["x"]:
            headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
        else:
            headers = {'content-type': 'application/json'}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
        if response.status_code == 204:
            logging.info("- PASS, command passed to power ON server")
        else:
            logging.error("\n- FAIL, command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(0)

def export_DBX():
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, args["export_uri"]), verify=verify_cert, headers={'X-Auth-Token': args["x"], "accept":"application/octet-stream"}, stream=True)   
    else:
        response = requests.get('https://%s%s' % (idrac_ip, args["export_uri"]), verify=verify_cert,auth=(idrac_username, idrac_password), headers={"accept":"application/octet-stream"}, stream=True)
    if response.status_code == 200:
        logging.info("\n- PASS, export DBX cert was successful")
    else:
        data = response.json()
        logging.error("\n- FAIL, export DBX cert failed, status code %s returned, detailed error: \n%s" % (response.status_code, data))
        sys.exit(0)
    with open(args["export_filename"], 'wb') as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)
    logging.info("- INFO, DBX cert copied to file \"%s\"" % args["export_filename"])

def import_DBX():
    filename = args["import_filename"]
    ImageLocation = args["dir_location"]
    ImagePath = os.path.join(ImageLocation, filename)
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/' % (idrac_ip)
    payload = {"CryptographicHash": args["hashtype"]}
    files = {'text':(None, json.dumps(payload), 'application/json'),'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    if args["x"]:
        headers = {'X-Auth-Token': args["x"]}
        response = requests.post(url, files=files, data=payload, headers=headers, verify=verify_cert)
    else:
        response = requests.post(url, files=files, data=payload, verify=verify_cert, auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
        logging.info("\n- PASS, import DBX cert passed. Server reboot is required to apply the changes.")
    else:
        data = response.json()
        logging.error("- FAIL, POST command failed to import DBX cert, status code %s returned. Error results: \n%s" % (response.status_code, data))
        sys.exit(0)
        
def get_all_DBX_URIs():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/%s' % (idrac_ip, "DBX"), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/%s' % (idrac_ip, "DBX"), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n- Ceritificate \"%s\" Key Type Entries For iDRAC %s -\n" % ("DBX", idrac_ip))
    time.sleep(3)
    if data["Hash"] == []:
        key = "Certificates"
    elif data["Certificates"] == []:
        key = "Hash"
    else:
        logging.warning("\n- WARNING, no certificate entries detected")
        sys.exit(0)
    for i in data[key]:
        for ii in i.items():
            print("%s: %s" % (ii[0], ii[1]))
        print("\n")

def get_DBX_uri():
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_specific"]), verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s%s' % (idrac_ip, args["get_specific"]), verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed, status code %s returned, detailed error results: %s" % (response.status_code, data))
        sys.exit(0)
    logging.info("\n- Certificate information for URI \"%s\" -\n" % args["get_specific"])
    for i in data.items():
        print("%s: %s" % (i[0], i[1]))

def delete_hash():
    url = 'https://%s%s' % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("- FAIL, unable to delete certificate hash, status code is %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    else:
        logging.info("\n- PASS, DELETE command passed to delete certificate hash. Server reboot is required to apply the changes.")

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
    if args["export_filename"] and args["export_uri"]:
        export_DBX()
    elif args["get"]:
        get_all_DBX_URIs()
    elif args["import_filename"] and args["dir_location"] and args["hashtype"]:
        import_DBX()
    elif args["get_specific"]:
        get_DBX_uri()
    elif args["delete"]:
        delete_hash()
    elif args["reboot"]:
        reboot_server()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

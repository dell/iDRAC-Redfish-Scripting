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

import argparse
import base64
import csv
import getpass
import json
import logging
import os
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to manage BIOS HTTP certificates.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('--ssl', help='Verify SSL certificate for all Redfish calls, pass in \"true\". This argument is optional, if you do not pass in this argument, all Redfish calls will ignore SSL cert checks.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID to execute all Redfish calls instead of passing in username/password', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--import', help='Import BIOS HTTP certificate. Argument --filename is also required for import. Note server reboot is required for the changes to become effective.', action="store_true", required=False)
parser.add_argument('--delete', help='Delete BIOS HTTP certificate, pass in the cert URI you want to delete. Note server reboot is required for the changes to become effective.', required=False)
parser.add_argument('--enable-bios-http-devices', help='Enable BIOS HTTP devices and set TLS mode to one way. This is required settings before you can import BIOS HTTP cert.', action="store_true", dest="enable_bios_http_device", required=False)
parser.add_argument('--get-current-certs', help='Get current BIOS HTTP certificates detected/installed', action="store_true", dest="get_current_certs", required=False)
parser.add_argument('--filename', help='Pass in the file name which contains the certificate to import.', required=False)
parser.add_argument('--reboot-server', help='Pass in this argument to reboot the server now to apply certificate changes', dest="reboot_server", action="store_true", required=False)


args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)


def script_examples():
    print("""\n- BiosHttpCertSupportREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-current-certs, this example will return current installed certs.
    \n BiosHttpCertSupportREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/Systems/System.Embedded.1/Boot/Certificates/SecurityCertificate.4 --reboot-server, this example will delete cert and reboot server now to apply changes
    \n- BiosHttpCertSupportREDFISH.py -ip 192.168.0.120 -u root -p calvin --enable-bios-http-devices --import --filename C:\\Users\\administrator\\Downloads\\http.crt --reboot-server, this enable to enable BIOS HTTP boot devices using BIOS config job. Once BIOS config job is marked completed HTTP cert will get imported and reboot server now to apply changes.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Boot/Certificates' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Boot/Certificates' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_current_certs():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Boot/Certificates?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Boot/Certificates?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET commmand failed to get current cert details, status code %s returned" % response.status_code)
        logging.error("- Detailed error results: %s" % data)
        sys.exit(0)
    if data["Members"] == []:
        logging.info("\n- WARNING, no BIOS HTTP certs detected")
        sys.exit(0)
    for i in data.items():
        pprint(i)
    
def import_HTTP_BIOS_cert():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Boot/Certificates' % (idrac_ip)
    if "p12" in args["filename"]:
        with open(args["filename"], 'rb') as cert:
            cert_content = cert.read()
            read_file = base64.encodebytes(cert_content).decode('ascii')
    else:
        with open(args["filename"],"r") as x:
            read_file = x.read()
    payload={"CertificateType":"PEM","CertificateString":read_file}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 201:
        logging.info("\n- PASS: POST command passed to import BIOS HTTP cert, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, POST command failed to import BIOS HTTP cert, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)

def delete_HTTP_BIOS_cert():
    url = 'https://%s%s' % (idrac_ip, args["delete"])
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.delete(url, headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: DELETE command passed to delete BIOS HTTP cert, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, DELETE command failed to delete BIOS HTTP cert, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- DELETE command failure results:\n %s" % data)
        sys.exit(0)


def reboot_server():
    logging.info("- INFO, rebooting server now to either run BIOS config job or apply certificate changes")
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("- INFO, Current server power state: %s" % data['PowerState'])
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
            logging.info("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 2 minutes")
            time.sleep(60)
            start_time = datetime.now()
        else:
            logging.error("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
        retry_count = 1
        while True:
            if retry_count == 20:
                logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
                sys.exit(0)
            try:
                if args["x"]:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                else:
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
            except requests.ConnectionError as error_message:
                logging.info("- INFO, GET request failed due to connection error, script will sleep 15 seconds and retry")
                time.sleep(15)
                retry_count += 1
                continue 
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                logging.info("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time >= "0:02:00":
                logging.info("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                time.sleep(60)
                if args["x"]:
                    headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
                else:
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
                if response.status_code == 204:
                    logging.info("- PASS, POST command passed to perform forced shutdown")
                    time.sleep(60)
                    if args["x"]:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                    else:
                        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                    try:
                        data = response.json()
                    except:
                        logging.warning("- WARNING, unable to get json response to validate current power state, retry in 30 seconds")
                        time.sleep(30)
                        if args["x"]:
                            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})   
                        else:
                            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
                        try:
                            data = response.json()
                        except:
                            logging.error("- FAIL, retry to get power state failed, script will exit")
                            sys.exit(0)
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
            logging.info("- PASS, POST command passed to power ON server")
            time.sleep(15)
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
            logging.info("- PASS, Command passed to power ON server, code return is %s" % response.status_code)
        else:
            logging.error("\n- FAIL, Command failed to power ON server, status code is: %s\n" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            sys.exit(0)
    else:
        logging.error("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit(0)

def enable_bios_http_device():
    global job_id
    global run_bios_config_job
    run_bios_config_job = False
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip, verify=verify_cert,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, GET command failed to get BIOS attributes, status code %s returned" % response.status_code)
        logging.error(data)
        sys.exit(0)
    http_device_values = []
    for i in data['Attributes'].items():
        if i[0] == "HttpDev1EnDis" or i[0] == "HttpDev2EnDis" or i[0] == "HttpDev3EnDis" or i[0] == "HttpDev4EnDis" or i[0] == "HttpDev1TlsMode" or i[0] == "HttpDev2TlsMode" or i[0] == "HttpDev3TlsMode" or i[0] == "HttpDev4TlsMode":
            http_device_values.append(i[1])
    if "Disabled" in http_device_values or "None" in http_device_values:
        logging.info("- INFO, all BIOS HTTP Devices are either not enabled or TLS mode not set to one way, creating BIOS config job to set these attributes")
        run_bios_config_job = True
    else:
        logging.info("\n- INFO, all BIOS HTTP Devices are set to enabled and TLS set to OneWay, no BIOS config job required")
        return
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"},"Attributes":{"HttpDev1EnDis":"Enabled","HttpDev1TlsMode":"OneWay","HttpDev2EnDis":"Enabled","HttpDev2TlsMode":"OneWay","HttpDev3EnDis":"Enabled","HttpDev3TlsMode":"OneWay","HttpDev4EnDis":"Enabled","HttpDev4TlsMode":"OneWay"}}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        logging.debug("\n- PASS: PATCH command passed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
    else:
        logging.error("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
        data = response.json()
        logging.error("\n- POST command failure:\n %s" % data)
        sys.exit(0)
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to locate job ID in JSON headers output")
        sys.exit(0)
    logging.info("- PASS, BIOS config job ID %s successfully created" % job_id)

def get_job_status_scheduled():
    count = 0
    while True:
        if count == 5:
            logging.error("- FAIL, GET job status retry count of 5 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.error(error_message)
            logging.info("\n- INFO, GET request will try again to poll job status")
            time.sleep(5)
            count += 1
            continue
        if response.status_code == 200:
            time.sleep(5)
        else:
            logging.error("\n- FAIL, Command failed to check job status, return code %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(response.json()))
            return
        data = response.json()
        if data['Message'] == "Task successfully scheduled.":
            logging.info("- INFO, staged config job marked as scheduled")
            break
        else:
            logging.info("- INFO: job status not scheduled, current status: %s" % data['Message'])

def loop_job_status_final():
    start_time = datetime.now()
    retry_count = 1
    while True:
        if retry_count == 20:
            logging.warning("- WARNING, GET command retry count of 20 has been reached, script will exit")
            sys.exit(0)
        try:
            if args["x"]:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
            else:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), verify=verify_cert,auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.info("- INFO, GET request failed due to connection error, retry")
            if "powercyclerequest" in args["attribute_names"].lower():
                logging.info("- INFO, PowerCycleRequest attribute detected, virtual a/c cycle is running. Script will sleep for 180 seconds, retry")
                time.sleep(180)
            else:
                time.sleep(60)
            retry_count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code != 200:
            logging.error("\n- FAIL, GET command failed to check job status, return code is %s" % response.status_code)
            logging.error("Extended Info Message: {0}".format(req.json()))
            return
        data = response.json()
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            return
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            logging.error("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            return
        elif data['JobState'] == "Completed":
            logging.info("- PASS, job ID %s successfully marked completed" % job_id)
            break
        else:
            logging.info("- INFO, job status not completed, current status: \"%s\"" % data['Message'])
            time.sleep(10)

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
    if args["get_current_certs"]:
        get_current_certs()
    elif args["enable_bios_http_device"]:
        enable_bios_http_device()
        if run_bios_config_job != False:
            get_job_status_scheduled()
            reboot_server()
            loop_job_status_final()
            if args["import"] and args["filename"]:
                import_HTTP_BIOS_cert()
                if args["reboot_server"]:
                    reboot_server()
                else:
                    logging.info("- WARNING, --reboot-server argument not detected. Cert changes will become effective on next server manual reboot")
    elif args["import"] and args["filename"]:
        import_HTTP_BIOS_cert()
        if args["reboot_server"]:
            reboot_server()
        else:
            logging.info("- WARNING, --reboot-server argument not detected. Cert changes will become effective on next server manual reboot")
    elif args["delete"]:
        delete_HTTP_BIOS_cert()
        if args["reboot_server"]:
            reboot_server()
        else:
            logging.info("- WARNING, --reboot-server argument not detected. Cert changes will become effective on next server manual reboot")
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

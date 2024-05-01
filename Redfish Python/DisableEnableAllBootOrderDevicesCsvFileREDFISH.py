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
#
# Edited CSV file example leveraging 'iDRAC_details_disable_boot_devices_example.csv' file from GitHub:
#
# iDRAC IP	        iDRAC Username	iDRAC Password	
# 192.168.0.120	        root		calvin	
# 192.168.0.130	        root            calvin
#
# Script pseudo code workflow:
#
# 1. Get current BIOS boot order devices
# 2. Create SCP import job to change enable/disable setting for all BIOS boot order devices for each iDRAC detected.
# 3. Loop querying job ID until marked completed. Note when you do configure multiple iDRACs all jobs will run in parallel even though the script will echo checking one job ID. 
# 4. Get BIOS boot order devices again and confirm either enabled or disabled.
# 5. Power off server if power-off argument detected. 


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

parser = argparse.ArgumentParser(description="Python script using Redfish API to either disable or enable all BIOS boot order devices using Server Configuration Profile (SCP) feature for multiple iDRACs using CSV file. NOTE: View comments in script to see CSV file examples for different workflow scenarios.")
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('-ip',help='Pass in iDRAC IP address. Note this argument is required if you do not want to use CSV file and only configure one server.', required=False)
parser.add_argument('-u', help='Pass in iDRAC username. Note this argument is required if you do not want to use CSV file and only configure one server.', required=False)
parser.add_argument('-p', help='Pass in iDRAC password. Note this argument is required if you do not want to use CSV file and only configure one server.', required=False)
parser.add_argument('--disable', help='Disable all BIOS boot order devices', action="store_true", required=False)
parser.add_argument('--enable', help='Enable all boot order devices', action="store_true", required=False)
parser.add_argument('--power-off', help='Power off the server once all BIOS boot order devices are enabled or disabled', action="store_true", required=False)
parser.add_argument('--csv-filename', help='Pass in CSV filename to configure multiple iDRACs', dest="csv_filename", required=False)


args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- python DisableEnableAllBootOrderDevicesCsvFileREDFISH.py --csv-filename iDRAC_details_disable_boot_devices_example.csv --disable --power-off, this example will leverage CSV file to disable all bios boot order devices for multiple iDRACs.
    \n- python DisableEnableAllBootOrderDevicesCsvFileREDFISH.py -ip 192.168.0.120 -u root -p calvin --enable, this example will enable all bios boot order devices for one iDRAC.""")
    return


def get_current_boot_order_devices(idrac_ip, idrac_username, idrac_password, check):
    # Function to get current boot order devices for the server
    global boot_order_devices
    boot_order_devices = ""
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip, verify = False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        return
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        return
    if check == "new":
        print_final_success_message = "yes"
        for i in data["Attributes"]["UefiBootSeq"]:
            for ii in i.items():
                if ii[0] == "Enabled":
                    if args["disable"]:
                        arg_name = "disabled"
                        if ii[1] != False and "Unknown" not in i["Name"] and "Virtual" not in i["Name"]:
                            logging.error("- FAIL, boot order device %s is not disabled" % i["Name"])
                            print_final_success_message = "no"
                    elif args["enable"]:
                        arg_name = "enabled"
                        if ii[1] != True and "Unknown" not in i["Name"] and "Virtual" not in i["Name"]:
                            logging.error("- FAIL, boot order device %s is not enabled" % i["Name"])
                            print_final_success_message = "no"
        if print_final_success_message == "yes":
            logging.info("\n- PASS, confirmed all boot devices successfully %s for iDRAC IP %s" % (arg_name, idrac_ip))
        elif print_final_success_message == "no":
            logging.error("- WARNING, one or more boot devices still %s for iDRAC IP %s" % (arg_name, idrac_ip))
            logging.info("\n- INFO current boot order details -\n")
            print("\n")
            for i in data["Attributes"]["UefiBootSeq"]:
                for ii in i.items():
                    print("%s: %s" % (ii[0], ii[1]))
                print("\n")
    else:
        for i in data["Attributes"]["UefiBootSeq"]:
            for ii in i.items():
                if ii[0] == "Name":
                    boot_order_devices = boot_order_devices+ii[1]+","
        boot_order_devices = boot_order_devices.rstrip(",")

def import_SCP_local_filename(idrac_ip, idrac_username, idrac_password, boot_order_devices):
    # Function to import SCP file for multiple iDRACs using CSV to get iDRAC details. 
    global job_id
    logging.info("\n- INFO, applying BIOS boot order changes for iDRAC IP %s -" % idrac_ip)   
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    # Code needed to modify the SCP file to one string to pass in for POST command
    if args["disable"]:
        payload = {"ImportBuffer":"<SystemConfiguration><Component FQDD=\"BIOS.Setup.1-1\"><Attribute Name=\"SetBootOrderDis\">%s</Attribute></Component></SystemConfiguration>" % boot_order_devices,"ShareParameters":{"Target":"BIOS"}}
    elif args["enable"]:
        payload = {"ImportBuffer":"<SystemConfiguration><Component FQDD=\"BIOS.Setup.1-1\"><Attribute Name=\"SetBootOrderEn\">%s</Attribute></Component></SystemConfiguration>" % boot_order_devices,"ShareParameters":{"Target":"BIOS"}}
    payload["ShutdownType"] = "Forced"
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 202:
        logging.error("\n- FAIL, POST command failed for import system configuration, status code %s returned" % response.status_code)
        logging.error(response.json())
        return
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        logging.error("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        return
    logging.info("\n- PASS, %s job ID successfully created for ImportSystemConfiguration method" % (job_id))
    

def loop_job_id(idrac_ip, idrac_username, idrac_password, job_id):
    # Function to loop checking final job status for SCP import job ID. The function will loop and check the job status for each iDRAC job created.
    logging.info("\n- INFO, loop checking %s job status for iDRAC %s until marked completed" % (job_id, idrac_ip))
    start_time = datetime.now()
    time.sleep(10)
    start_job_message = ""
    count = 1
    get_job_status_count = 1
    while True:
        current_time = (datetime.now()-start_time)
        if str(current_time)[0:7] >= "2:00:00":
            logging.error("\n- FAIL: timeout of 2 hours has been hit for querying job status. Manually check the server to debug the issue, check iDRAC job queue and LC logs.\n")
            return
        if count == 10:
            logging.error("- FAIL, 10 attempts at getting job status failed, script will exit")
            return
        if get_job_status_count == 10:
            logging.warning("- WARNING, retry count of 10 has been hit for retry job status GET request, script will exit")
            return
        try:
            response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), verify=False, auth=(idrac_username, idrac_password))
        except requests.ConnectionError as error_message:
            logging.warning("- WARNING, requests command failed to GET job status, detailed error information: \n%s" % error_message)
            logging.info("- INFO, script will attempt to get job status again")
            time.sleep(10)
            count += 1
            continue
        data = response.json()
        try:
            current_job_message = data['Oem']['Dell']['Message']
        except:
            logging.info("- INFO, unable to get job ID message string from JSON output, retry")
            count += 1
            continue
        current_time = (datetime.now()-start_time)
        if response.status_code == 202 or response.status_code == 200:
            time.sleep(1)
        else:
            logging.info("- INFO, GET command failed to get job ID details, error code: %s, retry" % response.status_code)
            count += 1
            time.sleep(5)
            continue
        if "Oem" not in data:
            logging.info("- INFO, unable to locate OEM data in JSON response, retry")
            get_job_status_count += 1
            time.sleep(5)
            continue
        if data['Oem']['Dell']['JobState'] == "Failed" or data['Oem']['Dell']['JobState'] == "CompletedWithErrors":
            logging.info("\n- INFO, job ID %s status marked as \"%s\" for iDRAC IP %s" % (job_id, data['Oem']['Dell']['JobState'], idrac_ip))
            logging.info("\n- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    print("%s: %s" % (i[0], i[1]))
            logging.debug("\n- %s completed in: %s\n" % (job_id, str(current_time)[0:7]))
            return
        elif data['Oem']['Dell']['JobState'] == "Completed":
            if "fail" in data['Oem']['Dell']['Message'].lower() or "error" in data['Oem']['Dell']['Message'].lower() or "not" in data['Oem']['Dell']['Message'].lower() or "unable" in data['Oem']['Dell']['Message'].lower() or "no device configuration" in data['Oem']['Dell']['Message'].lower() or "time" in data['Oem']['Dell']['Message'].lower():
                logging.error("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
            elif "success" in data['Oem']['Dell']['Message'].lower():
                logging.info("- PASS, job ID %s successfully marked completed for iDRAC %s\n" % (job_id, idrac_ip))
            elif "no changes" in data['Oem']['Dell']['Message'].lower():
                logging.info("\n- PASS, job ID %s marked completed for iDRAC IP %s\n" % (job_id, idrac_ip))
                logging.info("- Detailed job results for job ID %s\n" % job_id)
                for i in data['Oem']['Dell'].items():
                    pprint(i)
                print("\n")
                return
            logging.info("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
            try:
                for i in data["Messages"]:
                    pprint(i)
            except:
                logging.error("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
                for i in data['Oem']['Dell'].items():
                    pprint(i)
            logging.debug("\n- %s completed in: %s\n" % (job_id, str(current_time)[0:7]))
            return
        elif "No reboot Server" in data['Oem']['Dell']['Message']:
            logging.info("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
            logging.info("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            return
        else:
            if start_job_message != current_job_message:
                logging.info("- INFO, \"%s\", percent complete: %s" % (data['Oem']['Dell']['Message'].strip('"'),data['Oem']['Dell']['PercentComplete']))
                start_job_message = current_job_message
                continue

def power_off_server(idrac_ip, idrac_username, idrac_password):
    # Function to power off server once SCP import job is marked completed and verify server did power off once all bios boot devices are either disabled or enabled
    logging.info("- INFO, argument --power-off detected, powering off server")
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {"ResetType": "ForceOff"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        logging.debug("\n- PASS, POST action passed to power off the server")
        time.sleep(15)
    else:
        logging.error("\n- FAIL, POST action failed to power off server, status code %s returned\n" % response.status_code)
        logging.error(response.json())
        return
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.warning("\n- WARNING, GET request failed to get current server power state, status code %s returned." % response.status_code)
        logging.warning(data)
        return
    if data["PowerState"] == "Off":
        logging.info("- PASS, confirmed server is in OFF state")
    else:
        logging.error("- FAIL, server not in OFF state, current server power status: %s" % data["PowerState"])
            
if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["u"] and args["p"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        idrac_password = args["p"]
        get_current_boot_order_devices(idrac_ip, idrac_username, idrac_password, "old")
        import_SCP_local_filename(idrac_ip, idrac_username, idrac_password, boot_order_devices)
        loop_job_id(idrac_ip, idrac_username, idrac_password, job_id)
        get_current_boot_order_devices(idrac_ip, idrac_username, idrac_password, "new")
        if args["power_off"]:
            power_off_server(i[1][0], i[1][1], i[1][2])
    elif args["csv_filename"] and args["enable"] or args["disable"]:
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
            get_current_boot_order_devices(i[1][0], i[1][1], i[1][2], "old")
            import_SCP_local_filename(i[1][0], i[1][1], i[1][2], boot_order_devices)
            idrac_details_dict[i[0]].append(job_id)
        for i in idrac_details_dict.items():
            loop_job_id(i[1][0], i[1][1], i[1][2], i[1][3])
            time.sleep(30)
            get_current_boot_order_devices(i[1][0], i[1][1], i[1][2], "new")
            if args["power_off"]:
                power_off_server(i[1][0], i[1][1], i[1][2])     
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

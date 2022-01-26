#
# ExportHWInventoryREDFISH. Python script using Redfish API with OEM extension to export server hardware(HW)
# inventory to either local directory or network share
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _author_ = Grant Curell <grant_curell@dell.com>
# _version_ = 5.0
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
import os
import sys
import warnings
from datetime import datetime
from pprint import pprint

import requests

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export server "
                                             "hardware(HW) inventory to either local directory or supported network "
                                             "share")
parser.add_argument('-ip', help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples', action="store_true",
                    help='ExportHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 '
                         '--sharetype CIFS --sharename cifs_share_vm --username administrator --password pass '
                         '--filename export_hw_inv.xml, this example will export the server hardware inventory to a'
                         ' CIFS share.\n'
                         'ExportHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin --sharetype local, this'
                         ' example will export the HW configuration locally to an XML file.')
parser.add_argument('-s', help='Get supported network share types', required=False, action='store_true')
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype',
                    help='Pass in the share type of the network share to export or pass in "Local" to perform local'
                         ' export. For supported network share types, execute -s argument. NOTE: When passing in Local'
                         ' for share type, you don\'t need to pass in any other arguments. This exported HW inventory '
                         'file will be in XML format.', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the network username', required=False)
parser.add_argument('--password', help='Pass in the network username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional',
                    required=False)
parser.add_argument('--filename', help='Pass in unique file name string for export HW inventory file. This argument is'
                    ' only required for exporting to network share, not required for local export.', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only supported for'
                                                ' HTTPS share type', required=False)

args = vars(parser.parse_args())

idrac_ip = args["ip"]
idrac_username = args["u"]
idrac_password = args["p"]


def check_supported_idrac_version():
    """
    Contacts the Redfish API and pulls a list of supported features. Validates that the ExportHWInventory key is
    present. If it is not, it terminates the program.
    """
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,
                            verify=False, auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC"
              " username/password and the IDRAC user has the correct privileges")
        sys.exit()
    data = response.json()
    if "#DellLCService.ExportHWInventory" not in data['Actions']:
        print("\n- Error, iDRAC version installed does not seem to support the ExportHWInventory function.")
        sys.exit()


def get_supported_network_share_types():
    """
    Contacts the iDRAC and, if exporting hardware inventory is supported, retrieves a list of supported share types
    """
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,
                            verify=False, auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Supported network share types for ExportHWInventory Action -\n")
    for action in data['Actions'].items():
        if action[0] == "#DellLCService.ExportHWInventory":
            for allowed_sharetype in action[1]['ShareType@Redfish.AllowableValues']:
                print(allowed_sharetype)


def export_hw_inventory() -> str:
    """
    Exports hardware inventory using the user-indicated share type

    :return: Returns the job ID in the form 'JID_<ID>'. Ex: 'JID_431917118151'
    """
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportHWInventory' % idrac_ip
    METHOD = "ExportHWInventory"

    headers = {'content-type': 'application/json'}
    payload = {}
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        if args["sharetype"] == "local" or args["sharetype"] == "Local":
            payload["ShareType"] = args["sharetype"].title()
        else:
            payload["ShareType"] = args["sharetype"].upper()
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["filename"]:
        payload["FileName"] = args["filename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    print("\n- WARNING, arguments and values for %s method\n" % METHOD)
    for key in payload.items():
        if key[0] == "Password":
            print("Password: ********")
        else:
            print("%s: %s" % (key[0], key[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,
                             auth=(idrac_username, idrac_password))
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code 202 returned" % METHOD)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (METHOD, response.status_code))
        data = response.json()
        print("\n- POST command failure results:")
        pprint(data)
        sys.exit()
    if args["sharetype"].lower() == "local":
        if not args["filename"]:
            get_service_tag = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=False,
                                           auth=(idrac_username, idrac_password))
            data_get_service_tag = get_service_tag.json()
            chassis_service_tag = data_get_service_tag['Oem']['Dell']['DellSystem']['NodeID']
            get_datetime_info = datetime.now()
            export_filename = "%s-%s-%s_%s%s%s_export_HW_inventory_%s.xml" % (
                get_datetime_info.year, get_datetime_info.month, get_datetime_info.day, get_datetime_info.hour,
                get_datetime_info.minute, get_datetime_info.second, chassis_service_tag)
        else:
            export_filename = args["filename"]

        print("- INFO, Redfish export HW inventory URI: \"%s\"\n" % response.headers['Location'])
        response = requests.get('https://%s%s' % (idrac_ip, response.headers['Location']), verify=False,
                                auth=(idrac_username, idrac_password))
        filename_open = open(export_filename, "a")
        dict_response = response.__dict__['_content']
        string_convert = str(dict_response)
        string_convert = string_convert.lstrip("'b")
        string_convert = string_convert.rstrip("'")
        string_convert = string_convert.split("\\n")
        for key in string_convert:
            filename_open.writelines(key)
            filename_open.writelines("\n")
        filename_open.close()
        print("- INFO, Exported HW inventory captured to file \"%s\\%s\"" % (os.getcwd(), export_filename))
        sys.exit()
    else:
        try:
            job_id = response.headers['Location'].split("/")[-1]
            print("- PASS, job ID %s successfully created for %s method\n" % (job_id, METHOD))
            return job_id
        except:
            print("- FAIL, unable to find job ID in headers POST response, headers output is:")
            pprint(dict(response.headers))
            sys.exit()


def loop_job_status(job_id: str):
    """
    Finds and then waits for the iDRAC share export job to finish

    :param job_id: ID of the iDRAC job for exporting the inventory to a share. This is obtained from the call to
                   DellLCService.ExportHWInventory.
    """
    start_time = datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id),
                           auth=(idrac_username, idrac_password), verify=False)
        current_time = (datetime.now() - start_time)
        status_code = req.status_code
        if status_code != 200:
            print("\n- FAIL, Command failed to check job status, return code is %s" % status_code)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:05:00":
            print("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in \
                data[u'Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        elif data['JobState'] == "Completed":
            if data['Message'] == "Hardware Inventory Export was successful":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                print("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" not in i[0] and "MessageArgs" not in i[0] and "TargetSettingsURI" not in i[0]:
                    print("%s: %s" % (i[0], i[1]))
            break
        else:
            print("- INFO, job state not marked completed, current job status is running, polling again")


if __name__ == "__main__":

    if not args["s"] and args["sharetype"] != "local" and not args["ipaddress"]:
        print("- ERROR, When not using the -s argument you must include the ipaddress of the target share.")
        sys.exit()
    if not args["s"] and args["sharetype"] != "local" and not args["username"]:
        print("- ERROR, When not using the -s argument you must include the username of the target share.")
    if not args["s"] and args["sharetype"] != "local" and not args["password"]:
        print("- ERROR, When not using the -s argument you must include the password of the target share.")
        sys.exit()
    try:
        check_supported_idrac_version()
    except requests.exceptions.RequestException as e:
        print("Failed to connect to the iDRAC. Are you sure it is up?")
        raise SystemExit(e)
    if args["s"]:
        get_supported_network_share_types()
    else:
        loop_job_status(export_hw_inventory())

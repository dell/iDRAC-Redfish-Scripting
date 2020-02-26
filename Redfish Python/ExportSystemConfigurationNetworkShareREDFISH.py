#!/usr/bin/python
# ExportServerConfigurationNetworkShareREDFISH. Python script using Redfish API to export server configuration profile to a supported network share.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 7.0
#
# Copyright (c) 2017, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to export server configuration profile (SCP) to a supported network share")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportSystemConfigurationNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin -t ALL -xf XML --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --filename SCP_export_R740, this example is going to export attributes for all devices in a default XML SCP file to a NFS share. \nExportSystemConfigurationNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin -t BIOS -xf JSON --ipaddress 192.168.0.140 --sharetype CIFS --sharename cifs_share_vm --filename R740_scp_file -e Clone --username administrator --password password, this example is going to export only BIOS attributes in a clone JSON SCP file to a CIFS share.')
parser.add_argument('-st', help='Pass in \"y\" to get supported share types for your iDRAC firmware version', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. If needed, use argument -st to get supported values for your iDRAC firmware version', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username password', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('-t', help='Pass in Target value to get component attributes. You can pass in \"ALL" to get all component attributes or pass in a specific component to get only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=False)
parser.add_argument('-e', help='Pass in ExportUse value. Supported values are Default, Clone and Replace. If you don\'t use this parameter, default setting is Default or Normal export.', required=False)
parser.add_argument('-i', help='Pass in IncludeInExport value. Supported values are 0 for \"Default\", 1 for \"IncludeReadOnly\", 2 for \"IncludePasswordHashValues\" or 3 for \"IncludeReadOnly,IncludePasswordHashValues\". If you don\'t use this parameter, default setting is Default for IncludeInExport.', required=False)
parser.add_argument('--filename', help='Pass in unique filename for the SCP file which will get created on the network share', required=False)
parser.add_argument('-xf', help='Pass in the format type for SCP file generated. Supported values are XML and JSON', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Enabled and Disabled. This argument is only required if using HTTPS for share type', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def get_sharetypes():
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    print("\n- ExportSystemConfiguration supported share types for iDRAC %s\n" % idrac_ip)
    if 'OemManager.v1_0_0#OemManager.ExportSystemConfiguration' in data['Actions']['Oem']:
        share_types = data['Actions']['Oem']['OemManager.v1_0_0#OemManager.ExportSystemConfiguration']['ShareParameters']['ShareType@Redfish.AllowableValues']
    else:
        share_types = data['Actions']['Oem']['OemManager.v1_1_0#OemManager.ExportSystemConfiguration']['ShareParameters']['ShareType@Redfish.AllowableValues']
    for i in share_types:
        if i == "LOCAL":
            pass
        else:
            print(i)

def export_server_configuration_profile():
    global job_id
    method = "ExportSystemConfiguration"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
    payload = {"ExportFormat":args['xf'],"ShareParameters":{"Target":args["t"]}}
    if args["e"]:
        payload["ExportUse"] = args["e"]
    if args["i"]:
        if args["i"] == "1":
            payload["IncludeInExport"] = "Default"
        if args["i"] == "2":
            payload["IncludeInExport"] = "IncludeReadOnly"
        if args["i"] == "3":
            payload["IncludeInExport"] = "IncludePasswordHashValues"
        if args["i"] == "4":
            payload["IncludeInExport"] = "IncludeReadOnly,IncludePasswordHashValues"
    if args["ipaddress"]:
        payload["ShareParameters"]["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareParameters"]["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareParameters"]["ShareName"] = args["sharename"]
    if args["filename"]:
            payload["ShareParameters"]["FileName"] = args["filename"]
    if args["username"]:
        payload["ShareParameters"]["Username"] = args["username"]
    if args["password"]:
        payload["ShareParameters"]["Password"] = args["password"]
    if args["workgroup"]:
        payload["ShareParameters"]["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["ShareParameters"]["IgnoreCertificateWarning"] = args["ignorecertwarning"]
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
        if i[0] == "ShareParameters":
            for ii in i[1].items():
                if ii[0] == "Password":
                    print("Password: **********")
                else:
                    print("%s: %s" % (ii[0],ii[1]))
        else:
            print("%s: %s" % (i[0],i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    response_output_convert_to_string = str(response.__dict__)
    
    try:
        z=re.search("JID_.+?,",response_output_convert_to_string).group()
    except:    
        print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit()

    job_id=re.sub("[,']","",z)
    if response.status_code != 202:
        print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code)   
        sys.exit()
    else:
        print("\n- %s successfully created for ExportSystemConfiguration method\n" % (job_id)) 

    response_output=response.__dict__
    job_id=response_output["headers"]["Location"]
    job_id=re.search("JID_.+",job_id).group()


def loop_job_status():
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:05:00":
            print("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif data['JobState'] == "Completed":
            if data['Message'] == "Successfully exported Server Configuration Profile":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                print("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Message'],data['PercentComplete']))
            time.sleep(1)


if __name__ == "__main__":
    if args["st"]:
        get_sharetypes()
    else:
        export_server_configuration_profile()
        loop_job_status()
    
    

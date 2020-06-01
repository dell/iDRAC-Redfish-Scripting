#
# ImportSystemConfigurationNetworkSharePreviewREDFISH. Python script using Redfish API to preview import server configuration profile on a network share. 
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2019, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to preview server configuration profile (SCP) on a supported network share")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ImportSystemConfigurationNetworkSharePreviewREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --filename SCP_export_R740, this example is going to preview SCP file on NFS share. \nImportSystemConfigurationNetworkSharePreviewREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.140 --sharetype CIFS --sharename cifs_share_vm --filename R740_scp_file --username administrator --password password, this example is going to preview SCP file on the CIFS share.')
parser.add_argument('-st', help='Pass in \"y\" to get supported share types for your iDRAC firmware version', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. If needed, use argument -st to get supported values for your iDRAC firmware version', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--filename', help='Pass in the filename of the SCP file which is on the network share you are using', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Disabled and Enabled. This argument is only required if using HTTPS for share type. If you don\'t pass in this argument when using HTTPS, default iDRAC setting is Enabled', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def get_sharetypes():
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    print("\n- ImportSystemConfiguration supported share types for iDRAC %s\n" % idrac_ip)
    if u'OemManager.v1_0_0#OemManager.ImportSystemConfiguration' in data[u'Actions'][u'Oem']:
        share_types = data[u'Actions'][u'Oem'][u'OemManager.v1_0_0#OemManager.ImportSystemConfiguration'][u'ShareParameters'][u'ShareType@Redfish.AllowableValues']
    else:
        share_types = data[u'Actions'][u'Oem'][u'OemManager.v1_1_0#OemManager.ImportSystemConfiguration'][u'ShareParameters'][u'ShareType@Redfish.AllowableValues']
    for i in share_types:
        if i == "LOCAL":
            pass
        else:
            print(i)
    
def import_server_configuration_profile_preview():
    global job_id
    method = "ImportSystemConfigurationPreview"
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfigurationPreview' % idrac_ip
    payload = {"ShareParameters":{"Target":"ALL"}}
    if args["ipaddress"]:
        payload["ShareParameters"]["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareParameters"]["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareParameters"]["ShareName"] = args["sharename"]
    if args["filename"]:
        payload["ShareParameters"]["FileName"] = args["filename"]
    if args["username"]:
        payload["ShareParameters"]["UserName"] = args["username"]
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
    d=str(response.__dict__)

    try:
        z=re.search("JID_.+?,",d).group()
    except:
        print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit()

    job_id=re.sub("[,']","",z)
    if response.status_code != 202:
        print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code)   
        sys.exit()
    else:
        print("\n- Job ID \"%s\" successfully created for %s method\n" % (job_id, method)) 

    response_output=response.__dict__
    job_id=response_output["headers"]["Location"]
    job_id=re.search("JID_.+",job_id).group()


    
def loop_job_status():
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        message_string=data[u"Messages"]
        final_message_string=str(message_string)
        current_time=(datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            pass
            time.sleep(3)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string or "not compliant" in final_message_string or "Unable to complete" in final_message_string or "The system could not be shut down" in final_message_string or "timed out" in final_message_string:
            print("\n- FAIL, detailed job message is: %s" % data[u"Messages"])
            sys.exit()
        elif "No reboot Server" in final_message_string:
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
            sys.exit()
        elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully previewed" in final_message_string or data[u"TaskState"] == "Completed":
            print("- PASS, job ID %s successfully marked completed\n" % job_id)
            print("\n- Detailed job results for job ID %s\n" % job_id)
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            print("\n- Config results for job ID %s\n" % job_id)
            for i in data['Messages']:
                for ii in i.items():
                    print("%s: %s" % (ii[0], ii[1]))
            sys.exit()
        elif "No changes" in final_message_string or "No configuration changes" in final_message_string:
            print("- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            print("- Job not marked completed, current status is: %s" % data[u"TaskState"])
            print("- Message: %s\n" % message_string[0][u"Message"])
            time.sleep(1)
            continue
        

if __name__ == "__main__":
    if args["st"]:
        get_sharetypes()
    else:
        import_server_configuration_profile_preview()
        loop_job_status()
        

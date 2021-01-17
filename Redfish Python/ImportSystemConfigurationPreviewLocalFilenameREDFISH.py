#
# ImportSystemConfigurationPreviewLocalFilenameREDFISH. Python script using Redfish API to preview a local system configuration file. 
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2018, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import requests, json, re, sys, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to preview the a local import server configuration profile (SCP) file. This is recommended to execute first before importing the SCP file. Preview will check for any errors and if no errors detected, give you a timestamp of how long it will take to apply the configuration changes.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ImportSystemConfigurationPreviewLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -p calvin -f 2018-11-26_14462_export.xml, this example will preview the local SCP file')
parser.add_argument('-f', help='Pass in Server Configuration Profile filename', required=True)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
filename=args["f"]

response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
data = response.json()
if response.status_code == 401:
    print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
    sys.exit()
else:
    pass
        
try:
    file_open=open(filename,"r")
except:
    print("\n-FAIL, \"%s\" file doesn't exist" % filename)
    sys.exit()
    
url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfigurationPreview' % idrac_ip 

# Code needed to modify the XML to one string to pass in for POST command
modify_xml = file_open.read()
modify_xml = re.sub(" \n ","",modify_xml)
modify_xml = re.sub(" \n","",modify_xml)
xml_string=re.sub("   ","",modify_xml)
file_open.close()

payload = {"ImportBuffer":"","ShareParameters":{"Target":"ALL"}}


payload["ImportBuffer"]=xml_string
headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))

dict_response = str(response.__dict__)

try:
    job_id_search = re.search("JID_.+?,",dict_response).group()
except:
    print("\n- FAIL: status code %s returned" % response.status_code)
    print("- Detailed error information: %s" % dict_response)
    sys.exit()

job_id=re.sub("[,']","",job_id_search)
if response.status_code != 202:
    print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code )  
    sys.exit()
else:
    print("\n- %s successfully created for ImportSystemConfigurationPreview method\n" % (job_id) )

response_output=response.__dict__
job_id=response_output["headers"]["Location"]
job_id=re.search("JID_.+",job_id).group()
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
        


    






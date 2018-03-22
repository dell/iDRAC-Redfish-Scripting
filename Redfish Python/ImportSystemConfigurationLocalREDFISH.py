#
# ImportSystemConfigurationLocalREDFISH. Python script using Redfish API to import system configuration attributes locally from the python script. Using ImportBuffer parameter, pass in the correct open, closed tags along with FQDDs, attributes in XML format. Use payload dictionary example below for the correct format.
#
# NOTE: Local import is recommended to use if setting one or few attributes. If you're setting a large amount of attributes, use import file from a network share or import file locally script.
#
# NOTE: Before executing the script, modify the payload dictionary with supported parameters. For payload dictionary supported parameters, refer to schema "https://'iDRAC IP'/redfish/v1/Managers/iDRAC.Embedded.1/"
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to import the host server configuration profile locally.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
    
url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip

# Make sure to modify this payload dictionary first before you execute the script.
 
payload = {"ShutdownType":"Forced","ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"Telnet.1#Enable\">Disabled</Attribute></Component></SystemConfiguration>","ShareParameters":{"Target":"All"}}

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
    print("\n- %s successfully created for ImportSystemConfiguration method\n" % (job_id))

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
    if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string:
        print("\n- FAIL, detailed job message is: %s" % data[u"Messages"])
        sys.exit()
    elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully imported" in final_message_string:
        print("- Job ID = "+data[u"Id"])
        print("- Name = "+data[u"Name"])
        try:
            print("- Message = "+message_string[0][u"Message"])
        except:
            print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
        print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
        sys.exit()
    elif "No reboot Server" in final_message_string:
        try:
            print("- Message = "+message_string[0][u"Message"])
        except:
            print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
        sys.exit()
    elif "No changes" in final_message_string:
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
        
    



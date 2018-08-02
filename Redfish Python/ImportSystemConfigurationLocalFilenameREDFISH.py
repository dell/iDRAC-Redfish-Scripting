#
# ImportSystemConfigurationLocalFilenameREDFISH. Python script using Redfish API to import system configuration profile attributes locally from a configuration file.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to import the host server configuration profile locally from a configuration file.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-t', help='Pass in Target value to set component attributes. You can pass in \"ALL" to set all component attributes or pass in a specific component to set only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=True)
parser.add_argument('-s', help='Pass in ShutdownType value. Supported values are Graceful, Forced and NoReboot. If you don\'t use this optional parameter, default value is Graceful. NOTE: If you pass in NoReboot value, configuration changes will not be applied until the next server manual reboot.', required=False)
parser.add_argument('-f', help='Pass in Server Configuration Profile filename', required=True)
parser.add_argument('-e', help='Pass in end HostPowerState value. Supported values are On and Off. If you don\'t use this optional parameter, default value is On', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
filename=args["f"]

try:
    f=open(filename,"r")
except:
    print("\n-FAIL, \"%s\" file doesn't exist" % filename)
    sys.exit()
    
url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip

# Code needed to modify the XML to one string to pass in for POST command
z=f.read()
z=re.sub(" \n ","",z)
z=re.sub(" \n","",z)
xml_string=re.sub("   ","",z)
f.close()

payload = {"ImportBuffer":"","ShareParameters":{"Target":args["t"]}}
if args["s"]:
    payload["ShutdownType"] = args["s"]
if args["p"]:
    payload["HostPowerState"] = args["e"]

payload["ImportBuffer"]=xml_string
headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=('root','calvin'))

#print '\n- Response status code is: %s' % response.status_code


d=str(response.__dict__)

try:
    z=re.search("JID_.+?,",d).group()
except:
    print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
    sys.exit()

job_id=re.sub("[,']","",z)
if response.status_code != 202:
    print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code )  
    sys.exit()
else:
    print("\n- %s successfully created for ImportSystemConfiguration method\n" % (job_id) )

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
    if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string or "not compliant" in final_message_string or "Unable to complete" in final_message_string or "The system could not be shut down" in final_message_string:
        print("\n- FAIL, detailed job message is: %s" % data[u"Messages"])
        sys.exit()
    elif "No reboot Server" in final_message_string:
        try:
            print("- Message = "+message_string[0][u"Message"])
        except:
            print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
        sys.exit()
    elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully imported" in final_message_string:
        print("- PASS, job ID %s successfully marked completed\n" % job_id)
        print("\n- Detailed jb results for job ID %s\n" % job_id)
        for i in data['Oem']['Dell'].items():
            print("%s: %s" % (i[0], i[1]))
        print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
        print("\n- Config results for job ID %s\n" % job_id)
        for i in data['Messages']:
            for ii in i.items():
                if ii[0] == "Oem":
                    for iii in ii[1]['Dell'].items():
                        if iii[0] == 'NewValue':
                            print("%s: %s" % (iii[0], iii[1]))
                            print("\n")
                        else:
                            print("%s: %s" % (iii[0], iii[1]))
                else:
                    pass

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
        


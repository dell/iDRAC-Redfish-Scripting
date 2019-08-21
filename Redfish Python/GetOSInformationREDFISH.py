#
# GetOSInformationREDFISH. Python script using Redfish API with OEM extension to get OS information using Server Configuration Profile feature
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get OS information using OEM Server Configuration Profile (SCP) feature.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
payload = {"ExportFormat":"XML","IncludeInExport":"IncludeReadOnly","ShareParameters":{"Target":"System"}}


headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))

if response.status_code != 202:
    print("- FAIL, status code not 202, code is: %s" % response.status_code)
    print("- Error details: %s" % response.__dict__)
    sys.exit()
else:
    pass

response_output=response.__dict__
job_id=response_output["headers"]["Location"]

try:
    job_id=re.search("JID_.+",job_id).group()
except:
    print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
    sys.exit()

print("\n- WARNING, getting Operation System information for iDRAC IP %s using Server Configuration Profile feature" % idrac_ip)
start_time=datetime.now()

while True:
    current_time=(datetime.now()-start_time)
    req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    d=req.__dict__
    if "<SystemConfiguration Model" in str(d):
        print("\n- PASS, Operation System Information for iDRAC %s -\n" % idrac_ip)
        zz=re.search("<SystemConfiguration.+</SystemConfiguration>",str(d)).group()
        z=re.findall("ServerOS.+?->",str(d))
        for i in z:
            i=i.replace("</Attribute> -->","")
            print(i.replace(">"," = "))
        break
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        
        data = req.json()
        print("- WARNING, final detailed job status results for job ID %s -\n" % job_id)
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))
        print("\n Exported attributes also saved in file: %s" % filename)
        sys.exit()
    else:
        pass
        
    statusCode = req.status_code
    data = req.json()
    try:
        message_string=data[u"Messages"]
    except:
        print(statusCode)
        print(data)
        sys.exit()
    current_time=(datetime.now()-start_time)

    if statusCode == 202 or statusCode == 200:
        time.sleep(1)
        pass
    else:
        print("Execute job ID command failed, error code is: %s" % statusCode)
        sys.exit()
    if str(current_time)[0:7] >= "0:10:00":
        print("\n-FAIL, Timeout of 10 minutes has been reached before marking the job completed.")
        sys.exit()
    else:
        continue


       

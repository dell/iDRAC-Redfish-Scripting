#
# ExportServerConfigurationLocalREDFISH. Python script using Redfish API to export the system configuration locally. By default, POST command print all attributes to the screen. This script will also capture these attributes into a file.
#
# NOTE: Before executing the script, modify the payload dictionary with supported parameters. For payload dictionary supported parameters, refer to schema "https://'iDRAC IP'/redfish/v1/Managers/iDRAC.Embedded.1/"
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

import requests, json, sys, re, time, warnings

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("-FAIL, you must pass in script name along with iDRAC IP/iDRAC username/iDRAC password")
    sys.exit()

url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration' % idrac_ip
payload = {"ExportFormat":"XML","ShareParameters":{"Target":"LifecycleController"}}
headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))

if response.status_code != 202:
    print("- FAIL, status code not 202\n, code is: %s" % response.status_code)
    print("- Error details: %s" % response.__dict__)
    sys.exit()
else:
    print("\n- Job ID successfully created for ExportSystemConfiguration method\n") 

response_output=response.__dict__
job_id=response_output["headers"]["Location"]

try:
    job_id=re.search("JID_.+",job_id).group()
except:
    print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
    sys.exit()

start_time=datetime.now()

while True:
    current_time=(datetime.now()-start_time)
    req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    d=req.__dict__
    if "<SystemConfiguration Model" in str(d):
        print("\n- Export locally successfully passed. Attributes exported:\n")
        zz=re.search("<SystemConfiguration.+</SystemConfiguration>",str(d)).group()

        #Below code is needed to parse the string to set up in pretty XML format
        q=zz.replace("\\n"," ")
        q=q.replace("<!--  ","<!--")
        q=q.replace(" -->","-->")
        del_attribute='<Attribute Name="SerialRedirection.1#QuitKey">^\\\\</Attribute>'
        q=q.replace(del_attribute,"")
        l=q.split("> ")
        export_xml=[]
        for i in l:
            x=i+">"
            export_xml.append(x)
        export_xml[-1]="</SystemConfiguration>"
        d=datetime.now()
        filename="%s-%s-%s_%s%s%s_export.xml"% (d.year,d.month,d.day,d.hour,d.minute,d.second)
        f=open(filename,"w")
        for i in export_xml:
            f.writelines("%s \n" % i)
        f.close()
        for i in export_xml:
            print(i)

        print("\n")
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        data = req.json()
        message_string=data[u"Messages"]
        print("\n Job ID = "+data[u"Id"])
        print(" Name = "+data[u"Name"])
        print(" Message = "+message_string[0][u"Message"])
        print(" JobStatus = "+data[u"TaskState"])
        print("\n %s completed in: %s" % (job_id, str(current_time)[0:7]))
        print("\n Exported attributes also saved in file: %s" % filename)
        sys.exit()
    else:
        pass
        
    statusCode = req.status_code
    data = req.json()
    message_string=data[u"Messages"]
    current_time=(datetime.now()-start_time)

    if statusCode == 202 or statusCode == 200:
        print("\n- Execute job ID command passed, checking job status...\n")
        time.sleep(1)
    else:
        print("Execute job ID command failed, error code is: %s" % statusCode)
        sys.exit()
    if str(current_time)[0:7] >= "0:10:00":
        print("\n-FAIL, Timeout of 10 minutes has been reached before marking the job completed.")
        sys.exit()

    else:
        print("- Job not marked completed, current status is: %s" % data[u"TaskState"])
        print("- Message: %s\n" % message_string[0][u"Message"])
        time.sleep(1)
        continue


       

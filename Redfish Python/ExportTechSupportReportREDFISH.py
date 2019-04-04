#
# ExportTechSupportReportREDFISH. Python script using Redfish API with OEM extension to export tech support report (known as Support Assist now) to a network share
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export tech support report (known as Support Assist now) to a network share")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportTechSupportReportREDFISH.py -ip 192.168.0.120 -u root -p calvin --ipaddress 192.168.0.130 --sharetype CIFS --sharename cifs_share_vm --dataselectorarrayin 3 --scheduledstarttime TIME_NOW --username administrator --password password, this example will only export TTY logs to CIFS share')
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS.', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--scheduledstarttime', help='Start time for the job execution in format: yyyymmddhhmmss. Pass in value of "TIME_NOW" to start the job immediately', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--dataselectorarrayin', help='Pass in a value for the type of data you want to collect. Supported values are: pass in 0 for \"HWData\", pass in 1 for "OSAppDataWithoutPII\", pass in 2 for \"OSAppData\", pass in 3 for \"TTYLogs\". Note: If you do not pass in this argument, default settings will collect HWData. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values (Example: 0,3)', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def export_tech_support_report():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportTechSupportReport' % (idrac_ip)
    method = "ExportTechSupportReport"
    
        
    headers = {'content-type': 'application/json'}
    payload={}
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
    if args["dataselectorarrayin"]:
        data_selector_values=[]
        if "," in args["dataselectorarrayin"]:
            data_selector = [i for i in args["dataselectorarrayin"].split(",")]
            if "0" in data_selector:
                data_selector_values.append("HWData")
            if "1" in data_selector:
                data_selector_values.append("OSAppDataWithoutPII")
            if "2" in data_selector:
                data_selector_values.append("OSAppData")
            if "3" in data_selector:
                data_selector_values.append("TTYLogs")
            payload["DataSelectorArrayIn"] = data_selector_values
        else:
            if args["dataselectorarrayin"] == "0":
                data_selector_values.append("HWData")
            if args["dataselectorarrayin"] == "1":
                data_selector_values.append("OSAppDataWithoutPII")
            if args["dataselectorarrayin"] == "2":
                data_selector_values.append("OSAppData")
            if args["dataselectorarrayin"] == "3":
                data_selector_values.append("TTYLogs")
            payload["DataSelectorArrayIn"] = data_selector_values
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
        if i[0] == "Password":
            print("Password: ********")
        else:
            print("%s: %s" % (i[0],i[1]))
    
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
    


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
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or data[u'JobState'] == "Failed" or "error" in data[u'Message'] or "Error" in data[u'Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            if data[u'Message'] == "The SupportAssist Collection and Transmission Operation is completed successfully.":
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
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(5)
            

    

if __name__ == "__main__":
    check_supported_idrac_version()
    export_tech_support_report()
    loop_job_status()
    
    
        
            
        
        

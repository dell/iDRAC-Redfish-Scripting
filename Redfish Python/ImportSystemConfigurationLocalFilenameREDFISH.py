#
# ImportSystemConfigurationLocalFilenameREDFISH. Python script using Redfish API to import system configuration profile attributes locally from a configuration file.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 14.0
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
parser.add_argument('-np', help='Pass in new iDRAC user password that gets set during SCP import. This will be required to continue to query the job status.', required=False)
parser.add_argument('script_examples',action="store_true",help='ImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -p calvin -t ALL --filename SCP_export_R740, this example is going to import SCP file and apply all attribute changes for all components. \nImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -p calvin -t BIOS --filename R740_scp_file -s Forced, this example is going to only apply BIOS changes from the SCP file along with forcing a server power reboot. ImportSystemConfigurationLocalFilenameREDFISH.py -ip 192.168.0.120 -u root -t IDRAC -f 2020-8-5_135318_export.xml -p calvin -np Test1234#, this example uses SCP import to change root user password and will leverage the new user password to continue to query the job status until marked completed')
parser.add_argument('-t', help='Pass in Target value to set component attributes. You can pass in \"ALL" to set all component attributes or pass in a specific component to set only those attributes. Supported values are: ALL, System, BIOS, IDRAC, NIC, FC, LifecycleController, RAID.', required=True)
parser.add_argument('-s', help='Pass in ShutdownType value. Supported values are Graceful, Forced and NoReboot. If you don\'t use this optional parameter, default value is Graceful. NOTE: If you pass in NoReboot value, configuration changes will not be applied until the next server manual reboot.', required=False)
parser.add_argument('-f', help='Pass in Server Configuration Profile filename', required=True)
parser.add_argument('-e', help='Pass in end HostPowerState value. Supported values are On and Off. If you don\'t use this optional parameter, default value is On', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
filename=args["f"]

response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
if response.status_code == 401:
    print("\n- WARNING, status code 401 detected, check iDRAC username / password credentials")
    sys.exit()
else:
    pass

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
if args["e"]:
    payload["HostPowerState"] = args["e"]

payload["ImportBuffer"]=xml_string
headers = {'content-type': 'application/json'}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, idrac_password))

#print '\n- Response status code is: %s' % response.status_code


d=str(response.__dict__)

try:
    z=re.search("JID_.+?,",d).group()
except:
    print("\n- FAIL: status code %s returned" % response.status_code)
    print("- Detailed error information: %s" % d)
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
    count = 1
    while True:
        if count == 5:
            print("- FAIL, 5 attempts at getting job status failed, script will exit")
            sys.exit()
        try:
            req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
            break
        except requests.ConnectionError as error_message:
            print("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
            time.sleep(10)
            print("- WARNING, script will now attempt to get job status again")
            count+=1
            continue
    statusCode = req.status_code
    if statusCode == 401 and args["np"]:
        print("- WARNING, status code 401 and argument -np detected. Script will now query job status using iDRAC user \"%s\" new password set by SCP import" % idrac_username)
        idrac_password = args["np"]
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        if req.status_code == 401:
            print("- WARNING, new password passed in for argument -np still failed with status code 401 for idrac user \"%s\", unable to check job status" % idrac_username)
            sys.exit()
        else:
            continue
    elif statusCode == 401:
        print("- WARNING, status code 401 still detected for iDRAC user \"%s\". Check SCP file to see if iDRAC user \"%s\" password was changed for import" % (idrac_username, idrac_username))
        sys.exit()
    else:
        pass
    data = req.json()
    current_time=(datetime.now()-start_time)
    if statusCode == 202 or statusCode == 200:
        pass
        time.sleep(3)
    else:
        print("Query job ID command failed, error code is: %s" % statusCode)
        sys.exit()
    if "failed" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Not one" in data['Oem']['Dell']['Message'] or "not compliant" in data['Oem']['Dell']['Message'] or "Unable" in data['Oem']['Dell']['Message'] or "The system could not be shut down" in data['Oem']['Dell']['Message'] or "No device configuration" in data['Oem']['Dell']['Message'] or "timed out" in data['Oem']['Dell']['Message']:
        print("- FAIL, Job ID %s marked as %s but detected issue(s). See detailed job results below for more information on failure\n" % (job_id, data['Oem']['Dell']['JobState']))
        print("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
        try:
            for i in data["Messages"]:
                for ii in i.items():
                    if ii[0] == "Oem":
                        for iii in ii[1]["Dell"].items():
                            print("%s: %s" % (iii[0], iii[1]))
                    else:
                        if ii[0] == "Severity":
                            if ii[1] == "Critical":
                                print("%s: %s" % (ii[0], ii[1]))
                                print("Status: Failure")
                            elif ii[1] == "OK":
                                print("%s: %s" % (ii[0], ii[1]))
                                print("Status: Success")
                            else:
                                print("%s: %s" % (ii[0], ii[1]))
                                
                        else:
                            print("%s: %s" % (ii[0], ii[1]))
                print("\n")
        except:
            print("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
                
            print("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
        sys.exit()
            
    elif "No reboot Server" in data['Oem']['Dell']['Message']:
        print("- PASS, job ID %s successfully marked completed. NoReboot value detected and config changes will not be applied until next manual server reboot\n" % job_id)
        print("\n- Detailed job results for job ID %s\n" % job_id)
        for i in data['Oem']['Dell'].items():
            print("%s: %s" % (i[0], i[1]))
        sys.exit()
    elif "Successfully imported" in data['Oem']['Dell']['Message'] or "completed with errors" in data['Oem']['Dell']['Message'] or "Successfully imported" in data['Oem']['Dell']['Message']:
        print("- PASS, job ID %s successfully marked completed\n" % job_id)
        print("- Detailed configuration changes and job results for \"%s\"\n" % job_id)
        try:
            for i in data["Messages"]:
                for ii in i.items():
                    if ii[0] == "Oem":
                        for iii in ii[1]["Dell"].items():
                            print("%s: %s" % (iii[0], iii[1]))
                    else:
                        if ii[0] == "Severity":
                            if ii[1] == "Critical":
                                print("%s: %s" % (ii[0], ii[1]))
                                print("Status: Failure")
                            elif ii[1] == "OK":
                                print("%s: %s" % (ii[0], ii[1]))
                                print("Status: Success")
                            else:
                                print("%s: %s" % (ii[0], ii[1]))
                                
                        else:
                            print("%s: %s" % (ii[0], ii[1]))
                print("\n")
        except:
            print("- FAIL, unable to get configuration results for job ID, returning only final job results\n")
            for i in data['Oem']['Dell'].items():
                print("%s: %s" % (i[0], i[1]))
            
        print("- %s completed in: %s" % (job_id, str(current_time)[0:7]))
        sys.exit()
            
    elif "No changes" in data['Oem']['Dell']['Message'] or "No configuration changes" in data['Oem']['Dell']['Message']:
        print("\n- PASS, job ID %s marked completed\n" % job_id)
        print("- Detailed job results for job ID %s\n" % job_id)
        for i in data['Oem']['Dell'].items():
            print("%s: %s" % (i[0], i[1]))
        sys.exit()
    else:
        print("- INFO, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Oem']['Dell']['Message'],data['Oem']['Dell']['PercentComplete']))
        time.sleep(3)
        continue
    


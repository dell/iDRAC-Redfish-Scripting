#
# SupportAssistCollectionLocalREDFISH. Python script using Redfish API with OEM extension to perform Support Assist operations.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
#
# Copyright (c) 2020, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse, webbrowser

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform Support Assist(SA) operations. These include export SA report locally, accept End User License Agreement(EULA) or register SA for iDRAC.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin -s y, this example will get SA EULA current status. SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example will accept SA EULA. SupportAssistCollectionLocalREDFISH.py -ip 192.168.0.120 -u root -p calvin -l y -d 0,3, this example will export SA logs locally. The SA log will only include debug and TTY logs')
parser.add_argument('-l', help='Pass in \"y\" to export support assist collection locally. You must also use agrument -d with -l. Note, once the job is marked completed, you will be prompted to download the SA zip uisng your default browser. Select \"y\" to download or \"n\" to not download.',required=False)
parser.add_argument('-a', help='Pass in \"y\" to accept support assist end user license agreement (EULA)', required=False)
parser.add_argument('-s', help='Pass in \"y\" to get support assist end user license agreement (EULA)', required=False)
parser.add_argument('-r', help='Pass in \"y\" to register Support Assist for iDRAC. NOTE: You must also pass in city, company name, country, email, first name, last name, phone number, street, state and zip arguments to register. NOTE: ISM must be installed and running on the operating system before you register SA.', required=False)
parser.add_argument('--city', help='Pass in city name to register Support Assist', required=False)
parser.add_argument('--companyname', help='Pass in company name to register Support Assist', required=False)
parser.add_argument('--country', help='Pass in country to register Support Assist', required=False)
parser.add_argument('--email', help='Pass in email to register Support Assist', required=False)
parser.add_argument('--firstname', help='Pass in firstname to register Support Assist', required=False)
parser.add_argument('--lastname', help='Pass in lastname to register Support Assist', required=False)
parser.add_argument('--phonenumber', help='Pass in phone number to register Support Assist', required=False)
parser.add_argument('--street', help='Pass in street name to register Support Assist', required=False)
parser.add_argument('--state', help='Pass in state to register Support Assist', required=False)
parser.add_argument('--zip', help='Pass in zipcode to register Support Assist', required=False)
parser.add_argument('-d', help='Pass in a value for the type of data you want to collect for Support Assist collection. Supported values are: pass in 0 for \"DebugLogs\", pass in 1 for "HWData\", pass in 2 for \"OSAppData\", pass in 3 for \"TTYLogs\", pass in 4 for \"TelemetryReports\". Note: If you do not pass in this argument, default settings will collect HWData. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values (Example: 0,3)', required=False)




args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "SupportAssistCollection" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def support_assist_collection():
    global job_id
    global start_time
    start_time=datetime.now()
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection' % (idrac_ip)
    method = "SupportAssistCollection"
    payload = {"ShareType":"Local"}
    #payload = {}
    if args["d"]:
        data_selector_values=[]
        if "," in args["d"]:
            data_selector = [i for i in args["d"].split(",")]
            if "0" in data_selector:
                data_selector_values.append("DebugLogs")
            if "1" in data_selector:
                data_selector_values.append("HWData")
            if "2" in data_selector:
                data_selector_values.append("OSAppData")
            if "3" in data_selector:
                data_selector_values.append("TTYLogs")
            if "4" in data_selector:
                data_selector_values.append("TelemetryReports")
            payload["DataSelectorArrayIn"] = data_selector_values
        else:
            if args["d"] == "0":
                data_selector_values.append("DebugLogs")
            if args["d"] == "1":
                data_selector_values.append("HWData")
            if args["d"] == "2":
                data_selector_values.append("OSAppData")
            if args["d"] == "3":
                data_selector_values.append("TTYLogs")
            if args["d"] == "4":
                data_selector_values.append("TelemetryReports")
            payload["DataSelectorArrayIn"] = data_selector_values
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
        if i[0] == "Password":
            print("Password: ********")
        else:
            print("%s: %s" % (i[0],i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 201 or response.status_code == 202:
        pass
    else:
        data = response.json()
        print("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))


def support_assist_accept_EULA():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistAcceptEULA' % (idrac_ip)
    method = "SupportAssistAcceptEULA"
    payload = {}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS, %s method passed and End User License Agreement (EULA) has been accepted" % method)
    else:
        data = response.json()
        print("\n- FAIL, status code %s returned, detailed error information:\n %s" % (response.status_code, data))
        sys.exit()

def support_assist_get_EULA_status():
    print("\n- Current Support Assist End User License Agreement Information -\n")
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (idrac_ip)
    method = "SupportAssistGetEULAStatus"
    payload = {}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data.items():
        if "ExtendedInfo" in i[0]:
            pass
        else:
            print("%s: %s" % (i[0],i[1]))


def support_assist_register():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{"OS-BMC.1.AdminState":"Enabled"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    data = response.json()
    if statusCode == 200 or statusCode == 202:
        pass
    else:
        print("\n- FAIL, Command failed for action %s, status code is: %s\n" % (args["s"].upper(),statusCode))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistRegister' % (idrac_ip)
    method = "SupportAssistRegister"
    payload = {"City": args["city"], "CompanyName": args["companyname"], "Country":args["country"],"PrimaryEmail":args["email"],"PrimaryFirstName":args["firstname"],"PrimaryLastName":args["lastname"], "PrimaryPhoneNumber":args["phonenumber"], "State":args["state"], "Street1": args["street"],"Zip":args["zip"]}
    print("\n- Parameters passed in for SupportAssistRegister action -\n")
    for i in payload.items():
        print ("%s: %s" % (i[0], i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS, SupportAssistRegister action passed, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, SupportAssistRegister action failed, status code %s returned. Detailed error results:\n" % response.status_code)
        data = response.__dict__
        print(data["_content"])
        sys.exit()
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus' % (idrac_ip)
    method = "SupportAssistGetEULAStatus"
    payload = {}
    headers = {'content-type': 'application/json'}
    print("- WARNING, validating if Support Assist is registered for iDRAC")
    time.sleep(15)
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if data["IsRegistered"] == "Registered":
        print("\n- PASS, Support Assist verified as registered")
    else:
        print("\n- FAIL, Support Assist not registered, current status is: %s" % data["IsRegistered"])
        sys.exit()

    

def loop_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            data = req.json()
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        try:
            if req.headers['Location'] == "/redfish/v1/Dell/sacollect.zip" or req.headers['Location'] == "/redfish/v1/Oem/Dell/sacollect.zip":
                print("- PASS, job ID successfully marked completed. Support Assist logs filename: \"%s\"" % req.headers['Location'].split("/")[-1])
                python_version = sys.version_info
                while True:
                    if python_version.major <= 2:
                        request = raw_input("\n* Would you like to open browser session to download Support Assist file? Type \"y\" to download or \"n\" to not download: ")
                    elif python_version.major >= 3:
                        request = input("\n* Would you like to open browser session to download Support Assist file? Type \"y\" to download or \"n\" to not download: ")
                    else:
                        print("- FAIL, unable to get current python version, manually run GET on URI \"%s\" to get Support Assist logs capture" % req.headers['Location'])
                        sys.exit()
                    if str(request) == "y":
                        webbrowser.open('https://%s%s' % (idrac_ip, req.headers['Location']))
                        print("\n- WARNING, check you default browser session for downloaded Support Assist logs")
                        return
                    elif str(request) == "n":
                        sys.exit()
                    else:
                        print("- FAIL, incorrect value passed in for request, try again")
                        continue
        except:
            if str(current_time)[0:7] >= "0:30:00":
                print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
                sys.exit()
            elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "error" in data['Message'] or "Error" in data['Message']:
                print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
                sys.exit()
            elif data['JobState'] == "Completed" or "complete" in data['Message'] or "Complete" in data['Message']:
                if "local path" in data['Message']:
                    print("\n--- PASS, Final Detailed Job Status Results ---\n")
                else:
                    print("- WARNING, unable to detect final job status message. Manually run GET on URI \"%s\" using browser to see if SA zip collection is available to download." % req.headers['Location'])
                    sys.exit()
                for i in data.items():
                    if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                        pass
                    else:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                print("- INFO, Job status not marked completed, polling job status again, execution time: %s" % str(current_time)[0:7])
                time.sleep(30)
            

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["l"] and args["d"]:
        support_assist_collection()
        loop_job_status()
    elif args["a"]:
        support_assist_accept_EULA()
    elif args["s"]:
        support_assist_get_EULA_status()
    elif args["r"] and args["city"] and args["companyname"] and args["country"] and args["email"] and args["firstname"] and args["lastname"] and args["phonenumber"] and args["state"] and args["street"] and args["zip"]:
        support_assist_register()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")

    
    
        
            
        
        

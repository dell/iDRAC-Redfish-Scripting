#
# SupportAssistCollectionNetworkShareREDFISH. Python script using Redfish API with OEM extension to export Support Assist collection to a network share
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


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either export support assist (SA) collection to a network share or get/accept/register End User license agreement (EULA). NOTE: the SA file copied to your network share will be in ZIP format using your server service tag in the name. Example of SA report file name \"TSR20200122131132_M538C3S.zip\"")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin -s y, this example will get SA EULA current status. SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example will accept SA EULA. SupportAssistCollectionNetworkShareREDFISH.py -ip 192.168.0.120 -u root -p calvin -e y --ipaddress 192.168.0.130 --sharetype HTTP --sharename http_share --dataselectorarrayin 3, this example wil export SA collection for storage TTYlogs only to HTTP share')
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
parser.add_argument('-e', help='Export Support Assist collection to network share, pass in \"y\". NOTE: Make sure you also use arguments ipaddress, sharetype, sharename and dataselectorarrayin for export to network share. If using CIFS, you need to also use username and password arguments.', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS, FTP, TFTP', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--dataselectorarrayin', help='Pass in a value for the type of data you want to collect. Supported values are: pass in 0 for \"DebugLogs\", pass in 1 for "HWData\", pass in 2 for \"OSAppData\", pass in 3 for \"TTYLogs\", pass in 4 for \"TelemetryReports\". Note: If you do not pass in this argument, default settings will collect HWData. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values (Example: 0,3)', required=False)



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


def export_support_assist_colection_network_share():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection' % (idrac_ip)
    method = "SupportAssistCollection"
    
        
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
    if args["dataselectorarrayin"]:
        data_selector_values=[]
        if "," in args["dataselectorarrayin"]:
            data_selector = [i for i in args["dataselectorarrayin"].split(",")]
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
            if args["dataselectorarrayin"] == "0":
                data_selector_values.append("DebugLogs")
            if args["dataselectorarrayin"] == "1":
                data_selector_values.append("HWData")
            if args["dataselectorarrayin"] == "2":
                data_selector_values.append("OSAppData")
            if args["dataselectorarrayin"] == "3":
                data_selector_values.append("TTYLogs")
            if "4" in data_selector:
                data_selector_values.append("TelemetryReports")
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
    count_number = 0
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
        if str(current_time)[0:7] >= "1:00:00":
            print("\n- FAIL: Timeout of 1 hour has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "error" in data['Message'] or "Error" in data['Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif data['JobState'] == "Completed":
            if data['Message'] == "The SupportAssist Collection and Transmission Operation is completed successfully.":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                print("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            service_tag = data['Oem']['Dell']['DellSystem']['NodeID']
            print("\n- SA exported log file located on your network share should be in ZIP format with server service tag \"%s\" in the file name" % service_tag)
            break
        else:
            count_number_now = data['PercentComplete']
            if count_number_now > count_number:
                print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data['Message'],data['PercentComplete']))
                count_number = count_number_now
            else:
                continue
            

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["e"]:
        export_support_assist_colection_network_share()
        loop_job_status()
    elif args["a"]:
        support_assist_accept_EULA()
    elif args["s"]:
        support_assist_get_EULA_status()
    elif args["r"] and args["city"] and args["companyname"] and args["country"] and args["email"] and args["firstname"] and args["lastname"] and args["phonenumber"] and args["state"] and args["street"] and args["zip"]:
        support_assist_register()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    
    
        
            
        
        

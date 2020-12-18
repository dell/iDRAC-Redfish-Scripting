#
# RunDiagnosticsREDFISH. Python script using Redfish API with OEM extension to run remote diagnostics on the server.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to run remote diagnostics on the server.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin -r 2 -m 0, this example will perform forced server reboot and run express diagnostics. RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin -r 1 -m 2, this example will perform graceful without forced server reboot, run extended diagnostics. RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin -e 1, this example will export the DIAGs results locally using your default browser. RunDiagnosticsREDFISH.py -ip 192.168.0.120 -u root -p calvin -e 2 --ipaddress 192.168.0.130 --sharename /nfs --filename diags.log, this example will export DIAGs results to NFS share.')
parser.add_argument('-r', help='Pass in the reboot job type. Pass in \"0\" for GracefulRebootWithForcedShutdown, \"1\" for GracefulRebootWithoutForcedShutdown or \"2\" for Powercycle (forced)', required=False)
parser.add_argument('-m', help='Pass in the run mode type you want to execute for diags. Pass in \"0\" for Express only, \"1\" for Express and Extended or \"2\" for Extended only. Note: Run express diags, average completion time: 15-30 minutes. Run extended diags, average completion time: 3-5 hours.', required=False)
parser.add_argument('-e', help='Export diags results, pass in 1 for local, 2 for NFS, 3 for CIFS, 4 for HTTP or 5 for HTTPS. If using network share, you will need to also use IP address, sharename, sharetype, username, password arguments.', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharename', help='Pass in the network share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username password', required=False)
parser.add_argument('--filename', help='Pass in unique filename for the diags results', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)



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
        if "RunePSADiagnostics" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def export_diags():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportePSADiagnosticsResult' % (idrac_ip)
    method = "ExportePSADiagnosticsResult"
    headers = {'content-type': 'application/json'}
    payload = {}
    if args["e"] == "1":
        payload["ShareType"] = "Local"
    if args["e"] == "2":
        payload["ShareType"] = "NFS"
    if args["e"] == "3":
        payload["ShareType"] = "CIFS"
    if args["e"] == "4":
        payload["ShareType"] = "HTTP"
    if args["e"] == "5":
        payload["ShareType"] = "HTTPS"
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["filename"]:
            payload["FileName"] = args["filename"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertificateWarning"] = args["ignorecertwarning"]
        
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    if args["e"] == "1":
        if response.headers['Location'] == "/redfish/v1/Dell/diags.txt" or response.headers['Location'] == "/redfish/v1/Oem/Dell/diags.txt":
            #print("- PASS, job ID successfully marked completed. Support Assist logs filename: \"%s\"" % request.headers['Location'].split("/")[-1])
            python_version = sys.version_info
            while True:
                if python_version.major <= 2:
                    request = raw_input("\n- INFO, use browser session to view diags text file? Type \"y\" or \"n\": ")
                elif python_version.major >= 3:
                    request = input("\n- INFO, use browser session to view diags text file? Type \"y\" or \"n\": ")
                else:
                    print("- FAIL, unable to get current python version, manually run GET on URI \"%s\" to view diags text file" % response.headers['Location'])
                    sys.exit()
                if str(request) == "y":
                    webbrowser.open('https://%s%s' % (idrac_ip, response.headers['Location']))
                    print("\n- WARNING, check you default browser session to view diags text file.")
                    return
                elif str(request) == "n":
                    sys.exit()
                else:
                    print("- FAIL, incorrect value passed in for request, try again")
                    continue
    else:
        data = response.json()
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
            sys.exit()
        print("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
        loop_job_status()
        
    




def run_remote_diags():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.RunePSADiagnostics' % (idrac_ip)
    method = "RunePSADiagnostics"
    headers = {'content-type': 'application/json'}
    payload={}
        
    headers = {'content-type': 'application/json'}
    payload={}
    if args["r"]:
        if args["r"] == "0":
            payload["RebootJobType"] = "GracefulRebootWithForcedShutdown"
        elif args["r"] == "1":
            payload["RebootJobType"] = "GracefulRebootWithoutForcedShutdown"
        elif args["r"] == "2":
            payload["RebootJobType"] = "PowerCycle"
        else:
            print("- FAIL, invalid value entered for -r argument")
            sys.exit()
    if args["m"]:
        if args["m"] == "0":
            payload["RunMode"] = "Express"
        elif args["m"] == "1":
            payload["RunMode"] = "ExpressAndExtended"
        elif args["m"] == "2":
            payload["RunMode"] = "Extended"
        else:
            print("- FAIL, invalid value entered for -m argument")
            sys.exit()
    
    print("\n- INFO, arguments and values for %s method\n" % method)
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
    if args["e"]:
        pass
    else:
        print("- INFO, server will now automatically reboot and run remote diagnostics once POST completes. Script will check job status every 1 minute until marked completed\n")
        time.sleep(10)
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except requests.ConnectionError as error_message:
            if "Max retries exceeded with url" in str(error_message):
                print("- WARNING, max retries exceeded with URL error detected, retry GET command")
                time.sleep(10)
                continue
            else:
                print("- WARNING, GET command failed to get job status, script will exit")
                sys.exit()   
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        max_timeout = "10:00:00"
        if str(current_time)[0:7] >= max_timeout and len(str(current_time)[0:7]) == len(max_timeout):
            print("\n- FAIL: Timeout of 10 hours has been hit, script stopped. Check iDRAC LC logs or Job Queue to debug.\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed" or "Unable" in data['Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif data['JobState'] == "Completed":
            if data['Message'] == "Job completed successfully." or data['Message'] == "Successfully exported the ePSA Diagnostics results.":
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
            print("- INFO, job not marked completed, status running, execution time: %s" % str(current_time)[0:7])
            if args["e"]:
                continue
            else:
                time.sleep(60)
                continue
            

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["e"]:
        export_diags()
    elif args["m"] and args["r"]:
        run_remote_diags()
        loop_job_status()
    else:
        print("\n- FAIL, incorrect parameter(s) passed in or missing required parameters")
    
    
    
        
            
        
        

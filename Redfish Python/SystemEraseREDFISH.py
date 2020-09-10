#
# SystemEraseREDFISH. Python script using Redfish API with OEM extension to perform iDRAC System Erase feature.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to perform System Erase feature. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get supported component values which can be passed in for System Erase action. SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin -c DIAG,DrvPack, this example wil erase diag and driver pack, leave server in OFF state. SystemEraseREDFISH.py -ip 192.168.0.120 -u root -p calvin -c BIOS -e y, this example will reset BIOS to default settings and power back ON the server.')
parser.add_argument('-g', help='Get supported System Erase components, pass in \"y\"', required=False)
parser.add_argument('-c', help='Pass in the system erase component(s) you want to erase. If passing in multiple components, make sure to use comma separator. Example: BIOS,IDRAC,DIAG. NOTE: These values are case sensitive, make sure to pass in exact string values you get from -g argument.', required=False)
parser.add_argument('-e', help='Pass in \"y\" if you want the server to automatically power ON after system erase process is complete/iDRAC reboot. By default, once the system erase process is complete, server will be in OFF state, reboot the iDRAC and stay in OFF state.')

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
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- WARNING, iDRAC version detected does not support this feature")
        sys.exit()
    
    supported = "no"
    for i in data['Actions'].keys():
        if "SystemErase" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API or incorrect iDRAC user credentials passed in")
        sys.exit()
    else:
        pass

def get_components():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, GET command failed to get supported component values,status code %s returned" % response.status_code)
        sys.exit()
    print("\n- Supported component values for System Erase operation -\n")
    for i in data['Actions']['#DellLCService.SystemErase']['Component@Redfish.AllowableValues']:
        if i == "BIOS":
            print("BIOS: \"Reset BIOS to default configuration settings\"")
        elif i == "DIAG":
            print("DIAG: \"Delete only DIAG firmware image stored on iDRAC\"")
        elif i == "DrvPack":
            print("DrvPack: \"Delete only Driver Pack firmware image stored on iDRAC\"")
        elif i == "IDRAC":
            print("IDRAC: \"Reset iDRAC to default settings\"")
        elif i == "LCData":
            print("LCData: \"Delete Lifecycle Controller data(clears: Lifecycle logs, LC inventory, any rollback firmware packages stored on iDRAC)\"")
        elif i == "NonVolatileMemory":
            print("NonVolatileMemory: \"Erase NVDIMM devices\"")
        elif i == "OverwritePD":
            print("OverwritePD: \"Erase non ISE HDD devices\"")
        elif i == "CryptographicErasePD":
            print("CryptographicErasePD: \"Erase ISE/SED/NVMe devices\"")
        elif i == "PERCNVCache":
            print("PERCNVCache: \"Erase pinned cache on the PERC controller\"")
        elif i == "CryptographicErasePD":
            print("CryptographicErasePD: \"Erase ISE/SED/NVMe devices\"")
        elif i == "vFlash":
            print("vFlash: \"Erase iDRAC vFlash card\"")
        elif i == "AllApps":
            print("AllApps: \"Delete DIAG/Driver Pack firmware images and SupportAssist related non-volatile storage\"")
        else:
            print(i)


def system_erase():
    global job_id
    global method
    method = "SystemErase"
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SystemErase' % (idrac_ip)
    #url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService/Actions/DellLCService.SystemErase' % (idrac_ip)

        
    headers = {'content-type': 'application/json'}
    if "," in args["c"]:
        component_list =args["c"].split(",")
        payload={"Component":component_list}
    else:
        payload={"Component":[args["c"]]}
    print("\n- WARNING, component(s) selected for System Erase operation -\n")
    for i in payload["Component"]:
        print(i)
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
    print("- PASS, job ID %s successfuly created for %s method. Script will now loop polling job status until marked completed\n" % (job_id, method))
    

def loop_job_status():
    start_time=datetime.now()
    count_number = 0
    try:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    except:
        print("- WARNING, lost iDRAC network connection. Check the overall job queue for the job ID status")
        sys.exit()
    data = req.json()
    print("- WARNING, JobStatus not completed, current status: \"%s\"" % (data['Message']))
    start_job_status_message = data['Message']
    retry_count = 1
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except:
            if retry_count == 10:
                print("- WARNING, retry count of 10 has been reached to communicate with iDRAC, script will exit")
                sys.exit()
            else:
                print("- WARNING, lost iDRAC network connection, retry GET request after 10 second sleep delay")
                retry_count+=1
                time.sleep(15)
                continue
            
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            current_job_status = data['Message']
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
        data = req.json()
        new_job_status_message = data['Message']
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit()
        elif data['JobState'] == "Failed" or "Fail" in data['Message'] or "Unable" in data['Message'] or "Invalid" in data['Message'] or "fail" in data['Message'] or "Cannot" in data['Message'] or "cannot" in data['Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data['Message']))
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            print("\n- WARNING, server is in OFF state due to System Erase process completed, iDRAC will now reboot.")
            if args["e"] == "y":
                print("- WARNING, user selected to automatically power ON the server once iDRAC reboot is complete. Script will wait 6 minutes for iDRAC to come back up and attempt to power ON the server")
                time.sleep(360)
                count = 0
                while True:
                    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                    payload = {'ResetType': 'On'}
                    headers = {'content-type': 'application/json'}
                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                    statusCode = response.status_code
                    if count == 5:
                        print("- FAIL, 5 attempts at powering ON the server has failed, script will exit")
                        sys.exit()
                    if statusCode == 204:
                        print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
                        time.sleep(30)
                        if "BIOS" in args["c"]:
                            print("- WARNING, BIOS component selected. Server will power off one more time and automatically power back onto complete the process.")
                            count = 0
                            while True:
                                url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % idrac_ip
                                payload = {}
                                headers = {'content-type': 'application/json'}
                                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                                statusCode = response.status_code
                                data = response.json()
                                if statusCode == 200:
                                    pass
                                else:
                                    print("- FAIL, unable to get current server status, status code return is %s" % statusCode)
                                    print("- Detailed error message: %s" % data)
                                    sys.exit()
                                if data['ServerStatus'] == "PoweredOff":
                                    print("- PASS, verified server is in OFF state, executing power ON operation")
                                    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
                                    payload = {'ResetType': 'On'}
                                    headers = {'content-type': 'application/json'}
                                    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                                    statusCode = response.status_code
                                    if statusCode == 204:
                                        print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
                                        print("\n- PASS, script complete!")
                                        return
                                    else:
                                        print("- FAIL, unable to power ON server, status code return is %s" % statusCode)
                                        print("- Detailed error message: %s" % data)
                                        sys.exit()
                                elif count == 10:
                                    print("- WARNING, server still in POST/ON state after 10 attempts checking power state. Check the iDRAC Lifecycle logs, server to debug issue")
                                    sys.exit()
                                else:
                                    print("- WARNING, server still in POST/ON state, waiting for server to power down before executing power ON operation")
                                    time.sleep(60)
                                    count+=1
                                
                        else:
                            print("\n- PASS, script complete!")
                            return
                    else:
                        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
                        print("Extended Info Message: {0}".format(response.json()))
                        print("- WARNING, script will wait 1 minute and attempt power ON operation again")
                        time.sleep(60)
                        count +=1
                        continue
            else:
                if "BIOS" in args["c"]:
                    print("- WARNING, BIOS component selected. Manually power on the server for BIOS to complete reset to defaults. Server will power off one more time, process is complete.")
                    print("\n- PASS, script complete!")
                    return
                else:
                    print("\n- PASS, script complete!")
                    return
        else:
            if start_job_status_message != new_job_status_message:
                print("- WARNING, JobStatus not completed, current status: \"%s\"" % (data['Message']))
                start_job_status_message = new_job_status_message
            else:
                pass
            continue
            

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        system_erase()
        loop_job_status()
    elif args["g"]:
        get_components()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    
    
        
            
        
        

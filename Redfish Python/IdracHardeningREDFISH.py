#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse, getpass, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to configure server for iDRAC hardening (recommended server iDRAC settings for providing additional server security). Script workflow: (1) prompt for current iDRAC user ID 2 password. (2) Change iDRAC user ID 2 password. NOTE: Script will complete rest of the workflow using new password. (3) Check for any iDRAC users configured. If configured, script will prompt for password change. (4) Disable iDRAC Telnet. (5) Disable iDRAC IPMI. (6) Enable iDRAC webserver, configure TLS protocol to 1.2 only. (7) Check if iDRAC SNMP is configured. (8) Disable iDRAC VNC server. (8) Disable iDRAC USB config XML. (9) Check if iDRAC remote syslog is configured. (10) Check if iDRAC NTP is configured. (11) Disable iDRAC SOL. (12) Disable iDRAC local configuration using Settings. (13) Disable local iDRAC configuration using RACADM. (14) Set iDRAC virtual console plugin to eHTML5(if supported) or HTML5. (15) Disable iDRAC attached virtual media. (16) Set iDRAC SNMP settings to SNMPv3. (17) Disable iDRAC OS pass-through. (18) Disable iDRAC RAC serial. (19) Disable iDRAC Service Module. (20) Disable BIOS internal USB. NOTE: This will reboot the server to apply the change. (21) Prompt to enable iDRAC System Lockdown if disabled. NOTE: For each step in the workflow, if the recommended value is already set for that attribute, script will skip PATCH operation.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='Pass in iDRAC username for account id 2', required=True)
parser.add_argument('script_examples',action="store_true",help='IdracHardeningREDFISH.py -ip 192.168.0.120 -u root') 

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]

def check_supported_idrac_version(x,xx,xxx):
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        print("\nNote: If using iDRAC 7/8, this script is not supported. Use Server Configuration Profile feature instead with Redfish to set iDRAC / System and Lifecycle Controller attributes") 
        sys.exit()
    else:
        print("- PASS, GET request passed to check %s \"%s\" user credentials" % (xx,xxx))

def set_user_id_2_new_password(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/2' % (idrac_ip)
    payload = {'Password': x}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, xx))
    if response.status_code == 200:
        print("- PASS, PATCH command passed to change iDRAC user \"%s\" password" % idrac_username)
        time.sleep(10)
    else:
        data_error = response.json()
        print("\n- FAIL, status code %s returned, password was not changed. Detailed error results: \n%s" % (response.status_code, data_error))
        sys.exit()

def get_iDRAC_user_account_info(x):
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts' % (idrac_ip),verify=False,auth=(idrac_username, x))
    if response.status_code == 200:
        pass
    else:
        data = response.json()
        print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (response.status_code, data))
        sys.exit()
    data = response.json()
    for i in data["Members"]:
        for ii in i.items():
            response = requests.get('https://%s%s' % (idrac_ip,ii[1]),verify=False,auth=(idrac_username, x))
            if response.status_code == 200:
                data=response.json()
            else:
                data = response.json()
                print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (response.status_code, data))
                sys.exit()
            if data["Enabled"] == True and data["UserName"] != "" and data["Id"] != "1" and data["Id"] != "2":
                idrac_new_password = getpass.getpass("- INFO, iDRAC username \"%s\" enabled, set new password: " % data["UserName"]) 
                url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/%s' % (idrac_ip, data["Id"])
                payload = {'Password': idrac_new_password}
                headers = {'content-type': 'application/json'}
                response = requests.patch(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, x))
                if response.status_code == 200:
                    print("- PASS, PATCH command passed to change iDRAC user \"%s\" password" % (data["UserName"]))
                else:
                    data_error = response.json()
                    print("\n- FAIL, status code %s returned, password was not changed. Detailed error results: \n%s" % (response.status_code, data_error))
                    sys.exit()
                time.sleep(10)
                print("- INFO, validating new password with GET request for iDRAC user \"%s\"" % data["UserName"])
                if data["RoleId"] == "ReadOnly" or data["RoleId"] == "None":
                    print("- INFO, unable to validate iDRAC user \"%s\" new password due to unsupported privileges, skipping test" % data["UserName"])
                    continue
                else:
                    pass
                response = requests.get('https://%s/redfish/v1/Managers' % (idrac_ip),verify=False,auth=(data["UserName"], idrac_new_password))
                if response.status_code == 200:
                    print("- PASS, validation of new password for iDRAC user \"%s\" passed" % data["UserName"])
                else:
                    data_error = response.json()
                    print("\n- FAIL, status code %s returned for GET command. Detail error results: \n%s" % (response.status_code, data_error))
                    sys.exit()
            
def get_specific_attribute(x,xx):
    global set_flag
    global supported_idrac_version
    global virtual_console_plugin
    global system_lockdown_value
    global system_lockdown_not_supported
    system_lockdown_not_supported = ""
    virtual_console_plugin = ""
    system_lockdown_value = ""
    supported_idrac_version = "yes"
    set_flag = "no"
    count = 1
    print("- INFO, getting current value for attribute \"%s\"" % xx)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            count+=1
            print("- iDRAC Attribute: %s, Current Value: %s" % (i, attributes_dict[i]))
            if attributes_dict[i] == "HTML5":
                virtual_console_plugin = "HTML5"
            if xx == "WebServer.1.TLSProtocol":
                if attributes_dict[i] == "TLS 1.0 and Higher" or attributes_dict[i] == "TLS 1.1 and Higher":
                    set_flag = "yes"
                    break
                else:
                    break
            if xx == "SNMP.1.AgentEnable":
                if attributes_dict[i] == "Enabled":
                    print("- INFO, SNMP agent enabled, check current SNMP configuration settings to verify correct setup ")
                    break
                else:
                    print("- INFO, SNMP agent Disabled")
                    break
            if xx == "SysLog.1.SysLogEnable":
                if attributes_dict[i] == "Enabled":
                    print("- INFO, Remote Syslog enabled, check remote syslog settings to verify correct setup ")
                    break
                else:
                    print("- INFO, iDRAC Remote Syslog feature is Disabled")
                    break
            if xx == "NTPConfigGroup.1.NTPEnable":
                if attributes_dict[i] == "Enabled":
                    print("- INFO, NTP enabled, check NTP settings to verify correct setup ")
                    break
                else:
                    print("- INFO, iDRAC NTP feature is Disabled")
                    break
            if xx == "WebServer.1.Enable" or xx == "Lockdown.1.SystemLockdown":
                if attributes_dict[i] == "Disabled":
                    set_flag = "yes"
                    system_lockdown_value = "Disabled"
                    break
                else:
                    break
            if xx == "USB.1.ConfigurationXML":
                if attributes_dict[i] != "Enabled":
                    set_flag = "yes"
                    break
                else:
                    break
            if xx == "LocalSecurity.1.LocalConfig" or xx == "LocalSecurity.1.PrebootConfig" or xx == "VirtualMedia.1.Enable" or xx == "OS-BMC.1.AdminState" or xx == "Serial.1.Enable":
                if attributes_dict[i] == "Enabled":
                    set_flag = "yes"
                    break
                else:
                    break
            if xx == "VirtualConsole.1.PluginType":
                if attributes_dict[i] != "eHTML5":
                    set_flag = "yes"
                    break
                else:
                    break
            if xx == "SNMP.1.TrapFormat":
                if attributes_dict[i] != "SNMPv3":
                    set_flag = "yes"
                    break
                else:
                    break
            else:
                if attributes_dict[i] == "Enabled":
                    set_flag = "yes"
                    break
                else:
                    break
    if count == 1:
        if xx == "Telnet.1.Enable":
            print("- INFO, iDRAC version detected no longer supports Telnet service, skipping PATCH command to change current value")
            supported_idrac_version = "no"
        elif xx == "VNCServer.1.Enable" or xx == "SysLog.1.SysLogEnable":
            print("- INFO, unable to locate attribute \"%s\". Missing required iDRAC license to support this attribute" % xx)
        elif xx == "Lockdown.1.SystemLockdown":
            print("- INFO, unable to locate attribute \"%s\". Missing required iDRAC license to support this attribute" % xx)
            system_lockdown_not_supported = "yes"
        else:
            print("- INFO, unable to locate attribute \"%s\" to get current value, skipping PATCH command" % xx)

def set_attribute_disabled(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{xx:"Disabled"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("- PASS, PATCH command passed to set attribute \"%s\" to Disabled" % xx)
    else:
        print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    print("- INFO, getting new current value for attribute \"%s\"" % xx)
    time.sleep(10)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            if attributes_dict[i] == "Disabled":
                print("- PASS, iDRAC attribute \"%s\" successfully set to Disabled" % xx)
            else:
                print("- FAIL, iDRAC attribute \"%s\" not set to Disabled" % xx)
                sys.exit()

def set_attribute_enabled(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{xx:"Enabled"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("- PASS, PATCH command passed to set attribute \"%s\" to enabled" % xx)
    else:
        print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    print("- INFO, getting new current value for attribute \"%s\"" % xx)
    time.sleep(10)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            if attributes_dict[i] == "Enabled":
                print("- PASS, iDRAC attribute \"%s\" successfully set to Enabled" % xx)
            else:
                print("- FAIL, iDRAC attribute \"%s\" not set to Enabled" % xx)
                sys.exit()

def set_TLS_attribute_enabled(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{xx:"TLS 1.2 Only"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("- PASS, PATCH command passed to set attribute \"%s\" to TLS 1.2 Only" % xx)
    else:
        print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    print("- INFO, getting new current value for attribute \"%s\", script will wait 1 minute to validate new TLS changes" % xx)
    time.sleep(60)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            if attributes_dict[i] == "TLS 1.2 Only":
                print("- PASS, iDRAC attribute \"%s\" successfully set to TLS 1.2 Only" % xx)
            else:
                print("- FAIL, iDRAC attribute \"%s\" not set to TLS 1.2 Only" % xx)
                sys.exit()

def set_SNMP(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    payload = {"Attributes":{xx:"SNMPv3"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("- PASS, PATCH command passed to set attribute \"%s\" to SNMPv3" % xx)
    else:
        print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    time.sleep(10)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            if attributes_dict[i] == "SNMPv3":
                print("- PASS, iDRAC attribute \"%s\" successfully set to SNMPv3" % xx)
            else:
                print("- FAIL, iDRAC attribute \"%s\" not set to SNMPv3" % xx)
                sys.exit()

def set_virtual_console_plugin(x,xx):
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    
    payload = {"Attributes":{xx:"eHTML5"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
    data = response.json()
    if response.status_code == 400:
        if data["error"]["@Message.ExtendedInfo"][0]["Message"] == "The specified object value is not valid.":
            print("- INFO, current iDRAC version detected does not support plugin type \"eHTML5\"")
            if virtual_console_plugin == "HTML5":
                print("- INFO, attribute \"%s\" already set to HTML5, skipping PATCH command" % xx)
                return
            payload = {"Attributes":{xx:"HTML5"}}
            headers = {'content-type': 'application/json'}
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, x))
            data = response.json()
            if response.status_code == 200 or response.status_code == 202:
                print("- PASS, PATCH command passed to set attribute \"%s\" to HTML5" % xx)
                value_change = "HTML5"
            else:
                print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
                print("Extended Info Message: {0}".format(response.json()))
                sys.exit()
            
    else:
        if response.status_code == 200 or response.status_code == 202:
            print("- PASS, PATCH command passed to set attribute \"%s\" to eHTML5" % xx)
            value_change = "eHTML5"
        else:
            print("\n- FAIL, PATCH command failed to set attribute \"%s\", status code: %s\n" % (xx, response.status_code))
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    
    time.sleep(10)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    attributes_dict=data['Attributes']
    for i in attributes_dict:
        if i == xx:
            if attributes_dict[i] == value_change:
                print("- PASS, iDRAC attribute \"%s\" successfully set to %s" % (xx, value_change))
            else:
                print("- FAIL, iDRAC attribute \"%s\" not set to %s" % (xx, value_change))
                sys.exit()

def get_internal_USB_bios_attribute(x):
    global set_flag_bios_attribute
    set_flag_bios_attribute = "no"
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,x))
    data = response.json()
    for i in data['Attributes'].items():
        if i[0] == "InternalUsb":
            print("- BIOS attribute: \"%s\", Current Value: \"%s\"" % ("InternalUsb", i[1]))
            if i[1] == "On":
                set_flag_bios_attribute = "yes"
            elif i[1] == "Off":
                print("- INFO, BIOS attribute \"InternalUsb\" current value set to Off, skipping PATCH operation")
                set_flag_bios_attribute = "no"
                return
    if set_flag_bios_attribute == "no":
        print("\n- FAIL, unable to get BIOS attribute \"InternalUsb\" current value. Either attribute doesn't exist for this BIOS version or the server itself does not support internal USB port")
    
    
def create_next_boot_config_job(x):
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    bios_attribute_payload = {"Attributes":{"InternalUsb":"Off"}}
    payload_patch.update(bios_attribute_payload)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=False,auth=(idrac_username,x))
    statusCode = response.status_code
    if response.status_code == 202 or response.status_code == 200:
        print("- PASS, PATCH command passed to set BIOS attribute pending value")
    else:
        print("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    get_location_output = response.headers["Location"]
    try:
        job_id=re.search("JID.+",get_location_output).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("- PASS, BIOS config job ID \"%s\" successfully created" % (job_id))


def check_job_status_schedule(x):
    while True:
        response = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, x), verify=False)
        if response.status_code == 202 or response.status_code == 200:
            pass
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = response.json()
        if data['Messages'][0]['Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply boot option changes" % job_id)
            break
        if "Lifecycle Controller in use" in data['Messages'][0]['Message']:
            print("- INFO, Lifecycle Controller in use, this job will start when Lifecycle Controller is available. Check overall jobqueue to make sure no other jobs are running and make sure server is either off or out of POST")
            sys.exit()
        else:
            print("- INFO: JobStatus not scheduled, current status is: %s" % data['Messages'][0]['Message'])
            time.sleep(1)
            continue

def reboot_server(x):
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, x))
    data = response.json()
    print("- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,x))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to gracefully power OFF server")
            print("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            print("\n- FAIL, POST command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, x))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                print("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, x))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, POST command passed to perform forced shutdown")
                    time.sleep(15)
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, x))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        print("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        print("- FAIL, server not in OFF state, current power status: %s" % data['PowerState'])
                        sys.exit()    
            else:
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, x))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to power ON server")
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username, x))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to power ON server")
        else:
            print("\n- FAIL, POST command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()


def check_final_job_status(x):
    start_time=datetime.now()
    time.sleep(1)
    while True:
        check_idrac_connection()
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, x), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
        if response.status_code == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % response.status_code)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = response.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            break
        else:
            print("- INFO, job status not marked completed, current status: \"%s\"" % (data['Message']))
            check_idrac_connection()
            time.sleep(5)


def check_idrac_connection():
    ping_command="ping %s -n 5" % idrac_ip
    while True:
        try:
            ping_output = subprocess.Popen(ping_command, stdout = subprocess.PIPE, shell=True).communicate()[0]
            ping_results = re.search("Lost = .", ping_output).group()
            if ping_results == "Lost = 0":
                break
            else:
                print("\n- INFO, iDRAC connection lost, script will recheck iDRAC connection in 1 minute")
                time.sleep(60)
        except:
            ping_output = subprocess.run(ping_command,universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if "Lost = 0" in ping_output.stdout:
                break
            else:
                print("\n- INFO, iDRAC connection lost, script will recheck iDRAC connection in 1 minute")
                time.sleep(60)

def verify_internal_USB_bios_attribute_off(x):
    time.sleep(15)
    success_pass = "no"
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,x))
    data = response.json()
    count = 1
    while True:
        if success_pass == "yes":
            break
        if count == 10:
            print("- INFO, unable to get BIOS attribute \"Internal USB\" current value after 10 attempts, skipping test")
            break
        try:
            for i in data['Attributes'].items():
                if i[0] == "InternalUsb":
                    if i[1] == "Off":
                        print("- PASS, BIOS attribute \"Internal USB\" successfully set to Off")
                        success_pass = "yes"
                    else:
                        print("- FAIL, BIOS attribute \"Internal USB\" not set to Off, current value is: \"%s\"" % i[1])
                        sys.exit()
        except:
            print("- INFO, unable to get BIOS attribute \"Internal USB\" current value, trying again")
            time.sleep(15)
            count+=1
            continue
            

        


if __name__ == "__main__":
    current_idrac_root_password = getpass.getpass("\n- INFO, enter current password for iDRAC user %s: " % idrac_username)
    check_supported_idrac_version(current_idrac_root_password, "CURRENT", idrac_username)
    new_idrac_root_password = getpass.getpass("- INFO, enter new password for iDRAC user %s: " % idrac_username)
    set_user_id_2_new_password(new_idrac_root_password, current_idrac_root_password)
    check_supported_idrac_version(new_idrac_root_password, "NEW", idrac_username)
    get_iDRAC_user_account_info(new_idrac_root_password)
    get_specific_attribute(new_idrac_root_password,"Telnet.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"Telnet.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"Telnet.1.Enable\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"IPMILan.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"IPMILan.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"IPMILan.1.Enable\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"WebServer.1.Enable")
    if set_flag == "yes":
        set_attribute_enabled(new_idrac_root_password,"WebServer.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"WebServer.1.Enable\" already set to Enabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"WebServer.1.TLSProtocol")
    if set_flag == "yes":
        set_TLS_attribute_enabled(new_idrac_root_password,"WebServer.1.TLSProtocol")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"WebServer.1.TLSProtocol\" already set to TLS 1.2 Only, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"SNMP.1.AgentEnable")
    get_specific_attribute(new_idrac_root_password,"VNCServer.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"VNCServer.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, either iDRAC attribute \"VNCServer.1.Enable\" already set to Disabled or not supported, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"USB.1.ConfigurationXML")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"USB.1.ConfigurationXML")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, either iDRAC attribute \"USB.1.ConfigurationXML\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"SysLog.1.SysLogEnable")
    get_specific_attribute(new_idrac_root_password,"NTPConfigGroup.1.NTPEnable")
    get_specific_attribute(new_idrac_root_password,"IPMISOL.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"IPMISOL.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, either iDRAC attribute \"IPMISOL.1.Enable\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"LocalSecurity.1.LocalConfig")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"LocalSecurity.1.LocalConfig")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"LocalSecurity.1.LocalConfig\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"LocalSecurity.1.PrebootConfig")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"LocalSecurity.1.PrebootConfig")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"LocalSecurity.1.PrebootConfig(RACADM)\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"VirtualConsole.1.PluginType")
    if set_flag == "yes":
        set_virtual_console_plugin(new_idrac_root_password,"VirtualConsole.1.PluginType")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"VirtualConsole.1.PluginType\" already set to eHTML5(if supported) or HTML5, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"VirtualMedia.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"VirtualMedia.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"VirtualMedia.1.Enable\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"SNMP.1.TrapFormat")
    if set_flag == "yes":
        set_SNMP(new_idrac_root_password,"SNMP.1.TrapFormat")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"SNMP.1.TrapFormat\" already set to SNMPv3 , skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"OS-BMC.1.AdminState")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"OS-BMC.1.AdminState")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"OS-BMC.1.AdminState\" already set to Disabled , skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"Serial.1.Enable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"Serial.1.Enable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, either iDRAC attribute \"Serial.1.Enable\" already set to Disabled, skipping PATCH command")
    get_specific_attribute(new_idrac_root_password,"ServiceModule.1.ServiceModuleEnable")
    if set_flag == "yes":
        set_attribute_disabled(new_idrac_root_password,"ServiceModule.1.ServiceModuleEnable")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            print("- INFO, iDRAC attribute \"ServiceModule.1.ServiceModuleEnable\" already set to Disabled, skipping PATCH command")
            
            
    get_internal_USB_bios_attribute(new_idrac_root_password)
    if set_flag_bios_attribute == "yes":
        create_next_boot_config_job(new_idrac_root_password)
        check_job_status_schedule(new_idrac_root_password)
        reboot_server(new_idrac_root_password)
        check_final_job_status(new_idrac_root_password)
        verify_internal_USB_bios_attribute_off(new_idrac_root_password)
    else:
        pass

    get_specific_attribute(new_idrac_root_password,"Lockdown.1.SystemLockdown")
    if set_flag == "yes":
        if system_lockdown_value == "Disabled":
            user_response = input(str("- INFO, System lockdown currently set to Disabled, would you like to enable it? Pass in \"y\" for yes or \"n\" for no: "))
            if user_response.lower() == "n":
                print("- INFO, user selected to not enable iDRAC System Lockdown feature")
            else:
                set_attribute_enabled(new_idrac_root_password,"Lockdown.1.SystemLockdown")
    else:
        if supported_idrac_version == "no":
            pass
        else:
            if system_lockdown_not_supported == "yes":
                pass
            else:
                print("- INFO, iDRAC attribute \"Lockdown.1.SystemLockdown\" already set to Disabled , skipping PATCH command")
        
    print("\n-PASS, script completed hardening workflow")
    
    
    
        



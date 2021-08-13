#
# GetSetOemNetworkPropertiesREDFISH. Python script using Redfish API DMTF to either get or set OEM network device properties. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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


import requests, json, sys, re, time, warnings, argparse, os, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get or set OEM network device properties. This will configure properties which are not exposed as being supported from DMTF. Examples: virtual MAC address or virtualization mode.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get all supported network devices IDs. GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -a NIC.Integrated.1-1-1, this example will get attributes for only device ID NIC.Integrated.1-1-1. GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -a NIC.Integrated.1-1-1 -A VLanMode, this example will return only details for NIC.Integrated.1-1-1 attribute VLanMode. GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.120 -u root -p calvin -ars VLanMode, this example will return only attribute registry information for attribute VLanMode. GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s NIC.Integrated.1-1-1 -an VLanMode,VLanId -av Enabled,1000 -r y, this example shows configuring attributes VLanMode and VLandId for NIC.Integrated.1-1-1, rebooting the server immediately to apply. GetSetOemNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s NIC.Integrated.1-1-1 -an VLanMode,VLanId -av Enabled,1000 -mt n -st 2021-08-13T11:05:05-05:00 -dt 3000, this example shows setting attributes VLanMode and VLanId for NIC.Integrated.1-1-1 using the maintenance window. Job will get created and then reboot the server, execute at the specific time of 11:05 AM.')
parser.add_argument('-g', help='Get network device IDs, pass in a value of \"y\"', required=False)
parser.add_argument('-a', help='Get attributes for network device, pass in network device ID. Example: NIC.Integrated.1-1-1. if needed, execute script using argument -g to get network device IDs.', required=False)
parser.add_argument('-A', help='Get specific attribute, pass in the attribute name. You must also argument -a passing in the network device ID. NOTE: For the attribute name, make sure you pass in the exact case.', required=False)
parser.add_argument('-ar', help='Get network attribute registry, pass in a value of \"y\". Attribute registry will return attribute information for possible values, if read only, if read write, regex.', required=False)
parser.add_argument('-ars', help='Get registry information for a specific attribute, pass in the attribute name. NOTE: For the attribute name, make sure you pass in the exact case.', required=False)
parser.add_argument('-s', help='Set attributes, pass in the network device ID (Example: NIC.Integrated.1-1-1). You must also use arguments -an -av and -r for setting attributes.', required=False)
parser.add_argument('-an', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: VLanMode will work but vlanmode will fail. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: -r (reboot type) is required when setting attributes', required=False)
parser.add_argument('-av', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value.', required=False)
parser.add_argument('-r', help='Pass in value for reboot type. Pass in \"y\" for server to reboot now and apply changes immediately. Pass in \"n\" which will schedule the job but system will not reboot. Next manual server reboot, job will be applied. Pass in \"s\" to create a maintenance window config job. Job will go to schedule state once maintenance window has started', required=False)
parser.add_argument('-mt', help='Pass in the type of maintenance window job type you want to create. Pass in \"n\" if you want the server to automatically reboot and apply the changes once the maintenance windows has been hit. Pass in \"l\" if you don\'t want the server to automatically reboot once the maintenance window time has hit. If you select this option, user will have to reboot the server to apply the configuration job.', required=False)
parser.add_argument('-st', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', required=False)
parser.add_argument('-dt', help='Maintenance window duration time, pass in a value in seconds', required=False)
parser.add_argument('-t', help='Get current iDRAC time, pass in \"y\". Excute this argument to get iDRAC current time, help with setting maintenance window configuration job.', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit(1)
    elif response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(1)
    else:
        pass

def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":True}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n- Current iDRAC time -\n")
    else:
        print("\n- FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- Failure results:\n %s" % data)
        sys.exit(0)
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))

def get_network_device_fqdds():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    network_device_list=[]
    for i in data['Members']:
        for ii in i.items():
            network_device = ii[1].split("/")[-1]
            network_device_list.append(network_device)
    for i in network_device_list:
        port_list = []
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n- Network device ID(s) detected for %s -\n" % i)
        for i in data['Members']:
            for ii in i.items():
                print(ii[1].split("/")[-1])

def get_network_device_attributes():
    network_id = args["a"].split("-")[0]
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["a"], args["a"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- %s Attributes -\n" % args["a"])
    for i in data["Attributes"].items():
        print("Attribute Name: %s, Attribute Value: %s" % (i[0], i[1]))


def get_network_device_specific_attribute():
    network_id = args["a"].split("-")[0]
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s' % (idrac_ip, network_id, args["a"], args["a"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data["Attributes"].items():
        if i[0] == args["A"]:
            print("\nAttribute Name: %s, Attribute value: %s" % (i[0], i[1]))
            sys.exit(0)
        else:
            pass
    print("\n - INFO, unable to locate attribute %s. Confirm you passed in correct case for attribute" % args["A"])
    

def network_registry():
    try:
        os.remove("nic_attribute_registry.txt")
    except:
        pass
    f=open("nic_attribute_registry.txt","a")
    response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data['RegistryEntries']['Attributes']:
        for ii in i.items():
            message = "%s: %s" % (ii[0], ii[1])
            f.writelines(message)
            print(message)
            message = "\n"
            f.writelines(message)
        message = "\n"
        print(message)
        f.writelines(message)
    print("\n- Attribute registry is also captured in \"nic_attribute_registry.txt\" file")
    f.close()

def network_registry_get_specific_attribute():
    print("\n- INFO, searching attribute network registry for attribute \"%s\"" % args["ars"])
    response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    found = ""
    for i in data['RegistryEntries']['Attributes']:
        if args["ars"] in i.values():
            print("\n- Attribute Registry information for attribute \"%s\" -\n" % args["ars"])
            found = "yes"
            for ii in i.items():
                print("%s: %s" % (ii[0],ii[1]))
    if found != "yes":
        print("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % args["ars"])
        sys.exit(1)

    
def create_network_attribute_dict():
    global network_attribute_payload
    network_attribute_payload = {"Attributes":{}}
    attribute_names = args["an"].split(",")
    attribute_values = args["av"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        network_attribute_payload["Attributes"][i] = ii
    response = requests.get('https://%s/redfish/v1/Registries/NetworkAttributesRegistry/NetworkAttributesRegistry.json' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in network_attribute_payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    network_attribute_payload['Attributes'][i[0]] = int(i[1])
    print("\n- INFO, script will be setting network attribute(s) -\n")
    for i in network_attribute_payload["Attributes"].items():
        print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))

    
def create_next_boot_config_job():
    global job_id
    global payload_patch
    network_id = args["s"].split("-")[0]
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s/Settings" % (idrac_ip, network_id, args["s"], args["s"])
    payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    payload_patch.update(network_attribute_payload)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: PATCH command passed to set network attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, PATCH command failed to set network attribute pending values and create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit(1)
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to locate job ID in headers output.")
        sys.exit(1)
    print("\n- PASS, %s next reboot config JID successfully created\n" % (job_id))

def create_schedule_config_job():
    global job_id
    global payload_patch
    network_id = args["s"].split("-")[0]
    url = "https://%s/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s/Settings" % (idrac_ip, network_id, args["s"], args["s"])
    if args["mt"] == "l":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "InMaintenanceWindowOnReset","MaintenanceWindowStartTime":str(args["st"]),"MaintenanceWindowDurationInSeconds": int(args["dt"])}}
    elif args["mt"] == "n":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(args["st"]),"MaintenanceWindowDurationInSeconds": int(args["dt"])}}        
    else:
        print("- FAIL, invalid value passed in for maintenance window job type")
        sys.exit(1)
    payload_patch.update(network_attribute_payload)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: PATCH command passed to set network attribute pending values and create maintenance window config job, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, PATCH command failed to set network attribute pending values and create maintenance window config job, status code: %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure:\n %s" % data)
        sys.exit(1)
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit(1)

    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    time.sleep(5)
    print("\n--- PASS, Detailed Job Status Results ---\n")
    for i in data.items():
        if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
            pass
        else:
            print("%s: %s" % (i[0],i[1]))
    if args["mt"] == "l":                
        print("\n- PASS, %s maintenance window config jid successfully created.\n\nJob will go to scheduled state once start time has elapsed. You will need to schedule a seperate server reboot during the maintenance windows for the config job to execute.\n" % (job_id))
    elif args["mt"] == "n":
        print("\n- PASS %s maintenance window config jid successfully created.\n\nJob will go to scheduled state once start time has elapsed and automatically reboot the server to apply the configuration job." % job_id) 



def check_job_status_schedule():
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 202 or statusCode == 200:
            pass
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit(1)
        data = req.json()
        if data['Messages'][0]['Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled" % job_id)
            break
        if "Lifecycle Controller in use" in data['Messages'][0]['Message']:
            print("- INFO, Lifecycle Controller in use, this job will start when Lifecycle Controller is available. Check overall jobqueue to make sure no other jobs are running and make sure server is either off or out of POST")
            sys.exit(0)
        else:
            print("- INFO: JobStatus not scheduled, current status is: %s" % data['Messages'][0]['Message'])

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % statusCode)
            print("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit(1)
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                print("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, POST command passed to perform forced shutdown, status code return is %s" % statusCode)
                    time.sleep(15)
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        print("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        print("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit(1)    
            else:
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()


def check_final_job_status():
    start_time=datetime.now()
    time.sleep(1)
    while True:
        check_idrac_connection()
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
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
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- INFO, JobStatus not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'], current_time))
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
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                time.sleep(180)
        except:
            ping_output = subprocess.run(ping_command,universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if "Lost = 0" in ping_output.stdout:
                break
            else:
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                time.sleep(180)



if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_network_device_fqdds()
    elif args["t"]:
        get_idrac_time()
    elif args["a"] and args["A"]:
        get_network_device_specific_attribute()
    elif args["a"]:
              get_network_device_attributes()
    elif args["ar"]:
        network_registry()
    elif args["ars"]:
        network_registry_get_specific_attribute()
    elif args["an"] and args["av"] and args["r"] and args["s"]:
        create_network_attribute_dict()
        create_next_boot_config_job()
        check_job_status_schedule()
        if args["r"] == "y":
            print("\n- INFO, user selected to reboot the server now to execute the job ID.")
            reboot_server()
            time.sleep(20)
            check_final_job_status()
        elif args["r"] == "n":
            print("\n- INFO, user selected to not reboot the server now. Job ID is still scheduled and will execute on next manual server reboot.")
            sys.exit(0)
        else:
            print("- INFO, invalid value passed in for argument -r. Job ID is still scheduled and will execute on next manual server reboot.")
            sys.exit(0)
    elif args["an"] and args["av"] and args["mt"] and args["dt"]:
        create_network_attribute_dict()
        create_schedule_config_job()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
        
            
        


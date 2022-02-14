#
# GetSetBiosAttributesREDFISH. Python script using Redfish API DMTF to either get or set BIOS attributes using Redfish SettingApplyTime.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 14.0
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


import requests, json, sys, re, time, warnings, argparse, os, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get or set BIOS attributes using Redfish SettingApplyTime. If needed, run a GET on URI \"redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry\" to see supported possible values for setting attributes.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example will get all BIOS attributes. GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -an MemTest -av Disabled -r s -st "2018-10-30T20:10:10-05:00" -dt 600, this example shows setting BIOS attribute using scheduled start time with maintenance window. GetSetBiosAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -an EmbSata,NvmeMode -av RaidMode,Raid -r n, this example shows setting multiple BIOS attributes with reboot now to apply')
parser.add_argument('-a', help='Get all BIOS attributes, pass in a value of \"y\"', required=False)
parser.add_argument('-A', help='If you want to get only a specific BIOS attribute, pass in the attribute name you want to get the current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail', required=False)
parser.add_argument('-ar', help='Get BIOS attribute registry, pass in a value of \"y\"', required=False)
parser.add_argument('-s', help='Get registry information for a specific attribute, pass in the attribute name', required=False)
parser.add_argument('-an', help='Pass in the attribute name you want to change current value, Note: make sure to type the attribute name exactly due to case senstive. Example: MemTest will work but memtest will fail. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: -r (reboot type) is required when setting attributes', required=False)
parser.add_argument('-av', help='Pass in the attribute value you want to change to. Note: make sure to type the attribute value exactly due to case senstive. Example: Disabled will work but disabled will fail. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value.', required=False)
parser.add_argument('-r', help='Pass in value for reboot type. Pass in \"n\" for server to reboot now and apply changes immediately. Pass in \"l\" which will schedule the job but system will not reboot. Next manual server reboot, job will be applied. Pass in \"s\" to create a maintenance window config job. Job will go to schedule state once maintenance window has started', required=False)
parser.add_argument('-mt', help='Pass in the type of maintenance window job type you want to create. Pass in \"n\" if you want the server to automatically reboot and apply the changes once the maintenance windows has been hit. Pass in \"l\" if you don\'t want the server to automatically reboot once the maintenance window time has hit. If you select this option, user will have to reboot the server to apply the configuration job.', required=False)
parser.add_argument('-st', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', required=False)
parser.add_argument('-dt', help='Maintenance window duration time, pass in a value in seconds', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


if args["r"] and args["an"] and args["av"]:
    if args["r"] == "n":
        job_type = "n"
    elif args["r"] == "l":
        job_type = "l"
    elif args["r"] == "s" and args["st"] and args["dt"]:
        job_type = "s"
        start_time_input = args["st"]
        duration_time = args["dt"]
    else:
        print("\n- FAIL, -s, -st and -dt all required to create maintenance window config job")
        sys.exit()




def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned, check your iDRAC username/password is correct or iDRAC user has correct privileges to execute Redfish commands" % response.status_code)
        sys.exit()
    elif response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_bios_attributes():
    try:
        os.remove("bios_attributes.txt")
    except:
        pass
    f=open("bios_attributes.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.year,d.month,d.day, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    a="\n--- BIOS Attributes ---\n"
    print(a)
    f.writelines(a)
    for i in data['Attributes'].items():
        attribute_name = "Attribute Name: %s\t" % (i[0])
        f.writelines(attribute_name)
        attribute_value = "Attribute Value: %s\n" % (i[1])
        f.writelines(attribute_value)
        print("Attribute Name: %s\t Attribute Value: %s" % (i[0],i[1]))
        
    print("\n- Attributes are also captured in \"bios_attributes.txt\" file")
    f.close()

def get_specific_bios_attribute():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data['Attributes'].items():
        if i[0] == args["A"]:
            print("\n- Current value for attribute \"%s\" is \"%s\"\n" % (args["A"], i[1]))
            sys.exit()
    print("\n- FAIL, unable to get attribute current value. Either attribute doesn't exist for this BIOS version, typo in attribute name or case incorrect")
    sys.exit()

def bios_registry():
    try:
        os.remove("bios_attribute_registry.txt")
    except:
        pass
    f=open("bios_attribute_registry.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
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
    print("\n- Attribute registry is also captured in \"bios_attribute_registry.txt\" file")
    f.close()

def bios_registry_get_specific_attribute():
    print("\n- WARNING, searching BIOS registry for attribute \"%s\"" % args["s"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    found = ""
    for i in data['RegistryEntries']['Attributes']:
        if args["s"] in i.values():
            print("\n- Attribute Registry information for attribute \"%s\" -\n" % args["s"])
            found = "yes"
            for ii in i.items():
                print("%s: %s" % (ii[0],ii[1]))
    if found != "yes":
        print("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % args["s"])

    
def create_bios_attribute_dict():
    global bios_attribute_payload
    bios_attribute_payload = {"Attributes":{}}
    attribute_names = args["an"].split(",")
    attribute_values = args["av"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        bios_attribute_payload["Attributes"][i] = ii
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios/BiosRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in bios_attribute_payload["Attributes"].items():
        for ii in data['RegistryEntries']['Attributes']:
            if i[0] in ii.values():
                if ii['Type'] == "Integer":
                    bios_attribute_payload['Attributes'][i[0]] = int(i[1])
    print("\n- INFO, script will be setting BIOS attribute(s) -\n")
    for i in bios_attribute_payload["Attributes"].items():
        print("Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))

    
def create_next_boot_config_job():
    global job_id
    global payload_patch
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    payload_patch.update(bios_attribute_payload)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: PATCH command passed to set BIOS attribute pending values and create next reboot config job, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("\n- PASS, %s next reboot config JID successfully created\n" % (job_id))

def create_schedule_config_job():
    global job_id
    global payload_patch
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Bios/Settings' % (idrac_ip)
    if args["mt"] == "l":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "InMaintenanceWindowOnReset","MaintenanceWindowStartTime":str(start_time_input),"MaintenanceWindowDurationInSeconds": int(duration_time)}}
    elif args["mt"] == "n":
        payload_patch = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(start_time_input),"MaintenanceWindowDurationInSeconds": int(duration_time)}}        
    else:
        print("- FAIL, invalid value passed in for maintenance window job type")
        sys.exit()
    payload_patch.update(bios_attribute_payload)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload_patch), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: PATCH command passed to set BIOS attribute pending values and create maintenance window config job, status code %s returned" % response.status_code)
    else:
        print("\n- FAIL, PATCH command failed to set BIOS attribute pending values and create maintenance window config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()

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
        print("\n- PASS %s maintenance window config jid successfully created.\n\nJob will go to scheduled state once start time has elapsed and automatically reboot the server to apply the configuration job" % job_id) 
start_time=datetime.now()



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
            sys.exit()
        data = req.json()
        if data['Messages'][0]['Message'] == "Task successfully scheduled.":
            if args["r"] == "l":
                print("- PASS, %s job id successfully scheduled, next server manual reboot the job will execute" % job_id)
                break
            elif args["r"] == "n":
                print("- PASS, %s job id successfully scheduled, rebooting the server to apply boot option changes" % job_id)
                break
        if "Lifecycle Controller in use" in data['Messages'][0]['Message']:
            print("- INFO, Lifecycle Controller in use, this job will start when Lifecycle Controller is available. Check overall jobqueue to make sure no other jobs are running and make sure server is either off or out of POST")
            sys.exit()
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
            sys.exit()
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
                        sys.exit()    
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
    if sys.platform.startswith('win'):
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
                ping_output = subprocess.run(ping_command.split(),universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if "Lost = 0" in ping_output.stdout:
                    break
                else:
                    print(")\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                    time.sleep(180)
    else:
        ping_command="ping %s -c 5" % idrac_ip
        while True:
            try:
                ping_output = subprocess.Popen(ping_command, stdout = subprocess.PIPE, shell=True).communicate()[0]
                ping_results = re.search(".% packet loss", ping_output.decode('ascii')).group()
                if ping_results == "0% packet loss":
                    break
                else:
                    print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                    time.sleep(180)
            except:
                ping_output = subprocess.run(ping_command.split(),universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if "% packet loss" in ping_output.stdout:
                    break
                else:
                    print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                    time.sleep(180)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["a"]:
        get_bios_attributes()
    elif args["A"]:
        get_specific_bios_attribute()
    elif args["s"]:
        bios_registry_get_specific_attribute()
    elif args["ar"]:
        bios_registry() 
    elif args["an"] and args["av"] and args["r"]:
        create_bios_attribute_dict()     
        if job_type == "n":
            create_next_boot_config_job()
            check_job_status_schedule()
            reboot_server()
            time.sleep(20)
            check_final_job_status()
        elif job_type == "l":
            create_next_boot_config_job()
            check_job_status_schedule()
        elif job_type == "s" and args["mt"] and args["dt"]:
            create_schedule_config_job()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
        
            
        


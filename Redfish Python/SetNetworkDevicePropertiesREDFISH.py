#
# SetNetworkDevicePropertiesREDFISH. Python script using Redfish API to either get network devices/ports or set network properties.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 6.0
#
# Copyright (c) 2018, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get network devices/ports or set network properties")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-E', help='Pass in a value of \"y\" to see examples of executing the script', required=False)
parser.add_argument('-g', help='Pass in\"y\", this will generate ini file with payload dictionary to set properties. If setting properties, make sure to generate this ini file first. This file is needed to pass in the properties you want to configure', required=False)
parser.add_argument('-n', help='Get server network FQDD devices, pass in \"y\"', required=False)
parser.add_argument('-d', help='Get network device details, pass in network device ID, Example \"NIC.Integrated.1\"', required=False)
parser.add_argument('-P', help='Get network device port details, pass in network port ID, Example \"NIC.Integrated.1-1-1\" ', required=False)
parser.add_argument('-a', help='Get properties for network device, pass in network port ID . Example \"NIC.Integrated.1-1-1\"', required=False)
parser.add_argument('-s', help='To set network properties, pass in network port ID, Example \"NIC.Integrated.1-1-1\" ', required=False)
parser.add_argument('-r', help='Pass in value for reboot type. Pass in \"n\" for server to reboot now and apply changes immediately. Pass in \"l\" which will schedule the job but system will not reboot. Next manual server reboot, job will be applied. Pass in \"s\" to create a maintenance window config job. Job will go to schedule state once maintenance window has started', required=False)
parser.add_argument('-st', help='Maintenance window start date/time, pass it in this format \"YYYY-MM-DDTHH:MM:SS(+/-)HH:MM\"', required=False)
parser.add_argument('-dt', help='Maintenance window duration time, pass in a value in seconds', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["d"]:
    network_device=args["d"]
elif args["a"]:
    network_device_port=args["a"]
elif args["P"]:
    network_device_port=args["P"]
elif args["r"] and args["s"]:
    network_device_port=args["s"]
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
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def script_examples():
    print("\n- Executing Script Examples -")
    print("\nSetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -n y, this example will return network devices detected for your server\n\nSetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -a NIC.Integrated.1-1-1, this example will return NIC properties for NIC.Integrated.1-1-1 port\n\nSetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will generate the ini file needed to set NIC properties. It will also return an example of a modified dictionary for the ini file\n\nSetNetworkDevicePropertiesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s NIC.Integrated.1-1-1 -r n, this example is going to apply property changes immediately from the ini file to NIC.Integrated.1-1-1\n")
    
    
    
def generate_payload_dictionary_file():
    payload={"iSCSIBoot":{},"FibreChannel":{}}
    with open("set_network_properties.ini","w") as x:
        json.dump(payload,x)
    print("\n- WARNING, \"set_network_properties.ini\" file created. This file contains payload dictionary which will be used to set network properties.\n")
    print("Modify the payload dictionary passing in property names and values for the correct group.\n")
    print("Example of modified dictionary: {\"iSCSIBoot\":{\"InitiatorIPAddress\":\"192.168.0.120\",\"InitiatorNetmask\":\"255.255.255.0\"},\"FibreChannel\":{\"FCoELocalVLANId\":100}}\n")
    
def get_network_devices():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Network device ID(s) detected -\n")
    network_device_list=[]
    for i in data['Members']:
        for ii in i.items():
            network_device = ii[1].split("/")[-1]
            network_device_list.append(network_device)
            print(network_device)
    for i in network_device_list:
        port_list = []
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n- Network port ID(s) detected for %s -\n" % i)
        for i in data['Members']:
            for ii in i.items():
                print(ii[1].split("/")[-1])


def get_detail_network_device_info():   
    print("\n - Detailed network device information for %s -\n" % network_device)
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s' % (idrac_ip, network_device),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data.items():
        if i[0] == "Controllers":
            for ii in i[1]:
                for iii in ii.items():
                    if iii[0] == 'ControllerCapabilities':
                        for _ in iii[1].items():
                            print("%s: %s" % (_[0],_[1]))
                    elif iii[0] == 'Links':
                        for _ in iii[1].items():
                            print("%s: %s" % (_[0],_[1]))
                    else:
                        print("%s: %s" % (iii[0],iii[1]))
        else:
            print("%s: %s" % (i[0],i[1]))
    sys.exit()

def get_network_device_port_info():
    if "FC" in network_device_port:
        port_device=network_device_port
        id_device=network_device_port[:-2]
    else:
        port_device=network_device_port[:-2]
        id_device=network_device_port[:-4]
    print("\n - Detailed network port information for %s -\n" % network_device_port)
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkPorts/%s' % (idrac_ip, id_device, port_device),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data.items():
        print("%s: %s" % (i[0],i[1]))
    sys.exit()

def get_network_device_properties():
    print("\n- Properties for network device %s -" % network_device_port)
    if "FC" in network_device_port:
        id_device=network_device_port[:-2]
    else:
        id_device=network_device_port[:-4]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s' % (idrac_ip, id_device, network_device_port),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data.items():
        if i[0] == 'iSCSIBoot':
            if i[1] == None:
                pass
            else:
                print("\n - iSCSIBoot Attributes -\n")
                for i in data['iSCSIBoot'].items():
                    print("%s: %s" % (i[0],i[1]))
    for i in data.items():
        if i[0] == 'FibreChannel':
            if i[1] == None:
                pass
            else:
                print("\n - FibreChannel Attributes -\n")
                for i in data['FibreChannel'].items():
                    print("%s: %s" % (i[0],i[1]))
            

def set_network_properties():
    global job_id
    global job_type
    global port_device
    global id_device
    try:
        with open("set_network_properties.ini","r") as x:
            payload=json.load(x)
    except:
        print("\n- FAIL, \"set_network_properties.ini\" file does not exist. Execute the script with -g to generate the ini file which is needed to set attributes")
        sys.exit()
    if 'iSCSIBoot' in payload:
        if payload['iSCSIBoot'] == {}:
            del payload['iSCSIBoot']
    if 'FibreChannel' in payload:
        if payload['FibreChannel'] == {}:
            del payload['FibreChannel']
    
    if "FC" in network_device_port:
        port_device=network_device_port
        id_device=network_device_port[:-2]
    else:
        port_device=network_device_port
        id_device=network_device_port[:-4]
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    for i in payload.items():
        if type(i[1]) == dict:
            print("\n- WARNING, setting properties for %s group:\n" % i[0])
            for ii in i[1].items():
                print("Property Name: %s, Pending New Value: %s" % (ii[0], ii[1]))
    time.sleep(3)
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: PATCH command passed to set property pending value, status code 200 returned")
    else:
        print("\n- FAIL, PATCH command failed to set properties, status code is %s, failure is:\n%s" % (response.status_code, data))
        sys.exit()
   
def create_reboot_now_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if response.status_code == 202:
        print("\n- PASS: PATCH command passed to create reboot now config job, status code 202 returned")
    else:
        print("\n- FAIL, PATCH command failed to create reboot now config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("\n- PASS, %s reboot now config jid successfully created\n" % (job_id))

def create_next_boot_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if response.status_code == 202:
        print("\n- PASS: PATCH command passed to create next reboot config job, status code 202 returned")
    else:
        print("\n- FAIL, PATCH command failed to create next reboot config job, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("\n- PASS, %s next reboot config jid successfully created\n" % (job_id))

def create_schedule_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Settings' % (idrac_ip, id_device, port_device)
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime": "AtMaintenanceWindowStart","MaintenanceWindowStartTime":str(start_time_input),"MaintenanceWindowDurationInSeconds": int(duration_time)}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if response.status_code == 202:
        print("\n- PASS: PATCH command passed to create maintenance window config job, status code 202 returned")
    else:
        print("\n- FAIL, PATCH command failed to create maintenance window config job, status code is %s" % response.status_code)
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
                    
    print("\n\n- PASS, %s maintenance window config jid successfully created.\n\nJob will go to scheduled state once job start time has elapsed. You will need to schedule a seperate server reboot during the maintenance windows for the config job to execute. NOTE: If using iDRAC version 4.20 or newer, a reboot job will now get created and scheduled at the same time of the configuration job. Server will automatically reboot once scheduled time has been hit.\n" % (job_id))
    
start_time=datetime.now()

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
        elif "Fail" in data['Message'] or "fail" in data['Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data['Message'] == "Job completed successfully.":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            print("\n- %s job execution time: %s" % (job_id,str(current_time)[0:7]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", percent completion is: \"%s\"" % (data['Message'],data['PercentComplete']))
            time.sleep(10)

def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
            time.sleep(5)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data['Message'] == "Task successfully scheduled.":
            if args["r"] == "n":
                print("\n- WARNING, config job marked as scheduled, system will now reboot to apply configuration changes")
            elif args["r"] == "l":
                print("\n- WARNING, staged config job marked as scheduled, next manual reboot of system will apply configuration changes\n")
            else:
                pass
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data['Message'])

def reboot_server():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
    payload = {'ResetType': 'ForceOff'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power OFF server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power OFF server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    time.sleep(10)
    payload = {'ResetType': 'On'}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()




if __name__ == "__main__":
    check_supported_idrac_version()
    if args["n"]:
        get_network_devices()
    elif args["E"]:
          script_examples()
    elif args["g"]:
        generate_payload_dictionary_file()
    elif args["d"]:
        get_detail_network_device_info()
    elif args["P"]:
        get_network_device_port_info()
    elif args["a"]:
        get_network_device_properties()
    elif args["s"]:
        set_network_properties()     
        if job_type == "n":
            create_next_boot_config_job()
            get_job_status()
            reboot_server()
            loop_job_status()
        elif job_type == "l":
            create_next_boot_config_job()
            get_job_status()
        elif job_type == "s" and args["st"] and args["dt"]:
            create_schedule_config_job()
    else:
        print("\n- FAIL, missing argument(s) or incorrect argument(s) passed in")
            
        


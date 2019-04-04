#
# ChangeBiosBootOrderDMTF_REDFISH. Python script using Redfish API DMTF standard to change the BIOS boot order
#
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

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF standard to change the BIOS boot order")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
#parser.add_argument('script_examples',action="store_true",help='BiosSetAttributeREDFISH.py -ip 192.168.0.120 -u root -p calvin -a MemTest -v Disabled, this example will set one BIOS attribute. BiosSetAttributeREDFISH.py -ip 192.168.0.120 -u root -p calvin -an LogicalProc,EmbSata -av Disabled,AhciMode, this example is setting multiple BIOS attributes')
parser.add_argument('-g', help='Get current boot order, pass in \"y\"', required=False)
parser.add_argument('-c', help='Change boot order, pass in the Id of the boot device(s). You can pass in one, multiple or all. If you only pass in one device Id, the rest of the boot order will get moved down. Note: If you pass in multiple, use a comma separator. Example: Boot0004,Boot0005,Boot0006', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_current_boot_order():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    current_boot_mode=data[u'Attributes']['BootMode']
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootOptions' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    boot_device_display_name = ""
    boot_device_id = ""
    count = 0
    print("\n- Current boot order detected for BIOS boot mode \"%s\" -\n" % current_boot_mode) 
    for i in data[u'Members']:
        for ii in i.items():
            response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            for i in data.items():
                if i[0] == "DisplayName":
                    boot_device_display_name = i[1]
                if i[0] == "Id":
                    boot_device_id = i[1]
            if boot_device_display_name != "" and boot_device_id != "":
                print("SequenceNumber: %s, DisplayName: %s, Id: %s" % (count, boot_device_display_name, boot_device_id))
                count+=1
    sys.exit()
    
    
def change_boot_order():
    global job_id
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    current_boot_mode=data[u'Attributes']['BootMode']
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip
    if "," in args["c"]:
        boot_order_ids = args["c"].split(",")
    else:
        boot_order_ids = [args["c"]]
    payload = {"Boot":{"BootOrder":boot_order_ids}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    status_code = response.status_code
    data = response.json()
    if status_code == 200 or status_code == 202:
        print("\n- PASS: PATCH command passed to change %s boot order sequence" % current_boot_mode)
    else:
        print("\n- FAIL, PATCH command failed to change %s boot order sequence, status code is %s" % (current_boot_mode, status_code))
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers PATCH response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID \"%s\" successfuly created to change %s boot order sequence" % (job_id, current_boot_mode))
    
def get_job_status_scheduled():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            pass
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data[u'Message'])                                                                      

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data[u'PowerState'])
    if data[u'PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to gracefully power OFF server, code return is %s" % statusCode)
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data[u'PowerState'] == "Off":
                print("- PASS, GET command passed to verify server is in OFF state")
                break
            else:
                continue
            
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
    elif data[u'PowerState'] == "Off":
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
    

   

def loop_job_status_final():
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
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        elif data[u'Message'] == "Job completed successfully.":
            print("\n- Final detailed job results -")
            print("\n JobID = "+data[u'Id'])
            print(" Name = "+data[u'Name'])
            print(" Message = "+data[u'Message'])
            print(" PercentComplete = "+str(data[u'PercentComplete'])+"\n")
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\"" % data[u'Message'])
            time.sleep(30)


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_current_boot_order()
    elif args["c"]:
        change_boot_order()
        get_job_status_scheduled()
        reboot_server()
        loop_job_status_final()
        get_current_boot_order()



#
# BiosDeviceRecoveryREDFISH. Python script using Redfish API with OEM extension to recover the BIOS
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to recover the server BIOS. This script should be executed when the server BIOS gets corrupted causing POST to not complete.")
parser.add_argument('script_examples',action="store_true",help='BiosDeviceRecoveryREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will recover the server BIOS. NOTE: During this process, server will power OFF, power ON, recover the BIOS firmware, reboot and process will be complete.')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "DeviceRecovery" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def bios_device_recovery():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellBIOSService/Actions/DellBIOSService.DeviceRecovery' % (idrac_ip)
    method = "DeviceRecovery"
    payload={"Device":"BIOS"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    

def get_idrac_time():
    global current_idrac_time
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":True}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        #print("\n-PASS: POST command passed for %s action GET iDRAC time, status code 200 returned\n" % method)
        pass
    else:
        print("\n-FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            current_idrac_time = i[1]
    strip_timezone=current_idrac_time.find("-")
    strip_timezone=current_idrac_time.find("-", strip_timezone+1)
    strip_timezone=current_idrac_time.find("-", strip_timezone+1)
    current_idrac_time = current_idrac_time[:strip_timezone]
    time.sleep(10)


def validate_process_started():
    global start_time
    global t1
    start_time=datetime.now()
    count = 0
    while True:
        if count == 10:
            print("- FAIL, unable to validate the recovery operation has initiated. Check server status, iDRAC Lifecycle logs for more details")
            sys.exit()
        else:
            try:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
            except requests.ConnectionError as error_message:
                print("- FAIL, GET requests failed to check LC logs for validating recovery process started, detailed error information: \n%s" % error_message)
                sys.exit()
            data = response.json()
            for i in data['Members']:
                for ii in i.items():
                    if ii[1] == "UEFI0298":
                        #current_idrac_time = "2019-12-16T17:18:11"
                        message_id_timestamp = i['Created']
                        strip_timezone=message_id_timestamp.find("-")
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        message_id_timestamp_start = message_id_timestamp[:strip_timezone]
                        t1 = datetime.strptime(current_idrac_time, "%Y-%m-%dT%H:%M:%S")
                        t2 = datetime.strptime(message_id_timestamp_start, "%Y-%m-%dT%H:%M:%S")
                        if t2 > t1:
                            print("\n- PASS, recovery operation initiated successfully. The system will automatically turn OFF, turn ON to recovery the BIOS. Do not reboot server or remove power during this time.")
                            time.sleep(10)
                            return
                    else:
                      pass
            count+=1
            time.sleep(10)
    
def validate_process_completed():
    count = 0
    while True:
        if count == 100:
            print("- FAIL, unable to validate the recovery operation has completed. Check server status, iDRAC Lifecycle logs for more details")
            sys.exit()
        else:
            try:
                response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
            except requests.ConnectionError as error_message:
                if "Max retries exceeded with url" in str(error_message):
                    print("- WARNING, max retries exceeded with URL error, retry GET command")
                    time.sleep(10)
                    continue
                else:
                    print("- WARNING, GET command failed to query LC Logs, validate recovery process completed. Detail error results: %s" % error_message)
                    sys.exit()   
            data = response.json()
            for i in data['Members']:
                for ii in i.items():
                    if ii[1] == "UEFI0299":
                        message_id_timestamp = i['Created']
                        strip_timezone=message_id_timestamp.find("-")
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        strip_timezone=message_id_timestamp.find("-", strip_timezone+1)
                        message_id_timestamp_start = message_id_timestamp[:strip_timezone]
                        t2 = datetime.strptime(message_id_timestamp_start, "%Y-%m-%dT%H:%M:%S")
                        if t2 > t1:
                            print("\n- PASS, recovery operation completed successfully")
                            sys.exit()
                    else:
                      pass
            print("- WARNING, recovery operation is still executing, current execution process time: %s" % str(datetime.now()-start_time)[0:7]) 
            count+=1
            time.sleep(30)
    
            

    

if __name__ == "__main__":
    check_supported_idrac_version()
    get_idrac_time()
    bios_device_recovery()
    validate_process_started()
    validate_process_completed()
    
    
        
            
        
        

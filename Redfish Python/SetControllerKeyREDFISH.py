#
# SetControllerKeyREDFISH. Python script using Redfish API with OEM extension to set the storage controller key (enable encryption)
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to set the storage controller key 'enable encryption'")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SetControllerKeyREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will return storage controller FQDDs detected. SetControllerKeyREDFISH.py -ip 192.168.0.120 -u root -p calvin -e RAID.Slot.6-1 -k Test123## -i testkey, this example is setting the controller key for RAID.Slot.6-1 controller') 
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-g', help='Get current controller encryption mode settings, pass in controller FQDD, Example \"RAID.Slot.6-1\"', required=False)
parser.add_argument('-e', help='Set the controller key, pass in controller FQDD, Example \"RAID.Slot.6-1\"', required=False)
parser.add_argument('-k', help='Pass in unique key passpharse for setting controller key. Minimum length is 8 characters, must have at least 1 upper and 1 lowercase, 1 number and 1 special character Example \"Test123##\". Refer to Dell PERC documentation for more information.', required=False)
parser.add_argument('-i', help='Pass in unique key id name for setting the controller key, Example \"H730key\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
    

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'].split("/")[-1])
        print(i[u'@odata.id'].split("/")[-1])
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
    else:
        pass
    sys.exit()

def get_controller_encryption_setting():
    test_valid_controller_FQDD_string(args["g"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["g"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    try:
        print("\n- Encryption Mode Settings for controller %s -\n" % args["g"])
        print("EncryptionMode: %s" % data[u'Oem'][u'Dell'][u'DellController'][u'EncryptionMode'])
        print("EncryptionCapability: %s" % data[u'Oem'][u'Dell'][u'DellController'][u'EncryptionCapability'])
        print("SecurityStatus: %s" % data[u'Oem'][u'Dell'][u'DellController'][u'SecurityStatus'])
    except:
        print("- FAIL, invalid controller FQDD string passed in")
    


def set_controller_key():
    global job_id
    method = "SetControllerKey"
    test_valid_controller_FQDD_string(args["e"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["e"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if data[u'Oem'][u'Dell'][u'DellController'][u'SecurityStatus'] == "EncryptionNotCapable":
        print("\n- WARNING, storage controller %s does not support encryption" % args["e"])
        sys.exit()
    else:
        pass
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.SetControllerKey' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"TargetFQDD":args["e"],"Key":args["k"],"Keyid":args["i"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n-PASS: POST command passed to set the controller key for controller %s" % args["e"])
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created for storage method \"%s\"" % (job_id, method)) 
    else:
        print("\n-FAIL, POST command failed to set the controller key for controller %s" % args["e"])
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

def check_controller_key_set():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["e"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if data[u'Oem'][u'Dell'][u'DellController'][u'SecurityStatus'] == "SecurityKeyAssigned":
        print("\n- PASS, encryption enabled for storage controller %s " % args["e"])
    else:
        print("\n- FAIL, encryption not enabled for storage controller %s, current security status is \"%s\"" % (args["e"], data[u'Oem'][u'Dell'][u'DellController'][u'SecurityStatus']))
    sys.exit()

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
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or data[u'JobState'] == "Failed":
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(3)

def test_valid_controller_FQDD_string(x):
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, x),verify=False,auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        print("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string value is case sensitive)")
        sys.exit()
    else:
        pass
    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["g"]:
        get_controller_encryption_setting()
    elif args["e"] and args["k"] and args["i"]:
        set_controller_key()
        loop_job_status()
        check_controller_key_set()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
        
    
        
            
        
        

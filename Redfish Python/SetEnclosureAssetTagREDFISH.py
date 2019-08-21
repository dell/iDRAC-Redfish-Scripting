#
# SetEnclosureAssetTagREDFISH. Python script using Redfish API to either get controllers / external enclosures or set external enclosure asset tag.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get controllers / external enclosures or set external enclosure asset tag")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-c', help='Get server storage controllers, pass in \"y\". To get detailed controller information, pass in \"yy\"', required=False)
parser.add_argument('-e', help='Get external enclosures for controller, pass in storage controller FQDD, Example "\RAID.Slot.1-1\"', required=False)
parser.add_argument('--asset', help='Get current external enclosure asset tag, pass in external enclosure FQDD. Example "\Enclosure.External.0-0:RAID.Slot.5-1\"', required=False)
parser.add_argument('-x', help='Set external enclosure asset tag, pass in external enclosure FQDD. Example "\Enclosure.External.0-0:RAID.Slot.5-1\"', required=False)
parser.add_argument('-a', help='Set external enclosure asset tag, pass in asset tag value to set. You must use argument -x along with -a', required=False)
parser.add_argument('-j', help='Pass in config job type. Pass in \"r\" to execute in real time or now. Pass in \"s\" to execute staged or reboot the server to apply changes. You must use argument -x along with -a', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["e"]:
    controller=args["e"]
elif args["asset"]:
    external_enclosure=args["asset"]
elif args["x"] and args["a"] and args["j"]:
    external_enclosure=args["x"]
    asset_tag=args["a"]
    job_type=args["j"]



def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
        print(i[u'@odata.id'][46:])
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
    

def get_external_enclosures():
    response = requests.get('https://%s/redfish/v1/Chassis/' % (idrac_ip),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    new=data.values()
    supported_enclosures=[]
    for i in new:
        if type(i) == list:
            for ii in i:
                for iii in ii.items():
                    if controller in iii[1] and "External" in iii[1]:
                        supported_enclosures.append(iii[1])
    if supported_enclosures == []:
        print("\n- WARNING, no supported external enclosures detected for controller %s" % controller)
    else:
        print("\n- Supported External Enclosures to Set Asset Tag for controller %s -\n" % controller)
        for i in supported_enclosures:
            i=re.sub("/redfish/v1/Chassis/","",i)
            print(i)

def get_external_enclosure_current_asset_tag():
    response = requests.get('https://%s/redfish/v1/Chassis/%s' % (idrac_ip, external_enclosure),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    asset_tag = data["AssetTag"]
    if asset_tag == "":
        print("\n- WARNING, current asset tag for %s is blank" % external_enclosure)
    else:
        print("\n- WARNING, current asset tag for %s is: %s" % (external_enclosure, asset_tag))
    sys.exit()
    


def set_enclosure_asset_tag():
    global job_id
    global job_type
    url = 'https://%s/redfish/v1/Chassis/%s/Settings' % (idrac_ip, external_enclosure)
    payload={"AssetTag":asset_tag}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: PATCH command passed to set asset tag pending value to \"%s\", status code 200 returned" % asset_tag)
    else:
        print("\n- FAIL, PATCH command failed, status code is %s, failure is:\n%s" % (response.status_code, data))
        sys.exit()


def create_realtime_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Chassis/%s/Settings' % (idrac_ip, external_enclosure)
    
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"Immediate"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=('root','calvin'))
    statusCode = response.status_code
    if response.status_code == 202:
        print("\n- PASS: PATCH command passed to create real time config job, status code 202 returned")
    else:
        print("\n- FAIL, PATCH command failed, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("\n- PASS, %s real time jid successfully created\n" % (job_id))

def create_staged_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Chassis/%s/Settings' % (idrac_ip, external_enclosure)
    
    payload = {"@Redfish.SettingsApplyTime":{"ApplyTime":"OnReset"}}
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=('root','calvin'))
    statusCode = response.status_code
    if response.status_code == 202:
        print("\n- PASS: PATCH command passed to create staged config job, status code 202 returned")
    else:
        print("\n- FAIL, PATCH command failed, status code is %s" % response.status_code)
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    x=response.headers["Location"]
    try:
        job_id=re.search("JID.+",x).group()
    except:
        print("\n- FAIL, unable to create job ID")
        sys.exit()
    print("\n- PASS, %s staged jid successfully created\n" % (job_id))
    


start_time=datetime.now()

def loop_job_status():
    start_time = datetime.now()
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
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            print("- WARNING, job creation to completion time is: %s" % str(datetime.now()-start_time)[0:7])
            break
        else:
            print("- WARNING, JobStatus not completed, current status is: \"%s\", percent completion is: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            print("\n- WARNING, current job execution time is: %s" % str(datetime.now()-start_time)[0:7])
            time.sleep(1)

def get_job_status():
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 200:
            #print("- PASS, Command passed to check job status, code 200 returned")
            time.sleep(5)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data[u'Message'] == "Task successfully scheduled.":
            print("\n- WARNING, staged config job marked as scheduled, rebooting the system\n")
            break
        else:
            print("- WARNING: JobStatus not scheduled, current status is: %s" % data[u'Message'])

                                                                          
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
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=('root','calvin'))
    statusCode = response.status_code
    if statusCode == 204:
        print("\n- PASS, Command passed to power ON server, code return is %s\n" % statusCode)
    else:
        print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()

def get_new_external_enclosure_current_asset_tag():
    response = requests.get('https://%s/redfish/v1/Chassis/%s' % (idrac_ip, external_enclosure),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    asset_tag_new = data["AssetTag"]
    if asset_tag_new == asset_tag:
        print("\n- PASS, asset tag successfully set to \"%s\"" % asset_tag_new)
    else:
        print("\n- FAIL, asset tag not set to %s, current value is %s" % (asset_tag, asset_tag_new))
    sys.exit()


if __name__ == "__main__":
    if args["c"]:
        get_storage_controllers()
    elif args["e"]:
        get_external_enclosures()
    elif args["asset"]:
        get_external_enclosure_current_asset_tag()
    elif args["x"] and args["a"]:
        set_enclosure_asset_tag()
        if job_type == "r":
            create_realtime_config_job()
            loop_job_status()
            get_new_external_enclosure_current_asset_tag()
        elif job_type == "s":
            create_staged_config_job()
            get_job_status()
            reboot_server()
            loop_job_status()
            get_new_external_enclosure_current_asset_tag()
        


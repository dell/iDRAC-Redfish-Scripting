#
# UnpackAndAttachOsdREDFISH. Python script using Redfish API with OEM extension to either get driver pack information, unpack and attach driver pack or detach driver pack
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension either to get driver pack information, unpack and attach driver pack or detach driver pack")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example to get current driver pack list. UnpackAndAttachOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin -U \"Microsoft Windows Server 2012 R2\". This example will unpack and attach Windows Server 2012 driver pack')
parser.add_argument('-g', help='Get driver pack information, pass in \"y\"', required=False)
parser.add_argument('-a', help='Get attach status for driver pack, pass in \"y\"', required=False)
parser.add_argument('-U', help='Unpack and attach driver pack, pass in the operating system(OS) string. Example: pass in \"Microsoft Windows Server 2012 R2\"(make sure to pass double quotes around the string value)', required=False)
parser.add_argument('-d', help='Detach driver pack, pass in \"y\"', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass



def get_driver_pack_info():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetDriverPackInfo' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS: POST command passed to get driver pack information, status code 200 returned")
    else:
        print("\n- FAIL, POST command failed to get driver pack information, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    print("\n- Driver packs supported for iDRAC %s\n" % idrac_ip)
    for i in data[u'OSList']:
        i=i.replace("\n","")
        print(i)

def get_attach_status():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS: POST command passed to get driver pack attach status, status code 200 returned")
    else:
        print("\n- FAIL, POST command failed to get driver pack attach status, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    print("- WARNING, Current driver pack attach status: %s" % data[u'DriversAttachStatus'])


    
def unpack_and_attach_driver_pack():
    global concrete_job_uri
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.UnpackAndAttach' % (idrac_ip)
    method = "UnpackAndAttach"
    headers = {'content-type': 'application/json'}
    payload={"OSName":args["U"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    #print(dir(response))
    #print(response.headers)
    concrete_job_uri = response.headers[u'Location']
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        concrete_job_uri = response.headers[u'Location']
        print("- WARNING, concrete job URI created for method %s: %s\n" % (method, concrete_job_uri))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    

def detach_driver_pack():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachDrivers' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS: POST command passed to detach driver pack, status code 200 returned")
    else:
        print("\n- FAIL, POST command failed to detach driver pack, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()


    
def check_concrete_job_status():
    #concrete_job_uri = "/redfish/v1/TaskService/Tasks/OSDeployment"
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s%s' % (idrac_ip, concrete_job_uri), auth=(idrac_username, idrac_password), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
        statusCode = req.status_code
        if statusCode == 200 or statusCode == 202:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data= req.json()
        #print(data[u'TaskState'])
        #print(data[u'Messages'][0][u'Message'])
        #sys.exit()

        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif data[u'TaskState'] == "Completed":
            if "Fail" in data[u'Messages'][0][u'Message'] or "fail" in data[u'Messages'][0][u'Message']:
                print("- FAIL: concrete job failed, detailed error results: %s" % data.items())
                sys.exit()
        
            elif "completed successful" in data[u'Messages'][0][u'Message'] or "command was successful" in data[u'Messages'][0][u'Message']:
                print("\n- PASS, concrete job successfully marked completed")
                print("\n- Final detailed job results -\n")
                for i in data.items():
                    if '@odata.type' in i[0]:
                        pass
                    elif i[0] == u'Messages':
                        for ii in i[1][0].items():
                            print("%s: %s" % (ii[0], ii[1]))   
                    else:
                        print("%s: %s" % (i[0], i[1]))
                print("\n- Concrete job completed in %s\n" % (current_time))
                break
            else:
                print("- FAIL, unable to get final concrete job message string")
                sys.exit()
        elif data[u'TaskState'] == "Exception":
            print("\n- FAIL, final detailed job results -\n")
            for i in data.items():
                if '@odata.type' in i[0]:
                    pass
                elif i[0] == u'Messages':
                    for ii in i[1][0].items():
                        print("%s: %s" % (ii[0], ii[1]))   
                else:
                    print("%s: %s" % (i[0], i[1]))
            sys.exit()
        else:
            print("- WARNING, concrete job not completed, current status is: \"%s\", job execution time is \"%s\"" % (data[u'TaskState'], current_time))
            #print(data)
            time.sleep(3)    
    
def check_attach_status(x):
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, POST command failed to get driver pack attach status, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    if data[u'DriversAttachStatus'] == x:
        print("- PASS, driver pack attach status successfully identified as \"%s\"" % x)
    else:
        print("- FAIL, driver pack attach status not successfully identified as %s" % x)
        sys.exit()



    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_driver_pack_info()
    elif args["a"]:
        get_attach_status()
    elif args["U"]:
        unpack_and_attach_driver_pack()
        check_concrete_job_status()
        check_attach_status("Attached")
    elif args["d"]:
        detach_driver_pack()
        check_attach_status("NotAttached")
    else:
        print("\n- FAIL, either missing required parameter(s) or incorrect parameter value(s)")
    
        
        
    
    
        
            
        
        

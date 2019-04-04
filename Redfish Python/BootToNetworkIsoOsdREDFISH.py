#
# BootToNetworkIsoOsdREDFISH. Python script using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='BootToNetworkIsoOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example to get current network ISO attach status. BootToNetworkIsoOsdREDFISH.py -ip 192.168.0.120 -u root -p calvin -b y --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --imagename esxi-6.0.0.iso, this example will boot to network ISO on NFS share')
parser.add_argument('-a', help='Get attach status for network ISO, pass in \"y\"', required=False)
parser.add_argument('-b', help='Boot to network ISO, pass in \"y\". You must also pass in network share arguments', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS and CIFS', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--imagename', help='Pass in the operating system(OS) string you want to boot from on your network share', required=False)
parser.add_argument('-d', help='Detach network ISO, pass in \"y\"', required=False)



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





def get_attach_status():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed to get ISO attach status, status code 200 returned")
    else:
        print("\n- FAIL, POST command failed to get ISO attach status, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    print("- WARNING, Current ISO attach status: %s" % data[u'ISOAttachStatus'])


    
def boot_to_network_iso():
    global concrete_job_uri
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.BootToNetworkISO' % (idrac_ip)
    method = "BootToNetworkISO"
    headers = {'content-type': 'application/json'}
    payload={}
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["imagename"]:
        payload["ImageName"] = args["imagename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    print("\n- WARNING, arguments and values used to %s on network share\n" % method)
    for i in payload.items():
          print("%s: %s" % (i[0],i[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
        concrete_job_uri = response.headers[u'Location']
        print("- WARNING, concrete job URI created for method %s: %s\n" % (method, concrete_job_uri))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    

def detach_network_iso():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachISOImage' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed to detach ISO image, status code 200 returned")
    else:
        print("\n- FAIL, POST command failed to detach ISO image, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()


    
def check_concrete_job_status():
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
                print("\n- concrete job completed in %s" % (current_time))
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
            time.sleep(5)    
    
def check_attach_status(x):
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        pass
    else:
        print("\n- FAIL, POST command failed to get ISO attach status, status code is %s" % (response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    if data[u'ISOAttachStatus'] == x:
        print("- PASS, ISO attach status successfully identified as \"%s\"" % x)
    else:
        print("- FAIL, ISO attach status not successfully identified as %s" % x)
        sys.exit()



    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["a"]:
        get_attach_status()
    elif args["b"] and args["b"] and args["ipaddress"] and args["sharetype"] and args["sharename"]:
        boot_to_network_iso()
        check_concrete_job_status()
        check_attach_status("Attached")
    elif args["d"]:
        detach_network_iso()
        check_attach_status("NotAttached")
    else:
        print("\n- FAIL, either missing parameter(s) or invalid parameter value(s) passed in. If needed, review help text for script examples")
        
    
        
        
    
    
        
            
        
        

#
# ExportServerScreenShotOemREDFISH. Python script using Redfish API with OEM extension to export current server screen shot
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


import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export either last crash screen or server screen shot. NOTE: This image will be exported in base64 format to a file. You will need to take this content and use a utility which can convert base64 to PNG.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportServerScreenShotOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -f 2, this example will export a screenshot of the current server status.')
parser.add_argument('-f', help='Pass in the filetype to export. Either \"0\" for LastCrashScreenShot, \"1\" for Preview or \"2\" for ServerScreenShot', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("export_screenshot.txt")
except:
    pass


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "ExportServerScreenShot" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def export_server_screen_shot():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportServerScreenShot' % (idrac_ip)
    method = "ExportServerScreenShot"
    headers = {'content-type': 'application/json'}
    payload={}
    if args["f"] == "0":
        payload["FileType"] = "LastCrashScreenShot"
    elif args["f"] == "1":
        payload["FileType"] = "Preview"
    elif args["f"] == "2":
        payload["FileType"] = "ServerScreenShot"
    else:
        print("- FAIL, invalid value passed in for argument -f")
        sys.exit()
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
          print("%s: %s" % (i[0],i[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    print(data.keys())
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code %s returned" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    with open("export_screenshot.txt","w") as x:
        x.writelines(data['ServerScreenShotFile'])
    print("\n- PASS, screenshot exported locally to file \"export_screenshot.txt\". Take the contents and copy to a utility which can convert base64 into PNG file to view the screenshot")
    
    



            

    

if __name__ == "__main__":
    if args["f"]:
        check_supported_idrac_version()
        export_server_screen_shot()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    
    
        
            
        
        

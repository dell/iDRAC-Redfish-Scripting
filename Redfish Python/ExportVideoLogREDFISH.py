#
# ExportVideoLogREDFISH. Python script using Redfish API with OEM extension to export either boot capture videos or crash capture video locally.
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


import requests, json, sys, re, time, warnings, argparse, webbrowser

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to export either boot capture videos or crash capture video locally.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportVideoLogEDFISH.py -ip 192.168.0.120 -u root -p calvin -f 1, this example will download iDRAC boot capture videos locally in a zip file using your default browser.')
parser.add_argument('-f', help='Pass in the filetype to export locally. Either \"1\" for BootCaptureVideo or \"2\" for CrashCaptureVideo. Note: script will prompt you to save the zip file locally using your default browser. Extract the video files(dvc format) from the zip to view them.', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


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
        if "ExportVideoLog" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def export_video_log():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportVideoLog' % (idrac_ip)
    method = "ExportVideoLog"
    headers = {'content-type': 'application/json'}
    payload={}
        
    headers = {'content-type': 'application/json'}
    payload={"ShareType":"Local"}
    if args["f"] == "1":
        payload["FileType"] = "BootCaptureVideo"
    elif args["f"] == "2":
        payload["FileType"] = "CrashCaptureVideo"
    else:
        print("- FAIL, invalid value passed in for argument -f")
        sys.exit()
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
          print("%s: %s" % (i[0],i[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    time.sleep(10)
    try:
        video_log_capture_zip_uri = response.headers['Location']
    except:
        print("- FAIL, unable to locate video capture URI in POST response output")
        sys.exit()
    while True:
        request = raw_input("\n* Would you like to open browser session to download video capture zip file? Type \"y\" to download or \"n\" to not download: ")
        if request == "y":
            webbrowser.open('https://%s%s' % (idrac_ip, video_log_capture_zip_uri))
            print("\n- WARNING, check you default browser session for downloaded video capture zip file. If needed to watch the video capture files(dvc format), download the video player from the iDRAC GUI/Maintenance/Troubleshooting page.")
            break
        elif request == "n":
            break
        else:
            print("\n- FAIL, incorrect value passed in for request")
        
    
    


            

    

if __name__ == "__main__":
    if args["f"]:
        check_supported_idrac_version()
        export_video_log()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")

    
    
        
            
        
        

#
# BackupRestoreImageREDFISH. Python script using Redfish API with OEM extension to either backup or restore the server profile.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either backup or restore the server profile.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-b', help='Backup image to either network share or vflash, pass in \"y\"', required=False)
parser.add_argument('-r', help='Restore image from either network share or vflash, pass in \"y\"', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS, VFLASH. Note: passing in a value of VFLASH will backup the image to VFLASH iDRAC card.', required=False)
parser.add_argument('--sharename', help='Pass in the network share share name', required=False)
parser.add_argument('--username', help='Pass in the CIFS username', required=False)
parser.add_argument('--password', help='Pass in the CIFS username pasword', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--scheduledstarttime', help='Start time for the job execution in format: yyyymmddhhmmss. Pass in value of "TIME_NOW" to start the job immediately', required=False)
parser.add_argument('--passphrase', help='Pass in a passphrase to be applied to a backup file. This is optional for backup but if you apply it to a backup file, this will be required to pass in for restore operation', required=False)
parser.add_argument('--preservevdconfig', help='Restore argument only. Pass in value of True if you want to preserve current virtual disk configuration. Pass in False if you want to restore the virtual disk configuration from the backup file', required=False)
parser.add_argument('--imagename', help='Pass in unique file name string for the backup file image. If running restore, pass in the backup file image', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are Off and On. This argument is only required if using HTTPS for share type', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass




def backup_restore_image():
    global job_id
    global method
    if args["b"]:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.BackupImage' % (idrac_ip)
        method = "BackupImage"
    if args["r"]:
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.RestoreImage' % (idrac_ip)
        method = "RestoreImage"
        
    headers = {'content-type': 'application/json'}
    payload={}
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"].upper()
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["imagename"]:
            payload["ImageName"] = args["imagename"]
    if args["username"]:
        payload["Username"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["scheduledstarttime"] == "time_now":
        payload["ScheduledStartTime"] = args["scheduledstarttime"].upper()
    else:
        payload["ScheduledStartTime"] = args["scheduledstarttime"]
    if args["passphrase"]:
        payload["Passphrase"] = args["passphrase"]
    if args["preservevdconfig"]:
        payload["PreserveVDConfig"] = args["preservevdconfig"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertWarning"] = args["ignorecertwarning"]
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
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))
    

def loop_job_status():
    start_time=datetime.now()
    while True:
        try:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        except:
            if method == "RestoreImage":
                print("- WARNING, either iDRAC reset due to restore job getting marked completed or lost iDRAC network connection. Check the overall job queue for the job ID status")
                sys.exit()
            else:
                print("- WARNING, lost iDRAC network connection. Check the overall job queue for the job ID status")
                sys.exit()
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            try:
                print("Extended Info Message: {0}".format(req.json()))
                sys.exit()
            except:
                if method == "RestoreImage":
                    print("- WARNING, either iDRAC reset due to restore job getting marked completed or lost iDRAC network connection. Check the overall job queue for the job ID status")
                    sys.exit()
                else:
                    print("- WARNING, lost iDRAC network connection. Check the overall job queue for the job ID status")
                    sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit()
        if data[u'JobState'] == "Failed" or "Fail" in data[u'Message'] or "Unable" in data[u'Message'] or "Invalid" in data[u'Message'] or "fail" in data[u'Message'] or "Cannot" in data[u'Message'] or "cannot" in data[u'Message']:
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        if method == "BackupImage":
            if data[u'Message'] == "Export System Profile completed." and data[u'JobState'] == "Completed":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                        pass
                    else:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                pass
        else:
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(5)
            continue
        if method == "RestoreImage":
            if data[u'Message'] == "Import System Profile Complete, restarting Integrated Remote Access Controller." and data[u'JobState'] == "Completed":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                        pass
                    else:
                        print("%s: %s" % (i[0],i[1]))
                break
            else:
                pass
                
        else:
            print("- WARNING, JobStatus not completed, current status: \"%s\", percent complete: \"%s\"" % (data[u'Message'],data[u'PercentComplete']))
            time.sleep(5)
            continue
        
    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["b"] or args["r"]:
        backup_restore_image()
        loop_job_status()
    
    
        
            
        
        

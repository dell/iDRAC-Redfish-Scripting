#
# DeleteJobQueueREDFISH.py  Python script using Redfish API with OEM extension to get either delete single job ID, delete complete job queue or delete job queue and restart Lifecycle Controller services.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get either delete single job ID, delete complete job queue or delete job queue and restart Lifecycle Controller services.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('script_examples',action="store_true",help='DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get current job queue. DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -j JID_852366388723, this example will delete a specific job ID. DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will delete the job queue. DeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -cr y, this example will delete the jobqueue and restart Lifecycle Controller services.')
parser.add_argument('-j', help='Delete single job id, pass in the job ID', required=False)
parser.add_argument('-c', help='Clear the job queue, pass in a value of \"y\"', required=False)
parser.add_argument('-cr', help='Clear the job queue and restart iDRAC Lifecycle Controller services, pass in a value of \"y\". Note: By selecting this option, it will take a few minutes for the Lifecycle Controller to be back in Ready state.', required=False)
parser.add_argument('-g', help='Get current job ids in the job queue, pass in a value of \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def get_job_queue_job_ids():
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobid_search=re.findall("JID_.+?'",data)
    if jobid_search == []:
        print("\n- WARNING, job queue empty, no current job IDs detected for iDRAC %s" % idrac_ip)
        sys.exit()
    jobstore=[]
    for i in jobid_search:
        i=i.strip("'")
        jobstore.append(i)
    print("\n- Current job IDs in the job queue for iDRAC %s:\n" % idrac_ip)
    for i in jobstore:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip,i), auth=(idrac_username, idrac_password), verify=False)
        data = req.json()
        print("-" * 80)
        print("Job ID: %s\nJob Type: %s\nJob Message: %s\n" % (i,data['Name'], data['Message']))
        


def delete_jobID():
    url = "https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % idrac_ip
    headers = {'content-type': 'application/json'}
    if args["j"]:
        payload = {"JobID":args["j"]}
    elif args["c"]:
        payload = {"JobID":"JID_CLEARALL"}
    elif args["cr"]:
        payload = {"JobID":"JID_CLEARALL_FORCE"}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        if args["j"]:
            print("\n- PASS: DeleteJobQueue action passed to clear job ID \"%s\", status code 200 returned" % args["j"])
        elif args["c"]:
            print("\n- PASS: DeleteJobQueue action passed to clear the job queue, status code 200 returned")
        elif args["cr"]:
            print("\n- PASS: DeleteJobQueue action passed to clear the job queue and restart Lifecycle Controller services, status code 200 returned")
            time.sleep(10)
            
    else:
        print("\n- FAIL, DeleteJobQueue action failed, status code is %s" % (response.status_code))
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    if args["cr"]:
        print("\n- WARNING, Lifecycle Controller services restarted. Script will loop checking the status of Lifecycle Controller until Ready state")
        time.sleep(60)
        while True:
            url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.GetRemoteServicesAPIStatus' % (idrac_ip)
            method = "GetRemoteServicesAPIStatus"
            headers = {'content-type': 'application/json'}
            payload={}
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
            data=response.json()
            if response.status_code == 200:
                pass
            else:
                print("\n-FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
                data = response.json()
                print("\n-POST command failure results:\n %s" % data)
                sys.exit()
            lc_status = data["LCStatus"]
            server_status = data["Status"]
            if lc_status == "Ready" and server_status == "Ready":
                print("\n- PASS, Lifecycle Controller services are in ready state")
                sys.exit()
            else:
                print("- WARNING, Lifecycle Controller services not in ready state, polling again")
                time.sleep(20)
    





                    

if __name__ == "__main__":
    if args["j"] or args["c"] or args["cr"]:
        delete_jobID()
    elif args["g"]:
        get_job_queue_job_ids()
    else:
        print("\n- FAIL, either invalid argument entered or incorrect argument value entered. Check script help text if needed.")
        



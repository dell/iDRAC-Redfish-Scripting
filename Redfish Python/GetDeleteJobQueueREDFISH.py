#
# GetDeleteJobQueueREDFISH. Python script using Redfish API to either get current job IDs, get details for a specific job ID or delete a job ID.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current job IDs, get details for a specific job ID or delete a job ID.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetDeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get current job IDs in the job queue. GetDeleteJobQueueREDFISH.py -ip 192.168.0.120 -u root -p calvin -d JID_442159584605, this example will delete this specific job ID')
parser.add_argument('-g', help='Pass in \"y\" to get current job IDs in the job queue', required=False)
parser.add_argument('-j', help='Get specific job ID details, pass in the job ID', required=False)
parser.add_argument('-d', help='Pass in job ID to delete. To clear the job queue, pass in \"JID_CLEARALL\" for job ID', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

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
        print("Job ID: %s, Job Type: %s, Job Message: %s" % (i,data[u'Name'], data[u'Message']))

def get_job_id_details():
    try:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip,args["j"]), auth=(idrac_username, idrac_password), verify=False)
    except:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, args["j"]), auth=(idrac_username, idrac_password), verify=False)
    data = req.json()
    print("\n- Detailed results for job ID %s\n" % args["j"])
    for i in data.items():
        print("%s: %s" % (i[0], i[1]))


def delete_job_queue():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue' % idrac_ip
    method = "DeleteJobQueue"
    payload = {"JobID":args["d"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    data = response.json()
    if statusCode == 200:
        print("\n- PASS: POST command passed for %s method passing in job ID \"%s\", status code 200 returned" % (method, args["d"]))
    else:
        print("\n- FAIL, Command failed for method %s, status code is %s. Detailed error message is: %s\n" % (statusCode, method, data))
        sys.exit()


    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["d"]:
        delete_job_queue()
    elif args["g"]:
        get_job_queue_job_ids()
    elif args["j"]:
        get_job_id_details()
   
    
    
        
            
        
        

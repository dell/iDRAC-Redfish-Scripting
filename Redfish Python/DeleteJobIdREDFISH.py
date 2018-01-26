#
# DeleteJobIdREDFISH.py  Python script using Redfish API to get either delete single job ID, get current job queue or clear the job queue.
#
# 
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current job queue, delete single job ID or clear the job queue")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('-e', help='Examples of running the script, pass in a value of \"y\"', required=False)
parser.add_argument('-j', help='Delete single job id, pass in the job ID', required=False)
parser.add_argument('-c', help='Clear the job queue, pass in a value of \"y\"', required=False)
parser.add_argument('-q', help='Get current job ids in the job queue, pass in a value of \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

# Function to get executing script examples

def script_examples():
    print("\nDeleteJobIdREDFISH.py -ip 192.168.0.120 -u root -p calvin -j JID_169338747446, example shows deleting a specific job ID")
    print("\nDeleteJobIdREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, example shows clearing the job queue")
    print("\nDeleteJobIdREDFISH.py -ip 192.168.0.120 -u root -p calvin -q y, example shows getting the current job IDs in the job queue")

# Function to get current iDRAC job queue

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
        print("Job ID: %s, Job Type: %s" % (i,data[u'Name']))
        
# Function to clear job queue

def clear_job_queue():
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobstore=re.findall("JID_.+?'",data)
    if jobstore == []:
        print("\n- WARNING, job queue already cleared for iDRAC %s, DELETE command will not execute" % idrac_ip)
        sys.exit()
    print("\n- WARNING, clearing job queue for job IDs: %s\n" % jobstore)
    for i in jobstore:
        i=i.strip("'")
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, i)
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    data = str(data)
    jobstore=re.findall("JID_.+?'",data)
    if jobstore == []:
        print("- PASS, job queue for iDRAC %s successfully cleared" % idrac_ip)
    else:
        print("\n- FAIL, job queue not cleared, current job queue contains jobs: %s" % jobstore)
        sys.exit()
        

# Function to delete iDRAC job ID

def delete_jobID():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, args["j"])
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 200:
        print("\n- PASS: DELETE command passed to clear job ID \"%s\", status code 200 returned" % args["j"])
    else:
        print("\n- FAIL, DELETE command failed to clear job ID %s status code is %s" % (args["j"], response.status_code))
        data = response.json()
        print("\n- POST command failure is:\n %s" % data)
        sys.exit()
    req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip,args["j"]), auth=(idrac_username, idrac_password), verify=False)
    if req.status_code != 404:
        print("\n- FAIL, job id %s still exists in the job queue" % args["j"])
        sys.exit()
    else:
        pass
    

#Run Code

if __name__ == "__main__":
    if args["e"] == "y":
        script_examples()
    elif args["j"]:
        delete_jobID()
    elif args["c"]:
        clear_job_queue()
    elif args["q"]:
        get_job_queue_job_ids()
    else:
        print("\n- FAIL, invalid argument entered")
        sys.exit()



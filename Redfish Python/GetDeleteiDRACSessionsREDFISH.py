#
# GetDeleteiDRACSessionsREDFISH. Python script using Redfish API to either get current iDRAC sessions or delete iDRAC session
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


import requests, json, sys, re, time, warnings, argparse, subprocess

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC sessions or delete an iDRAC session. NOTE: current DMTF doesn't support Type property which this information is needed to know which session you want to delete. As a workaround, you can get this information using remote RACADM command which support has been added in this script.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetDeleteiDRACSessionsREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will return current iDRAC active sessions. GetDeleteiDRACSessionsREDFISH.py -ip 192.168.0.120 -u root -p calvin -d 1982, this example will delete iDRAC session 1982 and validate it has been deleted.')
parser.add_argument('-c', help='Get current iDRAC sessions running and details, pass in \"y\"', required=False)
parser.add_argument('-g', help='Get current iDRAC session IDs using remote RACADM, pass in \"y\". NOTE: Make sure you have remote RACADM installed first which is available to download from Dell support site.', required=False)
parser.add_argument('-d', help='Delete an iDRAC session, pass in the session ID', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

# Function to check supported iDRAC firmware version

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Sessions' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass
    
# Function to get current iDRAC sessions 

def get_current_iDRAC_sessions():
    response = requests.get('https://%s/redfish/v1/Sessions' % (idrac_ip),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    session_uris = []
    print("\n- Current running session(s) detected for iDRAC %s -\n" % idrac_ip) 
    for i in data[u'Members']:
        for ii in i.items():
            print(ii[1])
            session_uris.append(ii[1])
    for i in session_uris:
        print("\n- Detailed information for session URI \"%s\" -\n" % i)
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))

# Function using remote RACADM as workaround to get session type ID

def get_session_id_RACADM():
    racadm_get_ssninfo_command = "racadm -r %s -u %s -p %s --nocertwarn getssninfo" % (idrac_ip, idrac_username, idrac_password)
    try:
        racadm_command = subprocess.Popen(racadm_get_ssninfo_command,stdout=subprocess.PIPE, shell=True).communicate()[0]
        print("\n- Current active sessions for iDRAC %s using RACADM command -\n" % idrac_ip)
        print(racadm_command)
    except:
        print("- FAIL, either remote RACADM is not installed or invalid iDRAC IP address passed in")
    
# Function to delete session

def delete_session():
    url = 'https://%s/redfish/v1/Sessions/%s' % (idrac_ip, args["d"])
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 202 or response.status_code == 200:
        print("\n- PASS: DELETE command passed to delete session id \"%s\", status code %s returned" % (args["d"],response.status_code))
        response = requests.get('https://%s/redfish/v1/Sessions/%s' % (idrac_ip,args["d"]),verify=False,auth=(idrac_username, idrac_password))
        if response.status_code == 404:
            print("- PASS, validation passed to confirm session %s has been deleted" % args["d"])
        else:
            print("- FAIL, validation failed to confirm session %s has been deleted and still exists" % args["d"])
            sys.exit()
    else:
        print("\n- FAIL, DELETE command failed, status code returned is %s" % response.status_code)
        data = response.json()
        print("\n- DELETE command failure is:\n %s" % data)
        sys.exit()
   
        

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"] == "y" or args["c"] == "Y":
        get_current_iDRAC_sessions()
    elif args["g"] == "y" or args["g"] == "Y":
        get_session_id_RACADM()
    elif args["d"]:
        delete_session()
    else:
        print("\n- FAIL, either missing required parameter(s) or incorrect value passed in for parameter(s)")


#
# DeleteFirmwarePackageREDFISH. Python script using Redfish API to delete a downloaded package which has not been applied yet.
# To delete the downloaded package, you must first find out the AVAILABLE URI entry for the download, then the Etag for this URI. You will need to pass in both the complete AVAILABLE URI and Etag
# to delete the downloaded payload.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2017, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API to either get AVAILABLE entries for delete, get ETag for the AVAILABLE entry or DELETE the AVAILABLE downloaded package')
parser.add_argument('-ip', help='iDRAC IP Address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('-a', help='Get AVAILABLE URI entries for delete, pass in lower \"y\"', required=False)
parser.add_argument('-e', help='Get ETag id for AVAILABLE entry which is needed for DELETE command, you must pass in the complete AVAILABLE URI string', required=False)
parser.add_argument('-A', help='Pass in the complete AVAILABLE URI string', required=False)
parser.add_argument('-E', help='Pass in the ETag for the AVAILABLE entry', required=False)
parser.add_argument('-x', help='This will return executing script examples, pass in lower \"y\"', required=False)

args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
available_uri=args["e"]
available_uri_delete=args["A"]
ETag=args["E"]

# Function to get any Available entries for DELETE payload

def get_available_entries():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    l=[]
    for i in data[u'Members']:
        for ii in i.items():
            if "Available" in ii[1]:
                l.append(ii[1])
            else:
                pass
    if l == []:
        print("\n- No AVAILABLE entries for deleting payload")
    else:
        print("\n- Available URI entries for deleting payload:\n")
        for i in l:
            print(i)
    sys.exit()

# Function to get ETag for AVAILABLE URI 

def get_etag():
    req = requests.get('https://%s%s' % (idrac_ip, available_uri), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    ETag = req.headers['ETag']
    print("\n- ETag for URI \"%s\" is: %s" % (available_uri, ETag))
    sys.exit()

# Function to delete download payload

def delete_payload():
    url = 'https://%s%s' % (idrac_ip, available_uri_delete)
    headers = {"if-match": ETag}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS, Successfully deleted payload for URI %s" % available_uri_delete)
    else:
        print("\n- FAIL, command failed to delete AVAILABLE URI %s, error is: \n%s" % (available_uri_delete, data))
    sys.exit()
    
# Function for script examples

def script_examples():
    print("\nExample 1: DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y \"This will return any AVAILABLE downloaded URI entries which can be deleted.\"\nExample: 2: DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin -e /redfish/v1/UpdateService/FirmwareInventory/Available-25806-4301X07 \"This will return the Etag for the AVAILABLE URI entry.\"\nExample 3: DeleteFirmwarePackageREDFISH.py -ip 192.168.0.120 -u root -p calvin -A /redfish/v1/UpdateService/FirmwareInventory/Available-25806-4301X07 -E 4a2ae25594ccaa28535062b7b6d58df0 \"this will delete the payload for the AVAILABLE package\"")
    sys.exit()
# Run code here

while __name__ == "__main__":
    if args["a"] == "y":
        get_available_entries()
    elif args["e"]:
        get_etag()
    elif args["E"] and args["A"]:
        delete_payload()
    elif args["x"] == "y":
        script_examples()
    else:
        print("\nYou must pass in at least one argument when executing the script. If needed, execute script name along with \"-h\" to see all supported arguments.")
        sys.exit()
    



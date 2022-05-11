#!/usr/bin/python
#!/usr/bin/python3
#
# InsertEjectVirtualMediaREDFISH. Python script using Redfish API DMTF to either get virtual media information, insert or eject virtual media
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 5.0
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


import argparse
import getpass
import json
import logging
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get virtual media information, insert or eject virtual media")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False) 
parser.add_argument('--get', help='Get current virtual media information, if any devices are attached.', action="store_true", required=False)
parser.add_argument('--action', help='Pass in the type of action you want to perform. Possible values: insert and eject', required=False)
parser.add_argument('--device', help='Pass in the device you want to insert or eject. Possible values: cd and removabledisk. If attaching removable disk image, it must be .IMG type.', required=False)
parser.add_argument('--uri', help='Insert (attach) virtual media , pass in the HTTP or HTTPS URI path of the remote image. If using CIFS or NFS, pass in the remote image share path for mount. Note: If attaching removable disk, only supported file type is .img', required=False)
parser.add_argument('--username', help='Pass in the share username if your share has auth enabled (auth mandatory for CIFS)', required=False)
parser.add_argument('--password', help='Pass in the share username password if your share has auth enabled (auth mandatory for CIFS)', required=False)
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get current information for CD and removable disk virtual media.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin --action insert --device cd --uri http://192.168.0.130/esxi_5u1.iso, this example shows attaching ISO on HTTP share.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin --action eject --device cd, this example will detach CD ISO.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -x 748547616c93fbf446fd4155995731a2 --action insert --device removabledisk --uri 192.168.0.140:/nfs/idsdm.img, this example using X-auth token session will attach removabledisk image on NFS share.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root --device removabledisk, this example will first prompt to enter iDRAC password, then detach removabledisk image.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin --action insert --device cd --uri 192.168.0.140:/nfs/esxi_5u1.iso, this example will attach ISO on NFS share.
    \n- InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin --action insert --device cd --uri //192.168.0.150/cifs_share/esxi_5u1.iso, this example will attach ISO on CIFS share.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        logging.error("\n- FAIL, either incorrect iDRAC username / password passed in or iDRAC user doesn't have correct privileges")
        sys.exit(0)
    try:
        for i in data['Actions']:
            if i == "#VirtualMedia.InsertMedia" or i == "#VirtualMedia.EjectMedia":
                logging.debug("- PASS, iDRAC supported version detected")
    except:
        logging.error("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)
            
def get_virtual_media_info():
    virtual_media_uris = []
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    logging.info("\n - Virtual Media URIs detected \n")
    for i in data['Members']:
        for ii in i.items():
            print(ii[1])
            virtual_media_uris.append(ii[1])
    for i in virtual_media_uris:
        logging.info("\n- Detailed information for URI \"%s\" \n" % i)
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i), verify=verify_cert, auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            pprint(i)
        
def insert_virtual_media():
    if args["device"].lower() == "cd":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia" % idrac_ip
        media_device = "CD"
    elif args["device"].lower() == "removabledisk":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.InsertMedia" % idrac_ip
        media_device = "Removable Disk"
    else:
        logging.error("- FAIL, invalid value passed in for argument --device")
        sys.exit()
    logging.info("\n - INFO, insert(attached) \"%s\" virtual media device \"%s\"" % (media_device, args["uri"]))
    payload = {'Image': args["uri"], 'Inserted':True,'WriteProtected':True}
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.__dict__
    if response.status_code != 204:
        logging.error("\n- FAIL, POST command InsertMedia action failed, detailed error message: %s" % response._content)
        sys.exit(0)
    else:
        logging.info("\n- PASS, POST command passed to successfully insert(attached) %s media, status code %s returned" % (media_device, response.status_code))

def eject_virtual_media():
    if args["device"].lower() == "cd":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia" % idrac_ip
        media_device = "CD"
    elif args["device"].lower() == "removabledisk":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.EjectMedia" % idrac_ip
        media_device = "Removable Disk"
    else:
        logging.error("- FAIL, invalid value passed in for argument --device")
        sys.exit(0)
    logging.info("\n- INFO, eject(unattached) \"%s\" virtual media device" % (media_device))
    payload = {}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert,auth=(idrac_username,idrac_password))
    data = response.__dict__
    if response.status_code != 204:
        logging.error("\n- FAIL, POST command EjectMedia action failed, detailed error message: %s" % response._content)
        sys.exit(0)
    else:
        logging.info("\n- PASS, POST command passed to successfully eject(unattached) %s media" % media_device)
    
def validate_media_status():
    if args["device"].lower() == "cd":
        url = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD" 
        media_device = "CD"
    elif args["device"].lower() == "removabledisk":
        url = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk"
        media_device = "Removable Disk"
    if args["x"]:
        response = requests.get('https://%s%s' % (idrac_ip, url), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s%s' % (idrac_ip, url), verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    attach_status = data["Inserted"]
    if args["action"] == "1":
        if attach_status == True:
            logging.info("- PASS, GET command passed to verify %s media successfully inserted(attached)" % media_device)
        else:
            logging.error("- FAIL %s media not attached, current status: %s" % attach_status)
            sys.exit(0)
    elif args["action"] == "2":
        if attach_status == False:
            logging.info("- PASS, GET command passed to verify %s media successfully ejected(unattached)" % media_device)
        else:
            logging.error("- FAIL %s media not ejected, current status: %s" % attach_status)
            sys.exit(0)
        

    

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- Argument -p not detected, pass in iDRAC user %s password: " % args["u"])
        if args["ssl"]:
            if args["ssl"].lower() == "true":
                verify_cert = True
            elif args["ssl"].lower() == "false":
                verify_cert = False
            else:
                verify_cert = False
        else:
            verify_cert = False
        check_supported_idrac_version()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get"]:
        get_virtual_media_info()
    elif args["action"].lower() == "insert" and args["device"] and args["uri"]:
        insert_virtual_media()
        validate_media_status()
    elif args["action"].lower() == "eject" and args["device"]:
        eject_virtual_media()
        validate_media_status()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
    
    
        
            
        
        

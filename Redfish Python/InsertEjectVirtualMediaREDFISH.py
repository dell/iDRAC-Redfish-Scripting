#
# InsertEjectVirtualMediaREDFISH. Python script using Redfish API DMTF to either get virtual media information, insert or eject virtual media
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

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to either get virtual media information, insert or eject virtual media")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will get current information for CD and removable disk virtual media. InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin -o 1 -d 1 -i http://192.168.0.130/esxi_5u1.iso, this example shows booting to CD ISO on HTTP share. InsertEjectVirtualMediaREDFISH.py -ip 192.168.0.120 -u root -p calvin -o 2 -d 1, this example will detach CD ISO.')
parser.add_argument('-c', help='Get current virtual media information, pass in a value of \"y\"', required=False)
parser.add_argument('-o', help='Pass in the type of action you want to perform. Pass in \"1\" to Insert or \"2\" to Eject', required=False)
parser.add_argument('-d', help='Pass in the device you want to insert or eject. Pass in \"1\" for CD or \"2\" for RemovableDisk', required=False)
parser.add_argument('-i', help='Insert (attach) virtual media , pass in the HTTP or HTTPS URI path of the remote image. Note: If attaching removable disk, only supported file type is .img', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    try:
        data = response.json()
    except:
        print("\n- FAIL, either incorrect iDRAC username / password passed in or iDRAC user doesn't have correct privileges")
        sys.exit()
    try:
        for i in data[u'Actions']:
            if i == "#VirtualMedia.InsertMedia" or i == "#VirtualMedia.EjectMedia":
                pass
    except:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
            
    


def get_virtual_media_info():
    virtual_media_uris = []
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    print("\n - Virtual Media URIs detected \n")
    for i in data[u'Members']:
        for ii in i.items():
            print(ii[1])
            virtual_media_uris.append(ii[1])
    for i in virtual_media_uris:
        print("\n- Detailed information for URI \"%s\" \n" % i)
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        for i in data.items():
            if "@odata" in i[0] or "Actions" in i[0]:
                pass
            else:
                print("%s: %s" % (i[0], i[1]))

        
def insert_virtual_media():
    if args["d"] == "1":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia" % idrac_ip
        media_device = "CD"
    elif args["d"] == "2":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.InsertMedia" % idrac_ip
        media_device = "Removable Disk"
    else:
        print("- FAIL, invalid value passed in for argument d")
        sys.exit()
    print("\n - WARNING, insert(attached) \"%s\" virtual media device \"%s\"" % (media_device, args["i"]))
    payload = {'Image': args["i"], 'Inserted':True,'WriteProtected':True}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    data = response.__dict__
    if response.status_code != 204:
        print("\n- FAIL, POST command InsertMedia action failed, detailed error message: %s" % response._content)
        sys.exit()
    else:
        print("\n- PASS, POST command passed to successfully insert(attached) %s media" % media_device)

def eject_virtual_media():
    if args["d"] == "1":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia" % idrac_ip
        media_device = "CD"
    elif args["d"] == "2":
        url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.EjectMedia" % idrac_ip
        media_device = "Removable Disk"
    else:
        print("- FAIL, invalid value passed in for argument d")
        sys.exit()
    print("\n - WARNING, eject(unattached) \"%s\" virtual media device \"%s\"" % (media_device, args["i"]))
    payload = {}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    data = response.__dict__
    if response.status_code != 204:
        print("\n- FAIL, POST command EjectMedia action failed, detailed error message: %s" % response._content)
        sys.exit()
    else:
        print("\n- PASS, POST command passed to successfully eject(unattached) %s media" % media_device)
    

def validate_media_status():
    if args["d"] == "1":
        url = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD" 
        media_device = "CD"
    elif args["d"] == "2":
        url = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk"
        media_device = "Removable Disk"
    response = requests.get('https://%s%s' % (idrac_ip, url),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    attach_status = data["Inserted"]
    if args["o"] == "1":
        if attach_status == True:
            print("- PASS, GET command passed to verify %s media successfully inserted(attached)" % media_device)
        else:
            print("- FAIL %s media not attached, current status is: %s" % attach_status)
            sys.exit()
    elif args["o"] == "2":
        if attach_status == False:
            print("- PASS, GET command passed to verify %s media successfully ejected(unattached)" % media_device)
        else:
            print("- FAIL %s media not ejected, current status is: %s" % attach_status)
            sys.exit()
        

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_virtual_media_info()
    elif args["o"] == "1":
        insert_virtual_media()
        validate_media_status()
    elif args["o"] == "2":
        eject_virtual_media()
        validate_media_status()
    
    
        
            
        
        

#
# GetDHSDisksREDFISH. Python script using Redfish API with OEM extension to get available disks for dedicated hot spare(DHS) assignment
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get available disks for dedicated hot spare(DHS) assignment")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetDHSDisksREDFISH.py -ip 192.168.0.120 -u root -p calvin -t Disk.Virtual.0:RAID.Mezzanine.1C-1, this example will return all available disks that can be assigned as DHS for the virtual disk')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Slot.6-1\"', required=False)
parser.add_argument('-vv', help='Get current server storage controller virtual disk detailed information, pass in storage controller FQDD, Example "\RAID.Slot.6-1\"', required=False)
parser.add_argument('-t', help='Pass in the virtual disk FQQD to check for available disks that can be assigned for DHS, Example "\Disk.Virtual.1:RAID.Slot.6-1\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


    

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
        print(i[u'@odata.id'][46:])
    if args["c"] == "yy":
        for i in controller_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
    else:
        pass
    sys.exit()

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["v"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["v"])
        sys.exit()
    else:
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
    print("\n- Volume(s) detected for %s controller -" % args["v"])
    print("\n")
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                print("%s, Volume type: %s" % (ii, i[1]))
    sys.exit()

def get_virtual_disk_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["vv"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, status code %s returned. Check to make sure you passed in correct controller FQDD string for argument value" % response.status_code)
        sys.exit()
    if data[u'Members'] == []:
        print("\n- WARNING, no volume(s) detected for %s" % args["vv"])
        sys.exit()
    else:
        print("\n- Volume(s) detected for %s controller -\n" % args["vv"])
        for i in data[u'Members']:
            vd_list.append(i[u'@odata.id'][54:])
            print(i[u'@odata.id'][54:])
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n - Detailed Volume information for %s -\n" % ii)
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))
                
    sys.exit()


def get_DHS_disks():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.GetDHSDisks' % (idrac_ip)
    payload={"TargetFQDD":args["t"]}

    headers = {'content-type': 'application/json'}
    #payload={"TargetFQDD":args["a"],"DiskType":"IncludeAllTypes","Diskprotocol":"IncludeAllProtocols","RaidLevel":"RAID1"}
    #payload={"TargetFQDD":args["a"],"VirtualDiskArray":args["V"]}
    #print payload
    #sys.exit()
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    check_for_drives_detected=str(data)
    if "PDArray" not in check_for_drives_detected:
        print("\n- WARNING, either no drives available to assign as DHS, virtual disk RAID level does not support assign DHS or invalid virtual disk FQDD passed in\n")
        sys.exit()
    if response.status_code == 200:
        print("\n- PASS: POST command passed to get DHS disks for virtual disk \"%s\"" % args["t"])
    else:
        print("\n- FAIL, POST command failed to get DHS disks for virtual disk \"%s\"" % args["t"])
        data = response.json()
        print("\n- POST command failure detailed results:\n %s" % data)
        sys.exit()
    print("\n- WARNING, drives available to assign as DHS for virtual disk \"%s\" -\n" % args["t"])
    for i in data[u'PDArray']:
            print(i)
   


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["t"]:
        get_DHS_disks()
    elif args["v"]:
        get_virtual_disks()
    elif args["vv"]:
        get_virtual_disk_details()
    
    
    
        
            
        
        

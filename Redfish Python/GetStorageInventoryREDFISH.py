#
# GetStorageInventoryREDFISH. Python script using Redfish API DMTF to get storage inventory: controllers, disks and backplanes.
#
# NOTE: Recommended to run "GetStorageInventoryREDFISH -h" first to get help text, display supported parameter options and get examples. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")



parser = argparse.ArgumentParser(description='Python script using Redfish API DMTF to get server storage inventory (disks, controllers and backplanes)')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC username pasword', required=True)
parser.add_argument('script_examples',action="store_true",help='GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -b RAID.Integrated.1-1, this example will get backplanes for storage controller RAID.Integrated.1-1. GetStorageInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -dd RAID.Integrated.1-1, this example will get detailed information for all disks detected for storage controller RAID.Integrated.1-1')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-b', help='Get server backplane(s), pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


    

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

    
def get_storage_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, controller),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("- FAIL, GET command failed, detailed error information: %s" % data)
        sys.exit()
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % controller)
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % controller)
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'].split("/")[-1])
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i[u'@odata.id'].split("/")[-1]),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            print i[u'@odata.id'].split("/")[-1]
    if args["dd"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          print("\n - Detailed drive information for %s -\n" % i)
          for ii in data.items():
              print("%s: %s" % (ii[0],ii[1]))
                

def get_backplanes():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SimpleStorage/Controllers/%s' % (idrac_ip, args["b"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    backplane_dict = {}
    try:
        for i in data[u'Devices']:
            for ii in i.items():
                if ii[0] == "Name":
                    if "plane" in ii[1]:
                        backplane_dict = i
    except:
        print("\n- WARNING, invalid controller FQDD passed in for argument -b")
        sys.exit()
    if backplane_dict == {}:
        print("\n- WARNING, no backplanes detected in storage inventory for controller %s" % args["b"])
        sys.exit()
    else:
        print("\n- Backplane(s) detected for controller %s -\n" % args["b"])
        for i in backplane_dict.items():
            if i[0] == "Status":
                for ii in i[1].items():
                    print("%s: %s" % (ii[0],ii[1]))
            else:
                print("%s: %s" % (i[0],i[1]))
    
    


if __name__ == "__main__":
    if args["c"]:
        get_storage_controllers()
    elif args["d"] or args["dd"]:
        if args["d"]:
            controller = args["d"]
        elif args["dd"]:
            controller = args["dd"]
        get_storage_disks()
    elif args["b"]:
        get_backplanes()
    else:
        print("\n- WARNING, either incorrect parameter value(s) passed in or missing parameter")



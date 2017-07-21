#
# GetStorageInventoryREDFISH. Python script using Redfish API to get storage inventory: controllers, disks and backplanes.
#
# NOTE: Recommended to run "GetStorageInventoryREDFISH -h" first to get help text, display supported parameter options and get examples. 
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")



parser = argparse.ArgumentParser(description='Python script using Redfish API to get server storage inventory (disks, controllers and backplanes)')
parser.add_argument('-i', help='iDRAC IP Address', required=True, type=str)
parser.add_argument('-u', help='iDRAC username', required=True, type=str)
parser.add_argument('-p', help='iDRAC username pasword', required=True, type=str)
parser.add_argument('-e', help='pass in \"y\" to print excuting script examples', required=False, type=str)
parser.add_argument('-o', help='user option, pass in \"c\" to get controllers', required=False, type=str)
parser.add_argument('-c', help='user option, pass in your controller name to get supported disks and backplane', required=False, type=str)

args = parser.parse_args()

idrac_ip=args.i
idrac_username=args.u
idrac_password=args.p

if args.e == "y":
    print("\n- GetStorageInventoryREDFISH -i 192.168.0.120 -u root -p calvin -o c, this will return supported controllers detected.\n- GetStorageInventoryREDFISH -i 192.168.0.120 -u root -p calvin -c RAID.Integrated.1-1, this will return all detected drives and backplane for this controller.")

# Function to get current controllers on the server

def get_storage_controllers():
    if args.o == "c":
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Controllers' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        controller_list=[]
        for i in data["Members"]:
            for ii in i.items():
                controller_list.append(ii[1].split("/")[-1])
        print("\n- Current controllers detected in server:\n")
        for i in controller_list:
            print(i)
    
        sys.exit()

# Function to get disks and backplane

def get_storage_disks():
    try:
        os.remove("storage_inventory.txt")
    except:
        pass
    f=open("storage_inventory.txt","a")
    if args.c:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Controllers/%s' % (idrac_ip,args.c),verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if data[u'Devices'] == []:
            print("\n- No supported disks detected for controller %s") % args.c
            sys.exit()
        
        s="\n- Supported disks and backplane for controller: %s\n" % args.c
        print(s)
        f.writelines("%s\n" % s)
        for i in data[u'Devices']:
            for ii in i.items():
                if isinstance(ii[1],dict):
                    for iii in ii[1].items():
                        s="%s : %s" % (iii[0], iii[1])
                        print(s)
                        f.writelines(s)
                elif ii[0] == "Manufacturer":
                    s="%s : %s\n" % (ii[0], ii[1])
                    print(s)
                    f.writelines("%s\n" % s)
                else:
                    s="%s : %s" % (ii[0], ii[1])
                    print(s)
                    f.writelines(s)
        f.close()
        print("\n- WARNING, storage inventory also captured in \"storage_inventory.txt\" file")
        sys.exit()
        controller_list=[]
        for i in data["Members"]:
            for ii in i.items():
                controller_list.append(ii[1].split("/")[-1])
        print("\n- Current controllers detected in server:\n")
        for i in controller_list:
            print(i)
    
    
    
    
#Run Code

if __name__ == "__main__":
    get_storage_controllers()
    get_storage_disks()



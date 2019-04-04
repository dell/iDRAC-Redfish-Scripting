#
# GetDiskOperationREDFISH. Python script using Redfish API DMTF to get check a disk if any operations are in progress.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to get check a disk if any operations are in progress")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetDiskOperationREDFISH.py -ip 192.168.0.120 -u root -p calvin -o Disk.Bay.1:Enclosure.Internal.0-0:RAID.Mezzanine.1C-1, this example will return any operation information for this drive')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\". To get detailed information for all controllerse detected, pass in \"yy\"', required=False)
parser.add_argument('-cc', help='Pass in controller FQDD, this argument is used with -s to get support RAID levels for the controller', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-dd', help='Get server storage controller disks detailed information, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-o', help='Pass in the disk FQDD string', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def get_pdisks():
    disk_used_created_vds=[]
    available_disks=[]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["d"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("- FAIL, GET command failed, detailed error information: %s" % data)
        sys.exit()
    if data[u'Drives'] == []:
        print("\n- WARNING, no drives detected for %s" % args["d"])
        sys.exit()
    else:
        print("\n- Drive(s) detected for %s -\n" % args["d"])
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'].split("/")[-1])
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i[u'@odata.id'].split("/")[-1]),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if data[u'Links'][u'Volumes'] == []:
                print("Disk: %s, RaidStatus: Disk is not part of a RAID volume" % (i[u'@odata.id'].split("/")[-1]))
            else:
                print("Disk: %s, RaidStatus: Disk is part of a RAID volume, RAID volume is: %s" % (i[u'@odata.id'].split("/")[-1],data[u'Links'][u'Volumes'][0][u'@odata.id'].split("/")[-1] ))
    if args["dd"]:
      for i in drive_list:
          response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
          data = response.json()
          
          print("\n - Detailed drive information for %s -\n" % i)
          for ii in data.items():
              print("%s: %s" % (ii[0],ii[1]))
              if ii[0] == "Links":
                  if ii[1]["Volumes"] != []:
                      disk_used_created_vds.append(i)
                  else:
                      available_disks.append(i) 

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

def get_disk_operation_info():
    print("\n- %s Operation Information -\n" % args["o"])
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, args["o"]),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        if data[u'Operations'] == []:
            print("- WARNING, no operations running for %s" % args["o"])
            sys.exit()
        else:
            for i in data[u'Operations']:
                for ii in i.items():
                    print("%s: %s" % (ii[0],ii[1]))
            
    else:
        print("- FAIL, GET command failed to get disk operation information, status code is %s" % response.status_code)
        sys.exit()

if __name__ == "__main__":
    if args["o"]:
        get_disk_operation_info()
    elif args["d"] or args["dd"]:
        get_pdisks()
    elif args["c"] or args["cc"]:
        get_storage_controllers()
    else:
        print("- WARNING, either incorrect argument value passed in or missing argument(s)")
    
    
    
        
            
        
        

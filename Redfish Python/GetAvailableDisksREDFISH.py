#
# GetAvailableDisksREDFISH. Python script using Redfish API with OEM extension to get available disks for virtual disk creation
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


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get available disks for virtual disk creation")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetAvailableDisksREDFISH.py -ip 192.168.0.120 -u root -p calvin -t RAID.Mezzanine.1C-1 -dt 0 -dp 0, this example will return available disks for all disk types and protocols. GetAvailableDisksREDFISH.py -ip 192.168.0.120 -u root -p calvin -t RAID.Mezzanine.1C-1 -dt 0 -dp 1 -r RAID0, this example to get available disks for all disk types, SAS drives only for RAID 0 creation.') 
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-t', help='Get available disks for virtual disk creation, pass in target controller FQDD, Example \"RAID.Slot.6-1\". Note: You must pass in -dt and -dp also with -t which are the minimum required parameters needed to get available disks', required=False)
parser.add_argument('-dt', help='DiskType, pass in 0 for \"IncludeAllTypes\", pass in 1 for \"IncludeHardDiskOnly\", pass in 2 for \"IncludeSolidStateOnly\"', required=False)
parser.add_argument('-dp', help='Diskprotocol, pass in 0 for \"AllProtocols\", pass in 1 for \"SAS\", pass in 2 for \"SATA\", pass in 3 for \"NVMe\"', required=False)
parser.add_argument('-f', help='FormFactor, pass in 0 for \"IncludeAll\", pass in 1 for \"IncludeOnlyM.2\"', required=False)
parser.add_argument('-de', help='DiskEncrypt, pass in 0 for \"IncludeFDECapableAndNonEncryptionCapableDisks\", pass in 1 for \"IncludeFDEDisksOnly\", pass in 2 for \"IncludeOnlyNonFDEDisks\"', required=False)
parser.add_argument('-b', help='BlockSizeInBytes, pass in 0 for \"IncludeAllBlockSizeDisks\", pass in 1 for \"Include512BytesBlockSizeDisksOnly\", pass in 2 for \"Include4096BytesBlockSizeDisks\"', required=False)
parser.add_argument('-t10', help='T10PIStatus, pass in 0 for \"IncludeAlldrives,T10PIIncapableAndCapableDrives\", pass in 1 for \"IncludeT10PICapableDrivesOnly\", pass in 2 for \"IncludeT10PIIncapableDrivesOnly\"', required=False)
parser.add_argument('-r', help='RaidLevel, pass in a RAID level, output will return the minimum available disks to create the virtual disk. Supported values are \"RAID0\", \"RAID1\", \"RAID5\", \"RAID6\", \"RAID10\", \"RAID50\", \"RAID60\"', required=False)


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
        controller_list.append(i[u'@odata.id'].split("/")[-1])
        print(i[u'@odata.id'].split("/")[-1])
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



def get_available_disks():
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.GetAvailableDisks' % (idrac_ip)
    payload={"TargetFQDD":args["t"]}
    if args["dt"]:
        if args["dt"] == "0":
            payload["DiskType"] = "All"
        elif args["dt"] == "1":
            payload["DiskType"] = "HDD"
        elif args["dt"] == "2":
            payload["DiskType"] = "SSD"
        else:
            print("- WARNING, invalid value entered for -dt parameter")
            sys.exit()
    if args["dp"]:
        if args["dp"] == "0":
            payload["Diskprotocol"] = "AllProtocols"
        elif args["dp"] == "1":
            payload["Diskprotocol"] = "SAS"
        elif args["dp"] == "2":
            payload["Diskprotocol"] = "SATA"
        elif args["dp"] == "3":
            payload["Diskprotocol"] = "NVMe"
        else:
            print("\n- WARNING, invalid value entered for -dp parameter")
            sys.exit()
    if args["f"]:
        if args["f"] == "0":
            payload["FormFactor"] = "All"
        elif args["f"] == "1":
            payload["FormFactor"] = "M.2"
        else:
            print("- WARNING, invalid value entered for -f parameter")
            sys.exit()
    if args["de"]:
        if args["de"] == "0":
            payload["DiskEncrypt"] = "All"
        elif args["de"] == "1":
            payload["DiskEncrypt"] = "FDE"
        elif args["de"] == "2":
            payload["DiskEncrypt"] = "NonFDE"
        else:
            print("- WARNING, invalid value entered for -de parameter")
            sys.exit()
    if args["b"]:
        if args["b"] == "0":
            payload["BlockSizeInBytes"] = "All"
        elif args["b"] == "1":
            payload["BlockSizeInBytes"] = "512"
        elif args["b"] == "2":
            payload["BlockSizeInBytes"] = "4096"
        else:
            print("- WARNING, invalid value entered for -b parameter")
            sys.exit()
    if args["t10"]:
        if args["t10"] == "0":
            payload["T10PIStatus"] = "All"
        elif args["t10"] == "1":
            payload["T10PIStatus"] = "T10PICapable"
        elif args["t10"] == "2":
            payload["T10PIStatus"] = "T10PIIncapable"
        else:
            print("- WARNING, invalid value entered for -t10 parameter")
            sys.exit()
    if args["r"]:
        payload["RaidLevel"] = args["r"]
        
            
    print("\n- WARNING, parameters keys / values used for GetAvailableDisks POST command are:\n")
    for i in payload.items():
        print("%s: %s" % (i[0], i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed to get available disks for controller %s" % args["t"])
    else:
        print("\n- FAIL, POST command failed to get available disks for controller %s" % args["t"])
        data = response.json()
        print("\n-POST command failure detailed results:\n %s" % data)
        sys.exit()
    if args["r"]:
        if data[u'PDArray'] == []:
            print("\n- WARNING, no disk(s) available for \"%s\" Virtual Disk creation\n" % args["r"])
        else:
            print("\n- Minimum drives available for \"%s\" Virtual Disk creation\n" % args["r"])
            for i in data[u'PDArray']:
                print(i)
    else:    
        print("\n- Drives available for Virtual Disk creation\n")
        try:
            for i in data[u'PDArray']:
                print(i)
        except:
            print("- WARNING, no drives available based off arguments passed in for GetAvailableDisks method")
    sys.exit()
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    if args["t"] and args["dt"] and args["dp"]:
        get_available_disks()
    else:
        print("- WARNING, -t, -dt and -dp are minimum arguments required to get available disks")
    
    
    
        
            
        
        

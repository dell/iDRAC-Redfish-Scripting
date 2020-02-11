#
# DellSlotCollectionREDFISH. Python script using Redfish API with OEM extension to get server slot information.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2020, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API with OEM extension to get server slot information. This includes PSUs, Fans, DIMMs, CPUs, IDSDM, vFlash, PCIe, disks')
parser.add_argument('-ip', help='iDRAC IP Address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('script_examples',action="store_true",help='DellSlotCollectionREDFISH -ip 192.168.0.120 -u root -p calvin, this example will return server slot information.')

args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("slot_collection.txt")
except:
    pass

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_slot_collection():
    f=open("slot_collection.txt","a")
    d=datetime.now()
    current_date_time="- iDRAC IP %s, data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (idrac_ip,d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            slot_collection_entry = ("%s: %s" % (ii[0],ii[1]))
            print(slot_collection_entry)
            f.writelines("%s\n" % slot_collection_entry)
        print("\n")
        f.writelines("\n")

    
    number_list=[i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if "Members" in data:
            pass
        else:
            break
        for i in data['Members']:
            for ii in i.items():
                slot_collection_entry = ("%s: %s" % (ii[0],ii[1]))
                print(slot_collection_entry)
                f.writelines("%s\n" % slot_collection_entry)
            print("\n")
            f.writelines("\n")

    
    
    print("\n- WARNING, slot collection information also captured in \"slot_collection.txt\" file")
    f.close()

    

if __name__ == "__main__":
    check_supported_idrac_version()
    get_slot_collection()



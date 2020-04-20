#
# GetIdracServerSlotInformationREDFISH. Python script using Redfish API with OEM extension to get iDRAC server slot information.
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get server slot information. Slot information includes: Fan, CPU, DIMM, PCI, Backplane, PSU")
parser.add_argument('script_examples',action="store_true",help='GetIdracServerSlotInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -s y, this example will get slot information for all server devices and also redirect output to a file.')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-s', help='Get all iDRAC server information, pass in \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("server_slot_info.txt")
except:
    pass



def get_server_slot_info():
    f=open("server_slot_info.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data[u'Members']:
        for ii in i.items():
            server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
            print(server_slot_entry)
            f.writelines("%s\n" % server_slot_entry)
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
        for i in data[u'Members']:
            for ii in i.items():
                server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
                print(server_slot_entry)
                f.writelines("%s\n" % server_slot_entry)
            print("\n")
            f.writelines("\n")
    print("\n- WARNING, iDRAC Server Slot Information also captured in \"server_slot_info.txt\" file")
    f.close()

#Run Code

if __name__ == "__main__":
    if args["s"]:
        get_server_slot_info()
    else:
        print("\n- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")



#
# BiosGetAttributesREDFISH. Python script using Redfish API to get BIOS attributes with current values.
#
# NOTE: Recommended to run this script first to get attributes and current values before executing BiosSetAttributeREDFISH script.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to get all BIOS attributes or get current value for one specific attribute")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-a', help='Pass in the attribute name you want to get the current value, Note: make sure to type the attribute name exactly due to case sensitive. Example: MemTest will work but memtest will fail', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("bios_attributes.txt")
except:
    pass

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_bios_attributes():
    f=open("bios_attributes.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.year,d.month,d.day, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    a="\n--- BIOS Attributes ---\n"
    print(a)
    f.writelines(a)
    for i in data[u'Attributes'].items():
        attribute_name = "Attribute Name: %s\t" % (i[0])
        f.writelines(attribute_name)
        attribute_value = "Attribute Value: %s\n" % (i[1])
        f.writelines(attribute_value)
        print("Attribute Name: %s\t Attribute Value: %s" % (i[0],i[1]))
        
    print("\n- Attributes are also captured in \"bios_attributes.txt\" file")
    f.close()

def get_specific_bios_attribute():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data[u'Attributes'].items():
        if i[0] == args["a"]:
            print("\n- Current value for attribute \"%s\" is \"%s\"\n" % (args["a"], i[1]))
            sys.exit()
    print("\n- FAIL, unable to get attribute current value. Either attribute doesn't exist for this BIOS version, typo in attribute name or case incorrect")
    sys.exit()
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["a"]:
       get_specific_bios_attribute()
    else:
        get_bios_attributes()
    



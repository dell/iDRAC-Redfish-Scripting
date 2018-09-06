#
# GetIdracLcSystemAttributesREDFISH. Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run this script first to get attributes with current values before you execute SetIdracLcSystemAttributesREDFISH script.
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g idrac, this example wil get all iDRAC attributes and echo them to the screen along with copy output to a file.') 
parser.add_argument('-g', help='Get attributes, pass in the group name of the attributes you want to get. Supported values are \"idrac\", \"lc\" and \"system\"', required=True)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        print("\nNote: If using iDRAC 7/8, this script is not supported. Use Server Configuration Profile feature instead with Redfish to get iDRAC / System and Lifecycle Controller attributes") 
        sys.exit()
    else:
        pass

def get_attribute_group():
    global current_value
    if args["g"] == "idrac":
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "lc":
        response = requests.get('https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "system":
        response = requests.get('https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data[u'Attributes']
    print("\n- %s Attribute Names and Values:\n" % args["g"].upper())
    f = open("attributes.txt","w")
    for i in attributes_dict:
        z="Name: %s, Value: %s" % (i, attributes_dict[i])
        print(z)
        f.writelines("%s\n" % z)
    f.close()
    print("\n- WARNING, Attribute enumeration also copied to \"attributes.txt\" file")
    

if __name__ == "__main__":
    check_supported_idrac_version()
    get_attribute_group()



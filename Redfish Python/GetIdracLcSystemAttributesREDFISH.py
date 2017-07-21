#
# GetIdracLcSystemAttributesREDFISH. Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run this script first to get attributes with current values before you execute SetIdracLcSystemAttributesREDFISH script.
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
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

import requests, json, sys, re, time, warnings

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
    attribute_group = sys.argv[4]

except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password / attribute group. Example: \"script_name.py 192.168.0.120 root calvin idrac\"")
    sys.exit()

### Function to get attributes and current value

def get_attribute_group():
    global current_value
    if attribute_group == "idrac":
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif attribute_group == "lc":
        response = requests.get('https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif attribute_group == "system":
        response = requests.get('https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data[u'Attributes']
    print("\n- %s Attribute Names and Values:\n" % attribute_group.upper())
    f = open("attributes.txt","w")
    for i in attributes_dict:
        z="Name: %s, Value: %s" % (i, attributes_dict[i])
        print(z)
        f.writelines("%s\n" % z)
    f.close()
    print("\n- WARNING, Attribute enumeration also copied to \"attributes.txt\" file")
    

### Run code

if __name__ == "__main__":
    get_attribute_group()



#
# SetIdracLcSystemAttributesREDFISH. Python script using Redfish API to set either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run script GetIdracLcSystemAttributesREDFISH first to return attributes with current values. 
#
# NOTE: Before executing the script, edit "file_attributes_dict" dictionary below first. You want to pass in the attributes you want to change along with the new value. The script only supports setting one group of attributes (Example: you can only pass in iDRAC attributes in the dictionary. When you execute the script, you want to pass in "idrac" for the attribute_group parameter).
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

file_attributes_dict = {"Telnet.1.Enable":"Enabled","VirtualMedia.1.FloppyEmulation":"Enabled","EmailAlert.2.Address":"user@email.com"}

### Function to set attributes from "file_attributes_dict" dictionary

def set_attributes():
    print("- WARNING, changing %s attributes:\n" % attribute_group.upper())
    for i in file_attributes_dict:
        print(" Name:  %s, setting new value to: %s" % (i, file_attributes_dict[i]))
    payload = {"Attributes":file_attributes_dict}
    headers = {'content-type': 'application/json'}
    if attribute_group == "idrac":
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    elif attribute_group == "lc":
        url = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip
    elif attribute_group == "system":
        url = 'https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip 
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    
    if statusCode == 200:
        print("\n- PASS, Command passed to successfully set \"%s\" attribute(s), status code %s returned\n" % (attribute_group.upper(),statusCode))
    else:
        print("\n- FAIL, Command failed to set %s attributes(s), status code is: %s\n" % (attribute_group.upper(),statusCode))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    


### Function to verify new current values
    
def get_new_attribute_values():
    if attribute_group == "idrac":
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif attribute_group == "lc":
        response = requests.get('https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif attribute_group == "system":
        response = requests.get('https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    new_attributes_dict=data[u'Attributes']
    for i in file_attributes_dict.items():
        for ii in new_attributes_dict.items():
            if i[0] == ii[0]:
                if i[1] == ii[1]:
                    print("- PASS, Attribute %s successfully set to %s" % (i[0],i[1]))
                else:
                    print("- FAIL, Attribute %s not set to %s" % (i[0],i[1]))
        
    

### Run code

if __name__ == "__main__":
    set_attributes()
    get_new_attribute_values()
    



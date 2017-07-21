#
# BiosGetAttributesREDFISH. Python script using Redfish API to get BIOS attributes with current values.
#
# NOTE: Recommended to run this script first to get attributes and current values before executing BiosSetAttributeREDFISH script.
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

import requests, json, sys, re, time, os, warnings

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password")
    sys.exit()

try:
    os.remove("bios_attributes.txt")
except:
    pass

# Function to get BIOS attributes /current settings

def get_bios_attributes():
    f=open("bios_attributes.txt","a")
    global current_value
    global pending_value
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

#Run Code
    
get_bios_attributes()



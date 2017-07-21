#
# GetFirmwareInventoryREDFISH. Python script using Redfish API to get current firmware version for all devices iDRAC supports for updates.
#
# NOTE: Recommended to run this script first to get current FW versions of devices before executing DeviceFirmwareUpdateREDFISH script.
#
# 
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
except:
    print("\n- FAIL, you must pass in script name along with iDRAC IP / iDRAC username / iDRAC password. Example: \"script_name.py 192.168.0.120 root calvin\"")
    sys.exit()
    


# Function to get FW inventory

def get_FW_inventory():
        print("\n- WARNING, get current firmware version(s) for all devices in the system iDRAC supports\n")
        time.sleep(3)
        req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        number_of_devices=len(data[u'Members'])
        count = 0
        installed_devices=[]
        while count != len(data[u'Members']):
            a=data[u'Members'][count][u'@odata.id']
            a=a.replace("/redfish/v1/UpdateService/FirmwareInventory/","")
            if "Installed" in a:
                installed_devices.append(a)
            count +=1
        installed_devices_details=["\n--- Firmware Inventory ---"]
        a="-"*75
        installed_devices_details.append(a)
        l=[]
        ll=[]
        for i in installed_devices:
            req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
            statusCode = req.status_code
            data = req.json()
            a="Name: %s" % data[u'Name']
            l.append(a.lower())
            installed_devices_details.append(a)
            a="Firmware Version: %s" % data[u'Version']
            ll.append(a.lower())
            installed_devices_details.append(a)
            a="Updateable: %s" % data[u'Updateable']
            installed_devices_details.append(a)
            a="-"*75
            installed_devices_details.append(a)
            
        for i in installed_devices_details:
            print(i)
        sys.exit()


# Run code here

get_FW_inventory()



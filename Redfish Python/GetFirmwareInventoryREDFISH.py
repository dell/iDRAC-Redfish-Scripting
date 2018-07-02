#
# GetFirmwareInventoryREDFISH. Python script using Redfish API to get current firmware version for all devices iDRAC supports for updates.
#
# NOTE: Recommended to run this script first to get current FW versions of devices before executing DeviceFirmwareUpdateREDFISH script.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
#
# Copyright (c) 2018, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import requests, json, sys, re, time, warnings, os

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("\n- FAIL, you must pass in script name along with iDRAC IP / iDRAC username / iDRAC password. Example: \"script_name.py 192.168.0.120 root calvin\"")
    sys.exit()

# Function to check if current iDRAC version supports Redfish firmware features

def check_idrac_fw_support():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 400:
        print("\n- WARNING, current server iDRAC version does not support Redfish firmware features. Refer to Dell online Redfish documentation for information on which iDRAC version support firmware features.")
        sys.exit()
    else:
        pass
    


# Function to get FW inventory

def get_FW_inventory():
        print("\n- WARNING, get current firmware version(s) for all devices in the system iDRAC supports\n")
        time.sleep(3)
        try:
            os.remove("fw_inventory.txt")
        except:
            pass
        f=open("fw_inventory.txt","a")
        d=datetime.now()
        current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
        f.writelines(current_date_time)
        f.writelines("\n\n")
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
        for i in installed_devices:
            req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
            statusCode = req.status_code
            data = req.json()
            for i in data.items():
                if i[0] == u'Description':
                    entry = "%s: %s\n" % (i[0], i[1])
                    f.writelines("%s\n" % entry)
                    print(entry)
                    f.writelines("\n")
    
                else:
                    entry = "%s: %s" % (i[0], i[1])
                    print(entry)
                    f.writelines("%s\n" % entry)

        print("\n- WARNING, software inventory also captured in \"fw_inventory.txt\" file")
        f.close()
        sys.exit()


if __name__ == "__main__":
    check_idrac_fw_support()
    get_FW_inventory()



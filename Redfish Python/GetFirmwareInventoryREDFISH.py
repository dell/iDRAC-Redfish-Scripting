#
# GetFirmwareInventoryREDFISH. Python script using Redfish API DMTF method to get current firmware version for all devices iDRAC supports for updates.
#
# NOTE: Recommended to run this script first to get current FW versions of devices before executing DeviceFirmwareUpdateREDFISH script.
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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

import requests, json, sys, re, time, warnings, os, argparse

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF method to get current firmware version for all devices iDRAC supports for updates. This script is excuting one GET command using OData feature $expand ")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]




def check_idrac_fw_support():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 400:
        print("\n- WARNING, current server iDRAC version does not support Redfish firmware features. Refer to Dell online Redfish documentation for information on which iDRAC version support firmware features.")
        sys.exit()
    else:
        pass
    

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
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory?$expand=*($levels=1)' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    for i in data[u'Members']:
        for ii in i.items():
            if ii[0] == u'@odata.type':
                message = "\n%s: %s" % (ii[0], ii[1])
                f.writelines(message)
                print(message)
                message = "\n"
                f.writelines(message)
            elif ii[0] == "Oem":
                for iii in ii[1][u'Dell'][u'DellSoftwareInventory'].items():
                    message = "%s: %s" % (iii[0], iii[1])
                    f.writelines(message)
                    print(message)
                    message = "\n"
                    f.writelines(message)

            else:
                message = "%s: %s" % (ii[0], ii[1])
                f.writelines(message)
                print(message)
                message = "\n"
                f.writelines(message)

    print("\n- Firmware inventory output is also captured in \"fw_inventory.txt\" file")
    f.close()
        
        


if __name__ == "__main__":
    check_idrac_fw_support()
    get_FW_inventory()



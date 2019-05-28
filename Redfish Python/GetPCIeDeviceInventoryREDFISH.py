#
# GetPCIeDeviceInventoryREDFISH. Python script using Redfish API DMTF to get server PCIeDevice inventory.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
#
# Copyright (c) 2019, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API DMTF to get server PCIe Device Inventory')
parser.add_argument('-ip', help='iDRAC IP Address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('script_examples',action="store_true",help='GetPCIeDeviceInventoryREDFISH -ip 192.168.0.120 -u root -p calvin -d y, this example will return PCIe device URIs\n- GetPCIeDeviceInventoryREDFISH -ip 192.168.0.120 -u root -p calvin -d yy, this example will return detailed information for PCIe device URIs')
parser.add_argument('-d', help='Pass in \"y\" to get server pcie device URIs. Pass in \"yy\" to get detailed information for each device URI', required=False)
parser.add_argument('-f', help='Pass in \"y\" to get server pcie function URIs. Pass in \"yy\" to get detailed information for each device URI', required=False)


args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_idrac_fw_support():
    req = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    if u'PCIeDevices' in data.keys():
        pass
    else:
        print("\n- WARNING, current iDRAC version does not support getting server PCIe Device information")
        sys.exit()

def get_pcie_device_inventory():
        print("\n- WARNING, server PCIe Device URIs for iDRAC %s\n" % idrac_ip)
        req = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        pcie_devices=[]
        try:
            os.remove("pcie_devices.txt")
        except:
            pass
        f=open("pcie_devices.txt","a")
        for i in data[u'PCIeDevices']:
            for ii in i.items():
                print(ii[1])
                pcie_devices.append(ii[1])
        if args["d"] == "yy":
            for i in pcie_devices:
                req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
                statusCode = req.status_code
                data = req.json()
                message = "\n\n- Detailed information for URI \"%s\"\n\n" % i
                print(message)
                f.writelines(message)
                for ii in data.items():
                    device = "%s: %s" % (ii[0], ii[1])
                    print(device)
                    f.writelines("%s%s" % ("\n",device))
                    
        else:       
            sys.exit()
        f.close()
        print("\n- WARNING, detailed information also captured in \"pcie_devices.txt\" file")
        sys.exit()

def get_pcie_function_inventory():
        print("\n- WARNING, server PCIe Function URIs for iDRAC %s\n" % idrac_ip)
        req = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        pcie_devices=[]
        try:
            os.remove("pcie_function.txt")
        except:
            pass
        f=open("pcie_function.txt","a")
        for i in data[u'PCIeFunctions']:
            for ii in i.items():
                print(ii[1])
                pcie_devices.append(ii[1])
        if args["f"] == "yy":
            for i in pcie_devices:
                req = requests.get('https://%s%s' % (idrac_ip, i), auth=(idrac_username, idrac_password), verify=False)
                statusCode = req.status_code
                data = req.json()
                message = "\n\n- Detailed information for URI \"%s\"\n\n" % i
                print(message)
                f.writelines(message)
                for ii in data.items():
                    device = "%s: %s" % (ii[0], ii[1])
                    print(device)
                    f.writelines("%s%s" % ("\n",device))
                    
        else:       
            sys.exit()
        f.close()
        print("\n- WARNING, detailed information also captured in \"pcie_function.txt\" file")
        sys.exit()
        


if __name__ == "__main__":
    check_idrac_fw_support()
    if args["d"] == "y" or args["d"] == "yy":
        get_pcie_device_inventory()
    elif args["f"]:
        get_pcie_function_inventory()
    else:
      print("\n- FAIL, either missing or invalid parameter(s) passed in. If needed, see script help text for supported parameters and script examples")



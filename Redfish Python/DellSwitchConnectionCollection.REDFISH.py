#
# DellSwitchConnectionCollectionREDFISH.py   Python script using Redfish API with OEM extension to get Dell switch network connections. 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get Dell switch network connections")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/NetworkPorts/DellSwitchConnectionCollection' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass

def get_Dell_switch_connections():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/NetworkPorts/DellSwitchConnectionCollection' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, GET command failed to get Dell switch connection collection, status code %s, error is %s" % (response.status_code, data))
        sys.exit()
    else:
        print("\n- Dell switch connection collection for iDRAC %s -\n" % idrac_ip)
    for i in data.items():
        if i[0] == "Members":
            for ii in i[1]:
                for iii in ii.items():
                    if iii[0] == "Name":
                        print("%s: %s\n" % (iii[0],iii[1]))
                    else:
                        print("%s: %s" % (iii[0],iii[1]))

    

if __name__ == "__main__":
    check_supported_idrac_version()
    get_Dell_switch_connections()
    
    
        
            
        
        

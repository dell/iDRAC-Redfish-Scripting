#
# GetSchemaPrivilegesREDFISH. Python script using Redfish API DMTF to get schema privileges.
#
# 
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to get schema privileges")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/PrivilegeRegistry' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_privileges():
    try:
        os.remove("privileges.txt")
    except:
        pass
    f=open("privileges.txt","a")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/PrivilegeRegistry' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data[u'Mappings']:
        for ii in i.items():
            if ii[0] == "Entity":
                entity = ii[1]
        message = "\n- Privileges for Entity(Schema) \"%s\" -\n" % entity
        f.writelines(message)
        print(message)
        message = "\n"
        f.writelines(message)
        for ii in i.items():
            if ii[0] == "OperationMap":
                for iii in ii[1].items():
                    message = "%s: %s" % (iii[0], iii[1])
                    f.writelines(message)
                    print(message)
                    message = "\n"
                    f.writelines(message)

    print("\n- Privileges is also captured in \"privileges.txt\" file")
    f.close()
    
    


if __name__ == "__main__":
    check_supported_idrac_version()
    get_privileges()
    



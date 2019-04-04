#
# GetNvDimmInventoryREDFISH. Python script using Redfish API DMTF to get server NVDIMM inventory.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API DMTF to get server NVDIMM Inventory')
parser.add_argument('-ip', help='iDRAC IP Address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('script_examples',action="store_true",help='GetNvDimmInventoryREDFISH -ip 192.168.0.120 -u root -p calvin, this example will return NVDIMM information if NVDIMMs are detected on the server')

args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def get_NVDIMM_information():
    try:
        os.remove("NVDIMM_inventory.txt")
    except:
        pass
    f=open("NVDIMM_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    nvdimm_uris = []
    for i in data[u'Members']:
        for ii in i.items():
            response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            try:
                if "NVDIMM" in data[u'MemoryType']:
                    nvdimm_uris.append(ii[1])
            except:
                pass
    if nvdimm_uris == []:
        print("\n- WARNING, no NVDIMM(s) detected for iDRAC IP %s\n" % idrac_ip)
        sys.exit()
    else:
        print("\n- WARNING, NVDIMM URI(s) detected for iDRAC IP \"%s\"\n" % idrac_ip)
        time.sleep(3)
        for i in nvdimm_uris:
            print(i)
        print("\n")
        for i in nvdimm_uris:
            response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            message = "\n- Detailed NVDIMM information for URI \"%s\" -\n" % i
            f.writelines("\n")
            f.writelines(message)
            print message
            for ii in data.items():
                if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == "Assembly" or ii[0] == u'@odata.type':
                    pass
                elif ii[0] == u'Oem':
                    for iii in ii[1][u'Dell'][u'DellMemory'].items():
                        if iii[0] == u'@odata.context' or iii[0] == u'@odata.type' or iii[0] ==u'@odata.id':
                            pass
                        else:
                            message = "%s: %s" % (iii[0], iii[1])
                            f.writelines("\n")
                            f.writelines(message)
                            print(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    f.writelines("\n")
                    f.writelines(message)
                    print(message)
    f.close()
    print("\n- WARNING, output also captured in \"NVDIMM_inventory.txt\" file")

if __name__ == "__main__":
    get_NVDIMM_information()



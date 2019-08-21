#
# GetAssemblyInventoryREDFISH. Python script using Redfish API DMTF to get system assembly or hardware inventory
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

parser=argparse.ArgumentParser(description="Python script using Redfish API DMTF to get system assembly (hardware) inventory(output will be printed to the screen and also copied to a text file). This includes information for storage controllers, memory, network devices, motherboard(planar), power supplies, backplanes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetAssemblyInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example will get all chassis assembly URIs. GetAssemblyInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -A y, this example will get detailed information for all chassis assembly URIs. GetAssemblyInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -s /redfish/v1/Chassis/System.Embedded.1/Assembly/DIMM.Socket.A2, this example will only return data for this URI')
parser.add_argument('-a', help='Get device chassis assembly URIs, pass in \"y\"', required=False)
parser.add_argument('-A', help='Get detailed information for all chassis assembly URIs, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get detailed information for only a specific chassis assembly URI, pass in the URI', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("assembly_inventory.txt")
except:
    pass



f=open("assembly_inventory.txt","a")
d=datetime.now()
current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
f.writelines(current_date_time)
f.close()

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_assembly_uris():
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Assembly' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        pass
    assembly_uris = []
    print("\n- Chassis Assembly URIs -\n")
    for i in data[u'Assemblies']:
        for ii in i.items():
            if ii[0] == u'@odata.id':
                print(ii[1])
                assembly_uris.append(ii[1])
    if args["A"]:
        f=open("assembly_inventory.txt","a")
        for i in assembly_uris:
            message = "\n- Detailed information for URI %s -\n" % i
            f.writelines(message)
            f.writelines("\n")
            print(message)
            response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            for ii in data.items():
                if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] ==  u'@odata.type':
                    pass
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    f.writelines(message)
                    f.writelines("\n")
                    print(message)
        print("\n- WARNING, output also captured in \"%s\\assembly_inventory.txt\" file" % os.getcwd())
    else:
        pass
            
    
    
    

def get_specific_uri_info():
    response = requests.get('https://%s%s' % (idrac_ip, args["s"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        pass
    print("\n- Detailed information for URI %s -\n" % args["s"])
    for ii in data.items():
        if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] ==  u'@odata.type':
            pass
        else:
            print("%s: %s" % (ii[0], ii[1]))
                    
       
if __name__ == "__main__":
    check_supported_idrac_version()
    if args["a"] or args["A"]:
          get_assembly_uris()
    elif args["s"]:
        get_specific_uri_info()
    else:
        print("\n- FAIL, invalid argument passed in or missing required argument")
        
        
        
    

    
    
    
        
            
        
        

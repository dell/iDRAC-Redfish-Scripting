#
# GetEthernetInterfacesREDFISH. Python script using Redfish API to get ethernet interface information.
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

import requests, json, sys, re, time, warnings, argparse

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description='Python script using Redfish API to get ethernet interface information')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin -d NIC.Integrated.1-1-1, this example will return detailed information for NIC.Integrated.1-1-1 only. GetEthernetInterfacesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s LinkStatus,PermanentMACAddress,IPv4Addresses, this example will only return these specific properties for all NIC interfaces detected')
parser.add_argument('-e', help='Get current ethernet FQDDs for the server, pass in \"y\". To get detailed information for all ethernet FQDDs, pass in \"yy\"', required=False)
parser.add_argument('-d', help='Get ethernet FQDD detailed information for a specific FQDD, pass in ethernet FQDD. Example, pass in NIC.Integrated.1-1-1', required=False)
parser.add_argument('-s', help='Get specific FQDD property for all ethernet devices, pass in property name. To get the list of property names, first execute \"-e yy\" to get detailed information which will return the property values. Make sure to pass in the exact string as this value is case sensitive. Note: Multiple properties can be passed in by using a comma separator', required=False)

args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]
if args["d"]:
    fqdd = args["d"]
if args["s"]:
    if "," in args["s"]:
        specific_property = args["s"].split(",")
    else:
        specific_property = [args["s"]]



def get_ethernet_interfaces():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.status_code == 401:
        print("\n- FAIL, incorrect iDRAC username or password detected")
        sys.exit()
    elif response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass
    data = response.json()
    if args["e"] == "y":
        print("\n- Ethernet FQDDs detected -\n")
    else:
        pass
    for i in data['Members']:
        for ii in i.items():
            fqdd = (ii[1].split("/")[-1])
            if args["e"] == "y":
                print(fqdd)
            else:
                pass        
            if args["e"] == "yy":
                response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, fqdd),verify=False,auth=(idrac_username, idrac_password))
                data = response.json()
                print("\n- Detailed Ethernet Information for FQDD %s -\n" % fqdd)
                for i in data.items():
                    print("%s: %s" % (i[0], i[1]))
            else:
                pass

def get_specific_ethernet_property_old():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n"),
    correct_value=0
    for i in data['Members']:
        for ii in i.items():
            fqdd = (ii[1].split("/")[-1])
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, fqdd),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            #print("\n- Property %s for FQDD %s -\n" % (specific_property,fqdd))
            for i in data.items():
                if i[0] == specific_property:
                    if i[1] == []:
                        print("- Property \"%s\" for FQDD \"%s\" is: %s" % (specific_property,fqdd, "null"))
                        correct_value=1
                    else:
                        print("- Property \"%s\" for FQDD \"%s\" is: %s" % (specific_property,fqdd, i[1]))
                        correct_value=1
    if correct_value == 0:
        print("- WARNING, invalid property value entered. Make sure you pass in supported value and the case is correct.")


def get_specific_ethernet_property():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    nic_fqdds = []
    for i in data['Members']:
        for ii in i.items():
            fqdd = (ii[1].split("/")[-1])
            nic_fqdds.append(fqdd)
    for i in nic_fqdds:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        print("\n- FQDD %s -\n" % i)
        for ii in specific_property:
            if ii in data.keys():
                print("%s: %s" % (ii, data[ii]))
            else:
                print("- WARNING, unable to locate property \"%s\". Either spelling of property is incorrect or property not supported for %s" % (ii, i))
                

def get_FQDD_details():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, fqdd),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Detailed Information for FQDD %s -\n" % fqdd)
    for i in data.items():
        print("%s: %s" % (i[0], i[1]))
    




if __name__ == "__main__":
    if args["e"] == "y" or args["e"] == "yy":
        get_ethernet_interfaces()
    elif args["d"]:
        get_FQDD_details()
    elif args["s"]:
        get_specific_ethernet_property()
        
    


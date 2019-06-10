#
# GetIdracLcSystemAttributesREDFISH. Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run this script first to get attributes with current values before you execute SetIdracLcSystemAttributesREDFISH script.
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 6.0
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

import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to get either iDRAC, lifecycle controller or system attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g idrac, this example wil get all iDRAC attributes and echo them to the screen along with copy output to a file. GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g idrac -an LDAPRoleGroup.1.Privilege, this example will only return current value for attribute LDAPRoleGroup.1.Privilege. GetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -g idrac -ar y, this example will return the attribute registry for iDRAC, LC and System attributes.') 
parser.add_argument('-g', help='Get attributes, pass in the group name of the attributes you want to get. Supported values are \"idrac\", \"lc\" and \"system\"', required=False)
parser.add_argument('-an', help='Get specific attribute value, pass in the attribute name. Make sure to also pass in -g option with the group name.', required=False)
parser.add_argument('-ar', help='Pass in \"y\" to get the attribute registry for all iDRAC, System and LC attributes. This option is helpful for viewing attributes to see if they are read only or read write, supported possible values.', required=False)
parser.add_argument('-s', help='Get attribute registry information for a specific attribute, pass in the attribute name', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        print("\nNote: If using iDRAC 7/8, this script is not supported. Use Server Configuration Profile feature instead with Redfish to get iDRAC / System and Lifecycle Controller attributes") 
        sys.exit()
    else:
        pass

def get_attribute_registry():
    try:
        os.remove("idrac_attribute_registry.txt")
    except:
        pass
    f=open("idrac_attribute_registry.txt","a")
    response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data[u'RegistryEntries']['Attributes']:
        for ii in i.items():
            message = "%s: %s" % (ii[0], ii[1])
            f.writelines(message)
            print(message)
            message = "\n"
            f.writelines(message)
        message = "\n"
        print(message)
        f.writelines(message)
    print("\n- Attribute registry is also captured in \"idrac_attribute_registry.txt\" file")
    f.close()


def attribute_registry_get_specific_attribute():
    print("\n- WARNING, searching attribute registry for attribute \"%s\"" % args["s"])
    response = requests.get('https://%s/redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    found = ""
    for i in data[u'RegistryEntries']['Attributes']:
        if args["s"] in i.values():
            print("\n- Attribute Registry information for attribute \"%s\" -\n" % args["s"])
            found = "yes"
            for ii in i.items():
                print("%s: %s" % (ii[0],ii[1]))
    if found != "yes":
        print("\n- FAIL, unable to locate attribute \"%s\" in the registry. Make sure you typed the attribute name correct since its case sensitive" % args["s"])
        

def get_attribute_group():
    global current_value
    if args["g"] == "idrac":
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "lc":
        response = requests.get('https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "system":
        response = requests.get('https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data[u'Attributes']
    print("\n- %s Attribute Names and Values:\n" % args["g"].upper())
    f = open("attributes.txt","w")
    for i in attributes_dict:
        z="Name: %s, Value: %s" % (i, attributes_dict[i])
        print(z)
        f.writelines("%s\n" % z)
    f.close()
    print("\n- WARNING, Attribute enumeration also copied to \"attributes.txt\" file")


    
def get_specific_attribute():
    global current_value
    if args["g"] == "idrac":
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "lc":
        response = requests.get('https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    elif args["g"] == "system":
        response = requests.get('https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data[u'Attributes']
    for i in attributes_dict:
        if i == args["an"]:
            print("\nAttribute Name: %s, Current Value: %s" % (i, attributes_dict[i]))
            sys.exit()
    print("\n- FAIL, unable to locate attribute \"%s\". Either current iDRAC version installed doesn\'t support this attribute or iDRAC missing required license" % args["an"])

    


    
if __name__ == "__main__":
    check_supported_idrac_version()
    if args["ar"]:
        get_attribute_registry()
    elif args["s"]:
        attribute_registry_get_specific_attribute()
    elif args["g"] and args["an"]:
        get_specific_attribute()
    elif args["g"]:
        get_attribute_group()
    else:
        print("- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")
        
        
        



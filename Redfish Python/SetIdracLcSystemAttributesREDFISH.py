#
# SetIdracLcSystemAttributesREDFISH. Python script using Redfish API to set either iDRAC, lifecycle controller or system attributes.
#
# NOTE: Recommended to run script GetIdracLcSystemAttributesREDFISH first to return attributes with current values. 
#
# NOTE: Possible supported values for attribute_group parameter are: idrac, lc and system.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to set either iDRAC, lifecycle controller or system attributes")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SetIdracLcSystemAttributesREDFISH.py -ip 192.168.0.120 -u root -p calvin -s idrac -an Time.1.Timezone,Telnet.1.Enable,RemoteHosts.1.SMTPServerIPAddress -av CST6CDT,enabled,test.labs.net, this example is setting 3 iDRAC attributes.') 
parser.add_argument('-s', help='Set attributes, pass in the group name of the attributes you want to configure. Supported values are \"idrac\", \"lc\" and \"system\"', required=True)
parser.add_argument('-an', help='Pass in the attribute name you want to configure. If you want to configure multiple attribute names, make sure to use a comma separator between each attribute name. Note: Make sure you are passing in the correct attributes which match the value you are passing in for argument -s. Note: Attribute names are case sensitive, make sure to pass in the exact syntax of the attribute name', required=True)
parser.add_argument('-av', help='Pass in the attribute value you want to set the attribute to. If you want to configure multiple attribute values, make sure to use a comma separator between each attribute value. Note: Attribute values are case sensitive, make sure to pass in the exact syntax of the attribute value', required=True)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        print("\nNote: If using iDRAC 7/8, this script is not supported. Use Server Configuration Profile feature instead with Redfish to set iDRAC / System and Lifecycle Controller attributes") 
        sys.exit()
    else:
        pass


def set_attributes():
    global url
    global payload
    if args["s"] == "idrac":
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
    elif args["s"] == "lc":
        url = 'https://%s/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes' % idrac_ip
    elif args["s"] == "system":
        url = 'https://%s/redfish/v1/Managers/System.Embedded.1/Attributes' % idrac_ip
    else:
        print("\n- FAIL, invalid value entered for -s argument")
        sys.exit()
    response = requests.get('%s' % (url),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    payload = {"Attributes":{}}
    attribute_names = args["an"].split(",")
    attribute_values = args["av"].split(",")
    for i,ii in zip(attribute_names, attribute_values):
        payload["Attributes"][i] = ii
    print("\n- WARNING, changing \"%s\" attributes -\n" % args["s"].upper())
    for i in payload["Attributes"].items():
        print(" Attribute Name: %s, setting new value to: %s" % (i[0], i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, Command passed to successfully set \"%s\" attribute(s), status code %s returned\n" % (args["s"].upper(),statusCode))
    else:
        print("\n- FAIL, Command failed to set %s attributes(s), status code is: %s\n" % (args["s"].upper(),statusCode))
        print("Extended Info Message: {0}".format(response.json()))
        sys.exit()
    
    
def get_new_attribute_values():
    print("- WARNING, checking new attribute values - \n")
    response = requests.get('%s' % (url),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    new_attributes_dict=data[u'Attributes']
    new_attribute_values = {"Attributes":{}}
    for i in new_attributes_dict.items():
        for ii in payload["Attributes"].items():
            if i[0] == ii[0]:
                if i[1].lower() == ii[1].lower():
                    print("- PASS, Attribute %s successfully set to %s" % (i[0],i[1]))
                else:
                    print("- FAIL, Attribute %s not set to %s" % (i[0],i[1]))
        


if __name__ == "__main__":
    if args["s"] and args["an"] and args["av"]:
        set_attributes()
        get_new_attribute_values()
    



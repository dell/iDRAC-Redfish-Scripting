#
# GetOSNetworkInformationREDFISH. Python script using Redfish API to get host operating system (OS) network information.
#
# NOTE: iSM (iDRAC Service Module) must be installed and running in the OS for Redfish to be able to get this data. iSM is available on Dell support site under Drivers / Downloads, System Management section for your server model.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

from datetime import datetime

warnings.filterwarnings("ignore")



parser = argparse.ArgumentParser(description='Python script using Redfish API to get operating system (iSM must be running in the OS) network information')
parser.add_argument('-ip', help='iDRAC IP Address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('-e', help='Pass in \"y\" to get script examples', required=False)
parser.add_argument('-g', help='Pass in \"y\" to get supported host network devices. Pass in \"yy\" to get detailed information for all the supported devices', required=False)
parser.add_argument('-n', help='Pass in the network device string to get specific information for this device only. You must run \"-g y\" first to get the supported network device strings.', required=False)
parser.add_argument('-i', help='Pass in the network device string. You must run \"-g y\" first to get the supported network device strings. This option is only supported with \"-a\" option to get specific property information', required=False)
parser.add_argument('-a', help='Pass in specific property name to get only this data for a specific network device. You must first execute \"-g yy\" to get the supported properties. This value is case sensitive so make sure to pass in exact syntax (Example: Pass in \"HostName\", \"hostname\" will fail. \"-i\" option is also required with \"-a\" where you must pass in the network string device. ', required=False)


args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

if args["a"]:
    property_value = args["a"]

def script_examples():
    print("""\n- SCRIPT EXAMPLES -\n\nGetOSNetworkInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y. This example will return host supported network device URI strings\n
GetOSNetworkInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -n iDRAC.Embedded.1%23ServiceModule.1%23OSLogicalNetwork.1. This example will return detailed information for this network device only\n
GetOSNetworkInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -i iDRAC.Embedded.1%23ServiceModule.1%23OSLogicalNetwork.1 -a IPv4Addresses. This example will return only information for IPv4Addresses for this network device""")
    


def get_OS_network_devices():
    f=open("lc_logs.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    valid_network_devices=[]
    for i in data[u'Members']:
        for ii in i.items():
            if "ServiceModule" not in ii[1]:
                print("\n- WARNING, no supported devices detected to get OS network information. Either server in OFF state or iSM is not running in the OS.")
                sys.exit()
            else:
                valid_network_devices.append(ii[1].split("/")[-1])
    print("\n- Supported host network devices detected to get OS network information -\n")
    for i in valid_network_devices:
        print(i)
    if args["g"] == "yy":
        for i in valid_network_devices:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, i),verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            print("\n- Detailed information for network device %s -\n") % i
            for ii in data.items():
                print("%s: %s" % (ii[0], ii[1]))
            
        

def get_individual_network_device_info():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, args["n"]),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    print("\n- Detailed information for network device %s -\n") % args["n"]
    for ii in data.items():
        print("%s: %s" % (ii[0], ii[1]))

def get_property_value_only():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/%s' % (idrac_ip, args["i"]),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    count=0
    for i in data.items():
        if i[0] == property_value:
            print("\n- Property \"%s\" information for network device %s -\n") % (property_value, args["i"])
            print("%s: %s" % (i[0], i[1]))
            count+=1
    if count == 0:
        print("\n- FAIL, invalid property name entered. Please check if valid string valur or case is correct")
        sys.exit()


if __name__ == "__main__":
    if args["g"]:
        get_OS_network_devices()
    elif args["i"] and args["a"]:
        get_property_value_only()
    elif args["n"]:
        get_individual_network_device_info()
    elif args["e"]:
        script_examples()

        



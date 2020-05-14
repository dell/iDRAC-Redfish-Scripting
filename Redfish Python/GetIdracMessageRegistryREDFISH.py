#
# GetIdracMessageRegistryREDFISH. Python script using Redfish API with OEM extension to get iDRAC message registry.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2020, Dell, Inc.
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

parser = argparse.ArgumentParser(description='Python script using Redfish API with OEM extension to get iDRAC message registry. This is helpful for finding out details on a message ID or error message returned from executing any Redfish command against iDRAC.')
parser.add_argument('-ip', help='iDRAC IP Address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-g', help='Get message registry, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get information for only a specific message id, pass in the message ID string', required=False)
parser.add_argument('script_examples',action="store_true",help='GetIdracMessageRegistryREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get the complete message registry, print to the screen and also capture in a text file. GetIdracMessageRegistryREDFISH.py -ip 192.168.0.120 -u root -p calvin -s SYS409, this example will return information for only message ID SYS409.')

args = vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def get_message_registry():
    try:
        os.remove("message_registry.txt")
    except:
        pass
    f=open("message_registry.txt","a")
    response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Messages'].items():
        message = "Message ID: %s" % i[0]
        print(message)
        f.writelines("\n%s"% message)
        for ii in i[1].items():
            message = "%s: %s" % (ii[0], ii[1])
            print(message)
            f.writelines("\n%s"% message)
        message = "\n"
        print(message)
        f.writelines("%s"% message)
    f.close()
    print("\n- WARNING, output also captured in \"message_registry.txt\" file")

def get_specific_message_id():
    response = requests.get('https://%s/redfish/v1/Registries/Messages/EEMIRegistry' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    for i in data['Messages'].items():
        if i[0].lower() == args["s"].lower():
            print("\nMessage ID: %s" % i[0])
            for ii in i[1].items():
                print("%s: %s" % (ii[0], ii[1]))
            print("\n")
            sys.exit()
        else:
            pass
    print("\n - FAIL, either invalid message ID was passed in or message ID does not exist on this iDRAC version")
    
    

if __name__ == "__main__":
    if args["g"]:
        get_message_registry()
    elif args["s"]:
        get_specific_message_id()
    else:
        print("\n- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")

        



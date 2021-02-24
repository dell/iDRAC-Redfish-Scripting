#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse, webbrowser

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to return iDRAC server root details. Only iDRAC IP address argument required, no user credentials needed.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracServiceRootDetailsNoCredsREDFISH.py -ip 192.168.0.120, this example will return Redfish service root details for iDRAC.')

args=vars(parser.parse_args())
idrac_ip=args["ip"]

def get_idrac_oem_details_no_creds():
    print("\n- iDRAC %s Redfish Service Root Details -\n" % idrac_ip) 
    response = requests.get('https://%s/redfish/v1' % idrac_ip,verify=False)
    data = response.json()
    for i in data['Oem']['Dell'].items():
        print("%s: %s" % (i[0], i[1]))
    print("Product: %s" % data['Product'])
    print("Redfish Version: %s" % data['RedfishVersion'])
                                

if __name__ == "__main__":
    try:
        get_idrac_oem_details_no_creds()
    except:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")

    
    
        
            
        
        

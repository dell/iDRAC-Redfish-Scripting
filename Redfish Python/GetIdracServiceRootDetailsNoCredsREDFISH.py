#!/usr/bin/python3
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import argparse
import getpass
import json
import logging
import requests
import sys
import warnings

from pprint import pprint

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to return iDRAC server root details. Only iDRAC IP address argument required, no user credentials needed.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracServiceRootDetailsNoCredsREDFISH.py -ip 192.168.0.120, this example will return Redfish service root details for iDRAC.')
args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def get_idrac_oem_details_no_creds():
    logging.info("\n- iDRAC %s Redfish Service Root Details -\n" % args["ip"]) 
    response = requests.get('https://%s/redfish/v1' % args["ip"], verify=False)
    data = response.json()
    for i in data['Oem']['Dell'].items():
        pprint(i)                        

if __name__ == "__main__":
    try:
        get_idrac_oem_details_no_creds()
    except:
        logging.error("- ERROR, unable to run GET on service root URI. Confirm IP address is a valid iDRAC address")

    
    
        
            
        
        

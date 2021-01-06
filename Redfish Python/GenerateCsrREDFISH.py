#!/usr/bin/python
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC certs or generate CSR for iDRAC.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GenerateCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will get current iDRAC cert(s). GenerateCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y --city Austin --commonname idrac_tester --country US --email tester@dell.com --org test --orgunit "test group" --state Texas, this example will generate CSR for iDRAC.')
parser.add_argument('-g', help='Generate iDRAC CSR, pass in \"y\". You must also pass in arguments city, state, commonname, country, email, org, orgunit for generating CSR.', required=False)
parser.add_argument('--city', help='Generate iDRAC CSR, pass in city string value', required=False)
parser.add_argument('--state', help='Generate iDRAC CSR, pass in state string value', required=False)
parser.add_argument('--commonname', help='Generate iDRAC CSR, pass in common name string value', required=False)
parser.add_argument('--country', help='Generate iDRAC CSR, pass in common name string value', required=False)
parser.add_argument('--email', help='Generate iDRAC CSR, pass in email string value', required=False)
parser.add_argument('--org', help='Generate iDRAC CSR, pass in organization string value', required=False)
parser.add_argument('--orgunit', help='Generate iDRAC CSR, pass in organization unit string value', required=False)
parser.add_argument('-c', help='Get current iDRAC certs, pass in \"y\"', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/CertificateService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, incorrect iDRAC username or password detected")
        sys.exit()
    if response.status_code == 200:
        if "#CertificateService.GenerateCSR" in data["Actions"].keys():
            pass
        else:
            print("\n- WARNING, iDRAC version detected not supported for this feature")
            sys.exit()
    else:
        print("\n- WARNING, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()


def get_current_iDRAC_certs():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        pass
    else:
        print("\n- WARNING, status code %s detected, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()
    if data["Members"] == []:
        print("- INFO, no current certs detected for iDRAC %s" % idrac_ip)
    else:
        for i in data["Members"]:
            for ii in i.items():
                print("\n- Details for cert \"%s\"\n" % ii[1].split("/")[-1])
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                data = response.json()
                for i in data.items():
                    print("%s: %s" % (i[0], i[1]))

def generate_CSR():
    print("\n- INFO, generating CSR for iDRAC %s, this may take a few seconds to complete\n" % idrac_ip)
    url = 'https://%s/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR' % (idrac_ip)
    payload = {"CertificateCollection":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates","City":args["city"],"CommonName":args["commonname"],"Country":args["country"],"Email":args["email"],"Organization":args["org"],"OrganizationalUnit":args["orgunit"],"State":args["state"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    data_post = response.json()
    if response.status_code == 200:
        pass
    else:
        print("- FAIL, generate CSR failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data_post))
        sys.exit()
    print("\n- INFO, CSR generated for iDRAC %s\n" % idrac_ip)
    print(data_post["CSRString"])
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data_get = response.json()
    if response.status_code == 200:
        model_name = data_get["Model"].replace(" ","")
        service_tag = data_get["SKU"]
        filename = model_name+"_"+service_tag+".csr"
    else:
        print("-INFO, unable to get model and service tag information, using iDRAC IP for filename")
        filename = "%s.csr" % idrac_ip
    try:
        os.remove(filename)
    except:
        pass
    with open(filename, "a") as x:
        x.writelines(data_post["CSRString"])
    print("\n- Generated CSR also copied to file \"%s\"" % filename)
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"] and args["city"] and args["state"] and args["commonname"] and args["country"] and args["email"] and args["org"] and args["orgunit"]:
        generate_CSR()
    elif args["c"]:
        get_current_iDRAC_certs()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    



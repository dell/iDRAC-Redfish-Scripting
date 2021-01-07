#!/usr/bin/python
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current iDRAC certs or replace CSR for iDRAC. When replacing CSR, make sure the CSR has been signed first and once replaced, iDRAC must be reset for the new CSR to be applied.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ReplaceCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will get current iDRAC cert(s). ReplaceCsrREDFISH.py -ip 192.168.0.120 -u root -p calvin -r SecurityCertificate.1 -f signed_CSR_cert.cer, this example will replace current CSR with new signed CSR.')
parser.add_argument('-r', help='Replace iDRAC CSR, pass in the cert ID of the cert you want to replace. If needed, execute -c argument to get the cert ID. Example: SecurityCertificate.1', required=False)
parser.add_argument('-f', help='Replace iDRAC CSR, pass in the filename of the signed CSR.', required=False)
parser.add_argument('-c', help='Get current iDRAC certs, pass in \"y\"', required=False)
parser.add_argument('--reset', help='Reset iDRAC, pass in \"y\". Note: Reset of iDRAC is needed after CSR has been replaced. New CSR will not get applied until iDRAC has been reset.', required=False)

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

def replace_CSR():
    print("\n- INFO, replacing CSR for iDRAC %s\n" % idrac_ip)
    url = 'https://%s/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate' % (idrac_ip)
    try:
        open_filename = open(args["f"],"r")
    except:
        print("- FAIL, unable to locate file \"%s\"" % args["f"])
        sys.exit()
    read_file = open_filename.read()
    open_filename.close()
    payload = {"CertificateType": "PEM","CertificateUri":"/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates/%s" % args["r"],"CertificateString":read_file}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS, replace CSR cert passed. iDRAC reset is needed for new cert to be applied. Execute script using --reset argument to reset the iDRAC.")
    else:
        print("- FAIL, replace CSR failed, status code %s returned, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()
    print(data)


def reset_idrac():
    url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % idrac_ip
    payload={"ResetType":"GracefulRestart"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers,verify=False, auth=(idrac_username, idrac_password))
    if response.status_code == 204:
        print("\n- PASS, status code %s returned for POST command to reset iDRAC\n" % response.status_code)
    else:
        data=response.json()
        print("\n- FAIL, status code %s returned, detailed error is: \n%s" % (response.status_code, data))
        sys.exit()
    time.sleep(15)
    print("- INFO, iDRAC will now reset and be back online within a few minutes.")


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["r"] and args["f"]:
        replace_CSR()
    elif args["c"]:
        get_current_iDRAC_certs()
    elif args["reset"]:
        reset_idrac()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    



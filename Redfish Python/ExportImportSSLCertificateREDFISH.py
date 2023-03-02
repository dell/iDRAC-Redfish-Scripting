#!/usr/bin/python3
#
# ExportImportSSLCertificateREDFISH.py   Python script using Redfish API with OEM extension to either export or import SSL certificate.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 10.0
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

import argparse
import base64
import getpass
import json
import logging
import os
import requests
import sys
import time
import warnings

from pprint import pprint

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either export or import SSL certificate locally")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('--ssl', help='Verify SSL certificate for all Redfish calls, pass in \"true\". This argument is optional, if you do not pass in this argument, all Redfish calls will ignore SSL cert checks.', required=False)
parser.add_argument('-x', help='Pass in iDRAC X-auth token session ID to execute all Redfish calls instead of passing in username/password', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--export', help='Export SSL certificate. Argument --cert-type is also required for export SSL cert', action="store_true", required=False)
parser.add_argument('--import', help='Import SSL certificate. Argument --cert-type and --filename is also required for import SSL cert. Note: Once cert is successfully imported, script will prompt to reboot iDRAC which is needed to apply the new cert.', action="store_true", required=False)
parser.add_argument('--get-current-certs', help='Get current iDRAC certificates detected/installed', action="store_true", dest="get_current_certs", required=False)
parser.add_argument('--get-cert-types', help='Get current cert type values supported for Export or Import certificates.', action="store_true", dest="get_cert_types", required=False)
parser.add_argument('--cert-type', help='Pass in SSL cert type value for export or import (note: this value is case sensitive). If needed, use argument --get-cert-types to get supported values.', dest="cert_type", required=False)
parser.add_argument('--filename', help='Pass in the file name which contains the certificate to import. Cert file should be a base64 encoded string of the XML Certificate file. For importing CSC certificate, convert PKCS file to base64 format. The CTC file content has to be in PEM format (base64 encoded).', required=False)
parser.add_argument('--passphrase', help='Pass in passphrase string if the cert you are importing is passpharse protected.', required=False)
parser.add_argument('--reboot-idrac', help='Pass in this argument to reboot the iDRAC now to apply the new cert imported. Note: Starting in iDRAC 6.00.02 version, iDRAC reboot is no longer required after the new cert is imported.', dest="reboot_idrac", action="store_true", required=False)

args=vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO) 

def script_examples():
    print("""\n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-current-certs, this example will return current detected/installed certificates.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-cert-types, this example will return current cert type supported values for export or import cert operations.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --export --cert-type Server, this example will export current iDRAC Server certificate.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --import --cert-type CustomCertificate --filename signed_cert_R740.pem --passphrase Test1234#, this example using iDRAC 6.00.02 will import custom signed p12 cert with a passphrase.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --import --cert-type CSC --filename signed_cert_R740.pem --reboot-idrac, this example using iDRAC 5.10 will import signed p12 file and reboot the iDRAC.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 --export --cert-type Server -ssl true -x 52396c8ac35e15f7b2de4b18673b111f, this example shows validating ssl cert for all Redfish calls to export server cert using X-auth token session.""")
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_cert_types():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET commmand failed to get cert types supported for export/import cert operations, status code %s returned" % response.status_code)
        logging.error("- Detailed error results: %s" % data)
        sys.exit(0)
    for i in data["Actions"].items():
        if i[0] == "#DelliDRACCardService.ExportSSLCertificate":
            logging.info("\n- Support cert type values for ExportSSLCertificate -\n")
            for ii in i[1].items():
                if ii[0] == "SSLCertType@Redfish.AllowableValues":
                    print(ii[1])
        if i[0] == "#DelliDRACCardService.ImportSSLCertificate":
            logging.info("\n- Support cert type values for ImportSSLCertificate -\n")
            for ii in i[1].items():
                if ii[0] == "CertificateType@Redfish.AllowableValues":
                    print(ii[1])

def get_current_certs():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/CertificateService/CertificateLocations?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/CertificateService/CertificateLocations?$expand=*($levels=1)' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET commmand failed to get current cert details, status code %s returned" % response.status_code)
        logging.error("- Detailed error results: %s" % data)
        sys.exit(0)
    for i in data.items():
        pprint(i)

def export_SSL_cert():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (idrac_ip)
    method = "ExportSSLCertificate"
    payload={"SSLCertType":args["cert_type"]}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code 202 returned\n" % method)
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)
    logging.info("\n- Detailed SSL certificate information for certificate type \"%s\"\n" % args["cert_type"])
    logging.info(data['CertificateFile'])
    try:
        os.remove("ssl_certificate.txt")
    except:
        pass
    with open("ssl_certificate.txt","w") as x:
        x.writelines(data['CertificateFile'])
    logging.info("\n - SSL certificate information also copied to \"%s\ssl_certificate.txt\" file" % os.getcwd())
    
def import_SSL_cert():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ImportSSLCertificate' % (idrac_ip)
    method = "ImportSSLCertificate"
    if "p12" in args["filename"]:
        with open(args["filename"], 'rb') as cert:
            cert_content = cert.read()
            read_file = base64.encodebytes(cert_content).decode('ascii')
    else:
        with open(args["filename"],"r") as x:
            read_file = x.read()
    payload={"CertificateType":args["cert_type"],"SSLCertificateFile":read_file}
    if args["passphrase"]:
        payload["Passphrase"] = args["passphrase"]
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code 202 returned\n" % method)
        if args["reboot_idrac"]:
            logging.info("- INFO: user selected to reboot iDRAC now to apply the new imported cert")
            url = "https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset/" % idrac_ip
            payload={"ResetType":"GracefulRestart"}
            if args["x"]:
                headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
            else:
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
            if response.status_code == 204:
                logging.info("\n- PASS, status code %s returned for POST command to reset iDRAC\n" % response.status_code)
            else:
                data = response.json()
                logging.info("\n- FAIL, status code %s returned, detailed error is: \n%s" % (response.status_code, data))
                sys.exit(0)
            time.sleep(15)
            logging.info("- INFO, iDRAC will now reboot and be back online within a few minutes.")
        else:
            logging.info("- INFO, argument --reboot-idrac not detected, if using iDRAC version older than 6.00.02, iDRAC reboot is required to apply the new cert after import.")
            sys.exit(0)                  
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)

if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and args["ssl"] or args["u"] or args["p"] or args["x"]:
        idrac_ip=args["ip"]
        idrac_username=args["u"]
        if args["p"]:
            idrac_password=args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- Argument -p not detected, pass in iDRAC user %s password: " % args["u"])
        if args["ssl"]:
            if args["ssl"].lower() == "true":
                verify_cert = True
            elif args["ssl"].lower() == "false":
                verify_cert = False
            else:
                verify_cert = False
        else:
                verify_cert = False
        check_supported_idrac_version()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)
    if args["get_cert_types"]:
        get_cert_types()
    elif args["get_current_certs"]:
        get_current_certs()
    elif args["export"] and args["cert_type"]:
        export_SSL_cert()
    elif args["import"] and args["cert_type"] and args["filename"]:
        import_SSL_cert()
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

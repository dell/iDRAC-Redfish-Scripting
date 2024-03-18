#!/usr/bin/python3
#
# ExportImportSSLCertificateREDFISH.py   Python script using Redfish API with OEM extension to either export or import SSL certificate.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 13.0
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
import csv
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
parser.add_argument('--csv-file', help='Pass in name of CSV file to configure multiple iDRACs instead of using argument -ip for one iDRAC. For the CSV file creation column A header will be "iDRAC IP" and column B header will be "Cert Name" for the cert you want to import for that iDRAC. If only exporting you only need to fill in column A for iDRAC IPs. Note: arguments -u and -p are still required for iDRAC username and password which this user must be the same on all iDRACs.', required=False)
parser.add_argument('--upload', help='Upload SSL key, --filename is also required to pass in the key file name', action="store_true", required=False)
parser.add_argument('--delete', help='Delete SSL cert pass in value CustomCertificate, CSC or ClientTrustCertificate. iDRAC does not support delete server or CA certs', required=False)
parser.add_argument('--restore-factory-defaults', help='Restore the webserver certificate to factory defaults', action="store_true", dest="restore_factory_defaults", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

"""
CSV file contents example:

Column A 		Column B
iDRAC IP (header name)	Cert name (header name)
100.65.64.68		idrac-CTX4FF3.pem
100.65.242.194		idrac-7QZ0DN2.pem

"""

def script_examples():
    print("""\n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-current-certs, this example will return current detected/installed certificates.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-cert-types, this example will return current cert type supported values for export or import cert operations.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --export --cert-type Server, this example will export current iDRAC Server certificate.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --import --cert-type CustomCertificate --filename signed_cert_R740.pem --passphrase Test1234#, this example using iDRAC 6.00.02 will import custom signed p12 cert with a passphrase.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --import --cert-type CSC --filename signed_cert_R740.pem --reboot-idrac, this example using iDRAC 5.10 will import signed p12 file and reboot the iDRAC.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 --export --cert-type Server -ssl true -x 52396c8ac35e15f7b2de4b18673b111f, this example shows validating ssl cert for all Redfish calls to export server cert using X-auth token session.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --export --cert-type Server --csv-file iDRAC_ips.csv, this example will export current Server certificate for multiple iDRAC IPs using csv file.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --import --cert-type CustomCertificate --csv-file iDRAC_IPs.csv, this example will import custom certificates for multiple iDRAC IPs using csv file.
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --upload --filename key.pem, this example shows uploading SSL key file
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete CustomCertificate, this example shows deleting custom SSL cert
    \n- ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin --upload --restore-factory-defaults, this example shows restore webserver cert to factory default""")
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

def get_iDRAC_version():
    global iDRAC_version
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1?$select=FirmwareVersion' % idrac_ip, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.error("- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        return
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if int(data["FirmwareVersion"].replace(".","")) >= 6000000:
        iDRAC_version = "new"
    else:
        iDRAC_version = "old"

def get_cert_types():
    if args["x"]:
         response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- ERROR, GET command failed to get cert types supported for export/import cert operations, status code %s returned" % response.status_code)
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
        logging.error("\n- ERROR, GET command failed to get current cert details, status code %s returned" % response.status_code)
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
        os.remove("%s_ssl_certificate.txt" % idrac_ip)
    except:
        pass
    with open("%s_ssl_certificate.txt" % idrac_ip,"w") as x:
        x.writelines(data['CertificateFile'])
    logging.info("\n- SSL certificate information also copied to \"%s\%s_ssl_certificate.txt\" file" % (os.getcwd(), idrac_ip))

def delete_SSL_cert():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.DeleteSSLCertificate' % (idrac_ip)
    method = "DeleteSSLCertificate"
    payload={"CertificateType":args["delete"]}
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

def restore_factory_defaults():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.SSLResetCfg' % (idrac_ip)
    method = "SSLResetCfg"
    payload={}
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

def upload_SSL_key():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.UploadSSLKey' % (idrac_ip)
    method = "UploadSSLKey"
    if "p12" in args["filename"]:
        with open(args["filename"], 'rb') as cert:
            cert_content = cert.read()
            read_file = base64.encodebytes(cert_content).decode('ascii')
    else:
        with open(args["filename"],"r") as x:
            read_file = x.read()
    payload = {"SSLKeyString":read_file}
    if args["x"]:
        headers = {'content-type': 'application/json', 'X-Auth-Token': args["x"]}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert)
    else:
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 200:
        logging.info("\n- PASS: POST command passed for %s method, status code 200 returned" % method)
    else:
        logging.error("\n- FAIL, POST command failed to upload SSL key, status code %s returned\n" % response.status_code)
        print(data)
        sys.exit(0)
    
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
        logging.info("\n- PASS: POST command passed for %s method, status code 202 returned" % method)
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
            get_iDRAC_version()
            if iDRAC_version == "old":
                logging.info("- INFO, argument --reboot-idrac not detected and iDRAC version older than 6.00.02 detected, iDRAC reboot is required to apply the new cert after import.")
            else:
                logging.info("- INFO, iDRAC will report newly imported cert within 15-30 seconds, if using browser to access the iDRAC refresh the session")
    else:
        logging.error("\n- FAIL, POST command failed for %s method, status code %s returned" % (method, response.status_code))
        data = response.json()
        logging.error("\n- POST command failure results:\n %s" % data)
        sys.exit(0)

if __name__ == "__main__":
    if args["csv_file"]:
        csv_file_path = args["csv_file"]
        with open(csv_file_path, 'r') as csv_file:
            csv_contents = csv.DictReader(csv_file)
            for i in csv_contents:
                idrac_ip = i["iDRAC IP"]
                if i["Cert Name"] != "":
                    args["filename"] = i["Cert Name"]
                if args["script_examples"]:
                    script_examples()
                if args["ssl"] or args["u"] or args["p"] or args["x"]:
                    idrac_username = args["u"]
                    if args["p"]:
                        idrac_password = args["p"]
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
                    logging.info("\n- INFO, performing export cert operation for iDRAC %s" % idrac_ip)
                    export_SSL_cert()
                elif args["import"] and args["cert_type"]:
                    logging.info("\n- INFO, performing import cert operation for iDRAC %s to import cert %s" % (idrac_ip, args["filename"]))
                    import_SSL_cert()
                else:
                    logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
    else:
        if args["script_examples"]:
            script_examples()
        if args["ip"] or args["ssl"] or args["u"] or args["p"] or args["x"]:
            idrac_ip = args["ip"]
            idrac_username = args["u"]
            if args["p"]:
                idrac_password = args["p"]
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
        elif args["upload"] and args["filename"]:
            upload_SSL_key()
        elif args["delete"]:
            delete_SSL_cert()
        elif args["restore_factory_defaults"]:
            restore_factory_defaults()
        else:
            logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")

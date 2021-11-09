#
# ExportImportSSLCertificateREDFISH.py   Python script using Redfish API with OEM extension to either export or import SSL certificate.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
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


import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to either export or import SSL certificate locally")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin -e y -sct 1\", this example will export Web Server Certificate locally\n- \"ExportImportSSLCertificateREDFISH.py -ip 192.168.0.120 -u root -p calvin -i y -ct 4 -scf ssl_cert.pem\", this example will import client trust certificate')
parser.add_argument('-e', help='Export SSL cert, pass in \"y\". Argument -sct is also required for export SSL cert', required=False)
parser.add_argument('-i', help='Import SSL cert, pass in \"y\". Argument -ct and -scf is also required for import SSL cert', required=False)
parser.add_argument('-sct', help='Pass in SSL cert type for export. Supported values are: 1 for \"Server\"(Web Server Certificate), 2 for \"CSC\"(Custom Signing Certificate), 3 for \"CA\"(CA certificate for Directory Service), 4 for \"ClientTrustCertificate\"', required=False)
parser.add_argument('-ct', help='Pass in cert type for import. Supported values are: 1 for \"Server\"(Web Server Certificate), 2 for \"CSC\"(Custom Signing Certificate), 3 for \"CA\"(CA certificate for Directory Service:), 4 for \"ClientTrustCertificate\"', required=False)
parser.add_argument('-scf', help='Pass in the file name which contains tae certificate to import. Cert file should be a base64 encoded string of the XML Certificate file. For importing CSC certificate, convert PKCS file to base64 format. The CTC file content has to be in PEM format (base64 encoded).', required=False)
parser.add_argument('-s', help='Pass in passphrase string if the cert you are importing has one assigned', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def export_SSL_cert():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (idrac_ip)
    method = "ExportSSLCertificate"
    if args["sct"] == "1":
        cert_type = "Server"
    elif args["sct"] == "2":
        cert_type = "CSC"
    elif args["sct"] == "3":
        cert_type = "CA"
    elif args["sct"] == "4":
        cert_type = "ClientTrustCertificate"
    else:
        print("- FAIL, invalid value passed in for -sct argument")
        sys.exit()
    headers = {'content-type': 'application/json'}
    payload={"SSLCertType":cert_type}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code 202 returned\n" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    print("\n- Detailed SSL certificate information for certificate type \"%s\"\n" % cert_type)
    print(data['CertificateFile'])
    try:
        os.remove("ssl_certificate.txt")
    except:
        pass
    f = open("ssl_certificate.txt","w")
    f.writelines(data['CertificateFile'])
    f.close()
    print("\n - SSL certificate information also copied to \"%s\ssl_certificate.txt\" file" % os.getcwd())
    


def import_SSL_cert():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ImportSSLCertificate' % (idrac_ip)
    method = "ImportSSLCertificate"
    if args["ct"] == "1":
        cert_type = "Server"
    elif args["ct"] == "2":
        cert_type = "CSC"
    elif args["ct"] == "3":
        cert_type = "CA"
    elif args["ct"] == "4":
        cert_type = "ClientTrustCertificate"
    else:
        print("- FAIL, invalid value passed in for -sct argument")
        sys.exit()
    headers = {'content-type': 'application/json'}
    f = open(args["scf"],"r")
    read_file = f.read()
    f.close()
    payload={"CertificateType":cert_type,"SSLCertificateFile":read_file}
    if args["s"]:
        payload["Passphrase"] = args["s"]
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code 202 returned\n" % method)
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["e"] and args["sct"]:
        export_SSL_cert()
    elif args["i"] and args["ct"] and args["scf"]:
        import_SSL_cert()
    else:
        print("- FAIL, invalid argument values or not all required parameters passed in")
    
    
        
            
        
        

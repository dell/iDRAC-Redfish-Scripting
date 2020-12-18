#!/usr/bin/python
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

import requests, json, sys, re, time, os, warnings, argparse, shutil

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to manage BIOS DBX certificates.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get all DBX certs. SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -s /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84, this example will only return data for this DBX cert. SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -eu /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84 -e dbx_84_cert.hsh, this example will export DBX cert 84. SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -d /redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/CustSecbootpolicy.84, this example deletes DBX cert 84. SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -r y, this example reboots the server. Reboot the server is required after delete or import DBX cert for the changes to be applied. SecureBootCertificatesDbxREDFISH.py -ip 192.168.0.120 -u root -p calvin -i dbx_84_cert.hsh -l C:\Python38-32 -t SHA256, this example will import DBX cert.') 
parser.add_argument('-g', help='Get all DBX cert URIs, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get specific DBX cert only, pass in URI', required=False)
parser.add_argument('-e', help='Export DBX cert, pass in unique filename to create and make sure to pass in .hsh file extension. Argument -eu is also required for export.', required=False)
parser.add_argument('-eu', help='Export DBX cert, pass in the DBX URI.', required=False)
parser.add_argument('-i', help='Import DBX cert, pass in filename. Arguments -l and -t are also required when importing. Supported filename extensions are .hsh or .efi', required=False)
parser.add_argument('-l', help='Import DBX cert, pass in filename directory location', required=False)
parser.add_argument('-t', help='Import DBX cert, pass in the hash type. Supported values are SHA256, SHA384 and SHA512', required=False)
parser.add_argument('-d', help='Delete DBX cert, pass in URI', required=False)
parser.add_argument('-r', help='Reboot server, pass in \"y\". After delete or import DBX cert, server reboot is needed to apply the changes.', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]





def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    elif response.status_code == 401:
        print("- WARNING, incorrect iDRAC username or password detected")
        sys.exit()
    else:
        pass




def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % statusCode)
            print("- WARNING, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                print("- WARNING, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, POST command passed to perform forced shutdown, status code return is %s" % statusCode)
                    time.sleep(15)
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        print("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        print("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit()    
            else:
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()

def export_DBX():
    response = requests.get('https://%s%s' % (idrac_ip, args["eu"]),verify=False,auth=(idrac_username,idrac_password),headers={"accept":"application/octet-stream"}, stream=True)
    if response.status_code == 200:
        print("\n- PASS, export DBX cert was successful")
    else:
        data = response.json()
        print("\n- FAIL, export DBX cert failed, status code %s returned, detailed error: \n%s" % (response.status_code, data))
        sys.exit()
    with open(args["e"], 'wb') as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)
    print("- INFO, DBX cert copied to file \"%s\"" % args["e"])


def import_DBX():
    filename = args["i"]
    ImageLocation = args["l"]
    ImagePath = os.path.join(ImageLocation, filename)
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/DBX/' % (idrac_ip)
    payload = {"CryptographicHash": args["t"]}
    files = {'text':(None, json.dumps(payload), 'application/json'),'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    response = requests.post(url, files=files, data = payload, auth = (idrac_username, idrac_password), verify=False)
    if response.status_code == 200 or response.status_code == 202:
        print("\n- PASS, import DBX cert passed. Server reboot is required to apply the changes.")
    else:
        data = response.json()
        print("- FAIL, POST command failed to import DBX cert, status code %s returned. Error results: \n%s" % (response.status_code, data))
        sys.exit()
        

def get_all_DBX_URIs():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/SecureBoot/Certificates/%s' % (idrac_ip, "DBX"),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    print("\n- Ceritificate \"%s\" Key Type Entries For iDRAC %s -\n" % ("DBX", idrac_ip))
    time.sleep(3)
    if data["Hash"] == []:
        key = "Certificates"
    elif data["Certificates"] == []:
        key = "Hash"
    else:
        print("\n- WARNING, no certificate entries detected")
        sys.exit()
    for i in data[key]:
        for ii in i.items():
            print("%s: %s" % (ii[0], ii[1]))
        print("\n")

def get_DBX_uri():
    response = requests.get('https://%s%s' % (idrac_ip, args["s"]),verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    print("\n- Certificate information for URI \"%s\" -\n" % args["s"])
    for i in data.items():
        print("%s: %s" % (i[0], i[1]))

def delete_hash():
    url = 'https://%s%s' % (idrac_ip, args["d"])
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("- FAIL, unable to delete certificate hash, status code is %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit()
    else:
        print("\n- PASS, DELETE command passed to delete certificate hash. Server reboot is required to apply the changes.")


if __name__ == "__main__":
    if args["e"] and args["eu"]:
        export_DBX()
    elif args["g"]:
        get_all_DBX_URIs()
    elif args["i"] and args["l"] and args["t"]:
        import_DBX()
    elif args["s"]:
        get_DBX_uri()
    elif args["d"]:
        delete_hash()
    elif args["r"]:
        reboot_server()
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")
    



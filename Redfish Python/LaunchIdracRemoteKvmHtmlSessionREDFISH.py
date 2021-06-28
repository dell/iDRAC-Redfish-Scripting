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


import requests, json, sys, re, time, warnings, argparse, os, subprocess, webbrowser, csv

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to launch iDRAC HTML KVM session using your default browser.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-t', help='Pass in virtual console plugin type, supported values: \"HTML5\" or \"eHTML5\"', required=True)
parser.add_argument('script_examples',action="store_true",help='LaunchIdracRemoteKvmHtmlSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin -t eHTML5, this example will launch iDRAC eHTML5 KVM session using your default browser.')

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit(1)
    else:
        pass
    data = response.json()
    supported = "no"
    for i in data['Actions'].keys():
        if "GetKVMSession" in i:
            supported = "yes"
        else:
            pass
    if supported == "no":
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(1)
    else:
        pass


def get_set_iDRAC_vconsole_plugin():
    print("\n- INFO, getting current value for iDRAC attribute \"%s\"" % "VirtualConsole.1.PluginType")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    attributes_dict=data['Attributes']
    locate_attribute = "no"
    for i in attributes_dict:
        if i == "VirtualConsole.1.PluginType":
            print("- INFO, Attribute Name: %s, Current Value: %s" % (i, attributes_dict[i]))
            current_value = attributes_dict[i]
            locate_attribute = "yes"
    if locate_attribute == "no":
        print("\n- FAIL, unable to locate attribute \"%s\". Either current iDRAC version installed doesn\'t support this attribute or iDRAC missing required license" % "VirtualConsole.1.PluginType")
        sys.exit(1)
    else:
        pass
    if current_value != args["t"]:
        print("- INFO, attribute \"%s\" current value not set to %s, executing PATCH operation" % ("VirtualConsole.1.PluginType", args["t"]))
        url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
        payload = {'Attributes': {'VirtualConsole.1.PluginType': '%s' % args["t"]}}
        headers = {'content-type': 'application/json'}
        response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code == 200 or response.status_code == 202:
            print("- PASS, PATCH command passed to successfully set attribute \"%s\"" % "VirtualConsole.1.PluginType")
            time.sleep(10)
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            attributes_dict=data['Attributes']
            for i in attributes_dict:
                if i == "VirtualConsole.1.PluginType":
                    new_current_value = attributes_dict[i]
            if new_current_value == args["t"]:
                print("- PASS, verified attribute \"%s\" is set to %s" % ("VirtualConsole.1.PluginType",args["t"]))
            else:
                print("- FAIL, verified attribute \"%s\" is NOT set to %s, current value is \"%s\"" % ("VirtualConsole.1.PluginType", args["t"],new_current_value))
                sys.exit()
        else:
            print("- FAIL, PATCH command failed to set attribute \"%s\", status code \"%s\" returned, detailed error results:\n%s" % ("VirtualConsole.1.PluginType", response.status_code, data))
            sys.exit(1)
    else:
        print("- INFO, attribute \"%s\" current value set to %s, skipping PATCH operation" % ("VirtualConsole.1.PluginType", args["t"]))
        
def export_ssl_cert():
    print("- INFO, exporting iDRAC SSL server cert")
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"SSLCertType":"Server"}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, POST command failed for ExportSSLCertificate action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(1)
    try:
        os.remove("ssl_cert.txt")
    except:
        pass
    try:
        with open("ssl_cert.txt", "w") as x:
            x.write(data['CertificateFile'])
    except:
        print("- FAIL, unable to write cert contents to file")
        sys.exit(1)

def get_KVM_session_info():
    print("- INFO, getting KVM session temporary username, password")
    global temp_username
    global temp_password
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.GetKVMSession' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"SessionTypeName":"ssl_cert.txt"}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, POST command failed for GetKVMSession action, status code returned: %s, detailed error results: \n%s" % (response.status_code, data))
        sys.exit(1)
    try:
        temp_username = data["TempUsername"]
        temp_password = data["TempPassword"]
    except:
        print("- FAIL, unable to locate temp username or password in JSON output")
        sys.exit(1)


def launch_KVM_session():
    print("- INFO, launching iDRAC KVM session using your default browser")
    uri_string = "https://%s/console?username=%s&tempUsername=%s&tempPassword=%s" % (idrac_ip, idrac_username, temp_username, temp_password)
    webbrowser.open(uri_string)
    try:
        os.remove("ssl_cert.txt")
    except:
        pass






if __name__ == "__main__":
    check_supported_idrac_version()
    get_set_iDRAC_vconsole_plugin()
    export_ssl_cert()
    get_KVM_session_info()
    launch_KVM_session()








    

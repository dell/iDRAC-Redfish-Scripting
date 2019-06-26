#
# IdracLicenseManagementREDFISH. Python script using Redfish API with OEM extension to manage iDRAC license(s).
#
# 
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to manage iDRAC license(s). Supported script operations are: view current licenses, export / import / delete licenses")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='IdracLicenseManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will return current licenses detected. IdracLicenseManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin -el 7386PA_iDRAC_Enterprise_license, this example will export iDRAC Enterprise license locally. IdracLicenseManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin -in y --ipaddress 192.168.0.130 --sharetype NFS --sharename /nfs --licensename iDRAC_enterprise_license.xml, this example will import iDRAC enterprise license from NFS share') 
parser.add_argument('-g', help='Get current iDRAC license(s), pass in \"y\"', required=False)
parser.add_argument('-el', help='Export iDRAC license locally, pass in the license ID you want to export', required=False)
parser.add_argument('-en', help='Export iDRAC license to network share, pass in the license ID you want to export', required=False)
parser.add_argument('-in', help='Import iDRAC license from network share, pass in \"y\"', required=False)
parser.add_argument('-d', help='Delete iDRAC license, pass in the license ID you want to delete', required=False)
parser.add_argument('--ipaddress', help='Pass in the IP address of the network share to export / import iDRAC license', required=False)
parser.add_argument('--sharetype', help='Pass in the share type of the network share to export / import iDRAC license. If needed, use argument -st to get supported values for your iDRAC firmware version', required=False)
parser.add_argument('-st', help='Pass in \"y\" to get supported network share type values for your iDRAC firmware version', required=False)
parser.add_argument('--sharename', help='Pass in the network share name for export / import iDRAC license', required=False)
parser.add_argument('--username', help='Pass in the network share username (only required for CIFS share)', required=False)
parser.add_argument('--password', help='Pass in the network share username password (only required for CIFS share)', required=False)
parser.add_argument('--workgroup', help='Pass in the workgroup of your CIFS network share. This argument is optional', required=False)
parser.add_argument('--ignorecertwarning', help='Supported values are On and Off. This argument is only required if using HTTPS for share type', required=False)
parser.add_argument('--licensename', help='Pass in name of the license file on the network share you want to import', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_idrac_license_info():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseCollection' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    if response.status_code != 200:
        print("\n- FAIl, GET command failed to find iDRAC license data, error is: %s" % response)
        sys.exit()
    else:
        pass
    data = response.json()
    if data[u'Members'] == []:
        print("\n- WARNING, no licenses detected for iDRAC %s" % idrac_ip)
    else:
        print("\n- License(s) detected for iDRAC %s -\n" % idrac_ip)
        for i in (data[u'Members']):
            for ii in i.items():
                print("%s: %s" % (ii[0], ii[1]))
            print("\n")
   

def get_network_share_types():
    response = requests.get('https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    if response.status_code != 200:
        print("\n- FAIl, GET command failed to get supported network share types, error is: %s" % response)
        sys.exit()
    else:
        pass
    data = response.json()
    print("\n- Supported network share types for Export / Import license from network share -\n")
    for i in data[u'Actions'][u'#DellLicenseManagementService.ExportLicenseToNetworkShare'][u'ShareType@Redfish.AllowableValues']:
        print(i)
    

def export_idrac_license_locally():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicense' % (idrac_ip)
    method = "ExportLicense"
    headers = {'content-type': 'application/json'}
    payload={"EntitlementID":args["el"]}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    print("- iDRAC license for \"%s\" ID:\n" % args["el"])
    print(data[u'LicenseFile'])
    with open("%s_iDRAC_license.xml" % args["el"], "w") as x:
        x.writelines(data[u'LicenseFile'])
    print("\n- License also copied to \"%s_iDRAC_license.xml\" file" % args["el"])
    
def export_import_idrac_license_network_share():
    global job_id
    headers = {'content-type': 'application/json'}
    license_filename = "%s_iDRAC_license.xml" % args["en"]
    if args["en"]:
        method = "ExportLicenseToNetworkShare"
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ExportLicenseToNetworkShare' % (idrac_ip)
        payload = {"EntitlementID":args["en"],"FileName":license_filename}
    elif args["in"]:
        method = "ImportLicenseFromNetworkShare"
        url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.ImportLicenseFromNetworkShare' % (idrac_ip)
        payload = {"FQDD":"iDRAC.Embedded.1","ImportOptions":"Force"}
        if args["licensename"]:
            payload["LicenseName"] = args["licensename"]
    if args["ipaddress"]:
        payload["IPAddress"] = args["ipaddress"]
    if args["sharetype"]:
        payload["ShareType"] = args["sharetype"]
    if args["sharename"]:
        payload["ShareName"] = args["sharename"]
    if args["username"]:
        payload["UserName"] = args["username"]
    if args["password"]:
        payload["Password"] = args["password"]
    if args["workgroup"]:
        payload["Workgroup"] = args["workgroup"]
    if args["ignorecertwarning"]:
        payload["IgnoreCertificateWarning"] = args["ignorecertwarning"]
    print("\n- WARNING, arguments and values for %s method\n" % method)
    for i in payload.items():
        if i[0] == "ShareParameters":
            for ii in i[1].items():
                if ii[0] == "Password":
                    print("Password: **********")
                else:
                    print("%s: %s" % (ii[0],ii[1]))
        else:
            print("%s: %s" % (i[0],i[1]))
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 202:
        print("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    try:
        job_id = response.headers['Location'].split("/")[-1]
    except:
        print("- FAIL, unable to find job ID in headers POST response, headers output is:\n%s" % response.headers)
        sys.exit()
    print("- PASS, job ID %s successfuly created for %s method\n" % (job_id, method))


def delete_idrac_license():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLicenseManagementService/Actions/DellLicenseManagementService.DeleteLicense' % (idrac_ip)
    method = "DeleteLicense"
    headers = {'content-type': 'application/json'}
    payload={"EntitlementID":args["d"],"DeleteOptions":"Force"}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200:
        print("\n- PASS: POST command passed for %s method, status code %s returned\n" % (method, response.status_code))
    else:
        print("\n- FAIL, POST command failed for %s method, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n- POST command failure results:\n %s" % data)
        sys.exit()
    

def loop_job_status():
    start_time=datetime.now()
    time.sleep(1)
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:05:00":
            print("\n- FAIL: Timeout of 5 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or data[u'JobState'] == "Failed":
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            if data[u'Message'] == "The command was successful":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
            else:
                print("\n--- FAIL, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- WARNING, JobStatus not completed, current job status execution time is: \"%s\"" % (str(current_time)[0:7]))


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_idrac_license_info()
    elif args["el"]:
        export_idrac_license_locally()
    elif args["st"]:
        get_network_share_types()
    elif args["en"] or args["in"]:
        export_import_idrac_license_network_share()
        loop_job_status()
    elif args["d"]:
        delete_idrac_license()
    else:
        print("\n- FAIL, either incorrect or missing argument(s) when executing script")
        
    



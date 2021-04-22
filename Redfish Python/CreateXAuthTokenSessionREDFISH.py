#
# CreateXAuthTokenSessionREDFISH. Python script using Redfish API to create X-AUTH token session for iDRAC user.
#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 4.0
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


import requests, json, sys, re, time, warnings, argparse

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to create, test or delete X-AUTH token session for iDRAC user.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password', required=False)
parser.add_argument('script_examples',action="store_true",help='CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will create X auth token session for iDRAC. CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -g y -t 403ddd3c32df6fcbfdfec758780d2274, this example will test GET request using X auth token. CreateXAuthTokenSessionREDFISH.py -ip 192.168.0.120 -d 28 -t 403ddd3c32df6fcbfdfec758780d2274, this example will delete X auth token session for session ID 28.') 
parser.add_argument('-c', help='Create X-auth token session, pass in \"y\". You must also use argument -u and -p', required=False)
parser.add_argument('-t', help='Test X-auth token session using GET request, get iDRAC session information or delete X-Auth token session, pass in the token ID', required=False)
parser.add_argument('-g', help='Test X-auth token session, pass in \"y\". You must also use argument -t to pass in the token session', required=False)
parser.add_argument('-su', help='Get iDRAC session information, pass in \"y\". You must also use argument -u and -p', required=False)
parser.add_argument('-st', help='Get X-auth token session information/ID, pass in \"y\". You must also use argument -t to pass in the token session', required=False)
parser.add_argument('-d', help='Delete X-auth-token session, pass in the session ID. You must also use -t argument to pass in the token session', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

def get_redfish_version():
    global session_uri
    response = requests.get('https://%s/redfish/v1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        try:
            response = requests.get('https://%s/redfish/v1' % (idrac_ip),verify=False, headers={'X-Auth-Token': args["t"]})
            if response.status_code == 401:
                print("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
                sys.exit()
            else:
                data = response.json()
        except:
            print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
            sys.exit(1)
    elif response.status_code != 200:
        print("\n- WARNING, GET request failed to get Redfish version, status code %s returned" % response.status_code)
        sys.exit(1)
    else:
        pass
    redfish_version = int(data["RedfishVersion"].replace(".",""))
    if redfish_version >= 160:
        session_uri = "redfish/v1/SessionService/Sessions"
    elif redfish_version < 160:
        session_uri = "redfish/v1/Sessions"
    else:
        print("- INFO, unable to select URI based off Redfish version")
        sys.exit()

def create_x_auth_session():
    url = 'https://%s/%s' % (idrac_ip, session_uri)
    payload = {"UserName":args["u"],"Password":args["p"]}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
    data = response.json()
    if response.status_code == 201:
        print("\n- PASS, successfuly created X auth session")
    else:
        try:
            print("\n- FAIL, unable to create X-auth_token session, status code %s returned, detailed error results:\n %s" % (response.status_code, data))
        except:
            print("\n- FAIL, unable to create X-auth_token session, status code %s returned" % (response.status_code))
        sys.exit()
    print("\n- INFO, created session details -\n")
    for i in response.headers.items():
        print("%s: %s" % (i[0],i[1]))
    

def test_x_auth_session_get():
    response = requests.get('https://%s/%s' % (idrac_ip, session_uri),verify=False, headers={'X-Auth-Token': args["t"]})
    if response.status_code == 401:
        print("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
        sys.exit()
    elif response.status_code == 200:
        print("\n- PASS, GET request using X-auth session passed")
    else:
        data=response.json()
        print("\n- FAIL, GET request using X-auth_token session failed, status code is %s, detailed error results:\n %s" % (response.status_code, data))
        sys.exit()

def get_session_info_using_username_password():
    response = requests.get('https://%s/%s' % (idrac_ip, session_uri), auth=(idrac_username, idrac_password), verify=False)
    if response.status_code == 401:
        print("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
        sys.exit()
    elif response.status_code == 200:
        pass
    else:
        data=response.json()
        print("- FAIL, GET request failed, status code %s returned. Detailed error results:\n %s" % (response.status_code, data))
        sys.exit()
    data= response.json()
    if data["Members"] == []:
        print("\n- WARNING, no sessions detected for iDRAC %s" % idrac_ip)
        sys.exit()
    else:
        sessions_list = []
        for i in data["Members"]:
            for ii in i.items():
                sessions_list.append(ii[1])
    print("\n- Sessions detected for iDRAC %s\n" % idrac_ip)
    for i in sessions_list:
        print(i)
    for i in sessions_list:
        print("\n- Detailed information for sessions URI \"%s\" -\n" % i)
        response = requests.get('https://%s%s' % (idrac_ip,i), auth=(idrac_username, idrac_password), verify=False)
        data=response.json()
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))    

def get_session_info_using_token():
    response = requests.get('https://%s/%s' % (idrac_ip, session_uri),verify=False, headers={'X-Auth-Token': args["t"]})
    if response.status_code == 401:
        print("\n- FAIL, GET request failed, status code %s returned, check login credentials" % (response.status_code))
        sys.exit()
    elif response.status_code == 200:
        pass
    else:
        data=response.json()
        print("\n- FAIL, GET request using X-auth_token session failed, status code is %s, detailed error results:\n %s" % (response.status_code, data))
        sys.exit()
    data=response.json()
    sessions_list = []
    for i in data["Members"]:
        for ii in i.items():
            sessions_list.append(ii[1])
    print("\n- Sessions detected for iDRAC %s\n" % idrac_ip)
    for i in sessions_list:
        print(i)
    for i in sessions_list:
        print("\n- Detailed information for sessions URI \"%s\" -\n" % i)
        response = requests.get('https://%s%s' % (idrac_ip,i), verify=False, headers={'X-Auth-Token': args["t"]})
        data=response.json()
        for i in data.items():
            print("%s: %s" % (i[0],i[1]))

def delete_x_auth_session():
    url = 'https://%s/%s/%s' % (idrac_ip, session_uri, args["d"])
    headers = {'content-type': 'application/json','X-Auth-Token': args["t"]}
    try:
        response = requests.delete(url, headers=headers, verify=False)
    except requests.ConnectionError as error_message:
        print("- FAIL, requests command failed to GET job status, detailed error information: \n%s" % error_message)
        sys.exit()
    if response.status_code == 200:
        print("\n- PASS, successfully deleted X auth session for session ID %s" % args["d"])
    else:
        data = response.json()
        print("\n- FAIL, unable to delete X-auth_token session, status code is %s, detailed error results:\n %s" % (response.status_code, data))
        sys.exit()





if __name__ == "__main__":
    get_redfish_version()
    if args["c"]:
        create_x_auth_session()
    elif args["g"] and args["t"]:
        test_x_auth_session_get()
    elif args["st"] and args["t"]:
        get_session_info_using_token()
    elif args["su"]:
        get_session_info_using_username_password()
    elif args["d"]:
        delete_x_auth_session()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")
        
        


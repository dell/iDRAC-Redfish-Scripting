import argparse, getpass, logging, os, re, requests, sys, warnings
from pprint import pprint as pp
warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to get system hardware inventory(output will be printed to the screen and also copied to a text file). This includes information for storage controllers, memory, network devices, general system details, power supplies, hard drives, fans, backplanes, processors")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value \"true\" or \"false\". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--memory', help='Get Memory Health Information', action="store_true", required=False)
parser.add_argument('--processor', help='Get Power Supply Health Information', action="store_true", required=False)
parser.add_argument('--fans', help='Get Fan Health Information', action="store_true", required=False)
parser.add_argument('--all', help='Get Health Information of whole server', action="store_true", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def script_examples():
    print("""\n- GetHealthInformation.py -ip 10.2.161.103 -u root -p calvin --memory, this example will get only memory health information.
                 GetHealthInformation.py -ip 10.2.161.103 -u root -p calvin --processor, this example will get cpu health information.
                 GetHealthInformation.py -ip 10.2.161.103 -u root -p calvin --all, this example will get information of all Dell Server. """)
    sys.exit(0)

def check_supported_idrac_version():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)

def get_memory_health_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        print("\n ----------------- MEMORY INFORMATION ----------------- ")
        
    for i in data['Members']:
        dimm = i['@odata.id'].split("/")[-1]
        try:
            dimm_slot = re.search("DIMM.+",dimm).group()
        except:
            logging.error("\n- FAIL, unable to get dimm slot info")
            sys.exit(0)
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            logging.error("\n- FAIL, get command failed, error: %s" % sub_data)
            sys.exit(0)
        else:
            print('\n%s' %dimm_slot)

            for ii in sub_data.items():
                if ii[0] == 'Status':
                    if ii[1]['Health'] == 'OK':
                        pp('Health : %s' % (ii[1]['Health']))
                    else:
                        pp('Health: %s' % (ii[1]['Health']))

def get_processor_health_information():
    if args["x"]:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    else:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip, verify=verify_cert, auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, get command failed, error: %s" % data)
        sys.exit(0)
    else:
        print("\n ----------------- CPU INFORMATION ----------------- ")
    for i in data['Members']:
        cpu = i['@odata.id'].split("/")[-1]
        if args["x"]:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
        else:
            response = requests.get('https://%s%s' % (idrac_ip, i['@odata.id']), verify=verify_cert, auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error: %s" % sub_data)
            sys.exit(0)
        else:
            print("\n%s" %cpu)
            for ii in sub_data.items():
                if ii[0] == 'Status':
                    if ii[1]['Health'] == 'OK':
                        pp('Health : %s' % (ii[1]['Health']))
                    else:
                        pp('Health: %s\n' % (ii[1]['Health']))

if __name__ == "__main__":
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
    try:
        os.remove("hw_inventory.txt")
    except:
        logging.debug("- INFO, file %s not detected, skipping step to delete file" % "hw_inventory.txt")
    open_file = open("hw_inventory.txt","a")
    if args["memory"]:
        get_memory_health_information()
    if args ["processor"]:
        get_processor_health_information()
    if args["all"]:
        get_memory_health_information()
        get_processor_health_information()

    open_file.close()

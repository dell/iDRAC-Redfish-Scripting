#
# SubmitTestEventREDFISH. Python script using Redfish API to either get event service properties, get event subscriptions, create / delete subscriptions or submit test event.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
#
# Copyright (c) 2018, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get event service properties, get event subscriptions, create / delete subscriptions or submit test event.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='SubmitTestEventREDFISH.py -ip 192.168.0.120 -u root -p calvin -s yy, this example will get current subscription URIs and details. SubmitTestEventREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y -D https://192.168.0.130 -E Alert -V MetricReport, this example will create a MetricReport subscription for alert events which will use 192.168.0.130 Redfish event listener. SubmitTestEventREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/EventService/Subscriptions/c1a71140-ba1d-11e9-842f-d094662a05e6, this example will delete a subscription')
parser.add_argument('-e', help='Get event service properties, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get event service subscriptions URIs, pass in \"y\". To get detailed information for each subscription URI, pass in \"yy\"', required=False)
parser.add_argument('-c', help='Create subscription, pass in \"y\". You must also use agruments -D, -V and -E to create a subscription', required=False)
parser.add_argument('-t', help='Submit test event, pass in \"y\". You must also use arguments -D, -E and -M to submit a test event', required=False)
parser.add_argument('-D', help='Pass in Destination HTTPS URI path for either create subscription or send test event', required=False)
parser.add_argument('-V', help='Pass in Event Format Type for creating a subscription. Supported values are \"Event\", \"MetricReport\" or \"None\"', required=False)
parser.add_argument('-E', help='Pass in EventType value for either create subscription or send test event. Supported values are StatusChange, ResourceUpdated, ResourceAdded, ResourceRemoved, Alert.', required=False)
parser.add_argument('-M', help='Pass in MessageID for sending test event. Example: TMP0118', required=False)
parser.add_argument('--delete', help='Pass in complete service subscription URI to delete. Execute -s argument if needed to get subscription URIs', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

if args["D"]:
    destination = args["D"]
if args["E"]:
    event_type = args["E"]
if args["M"]:
    message_id = args["M"]

def get_event_service_properties():
    response = requests.get('https://%s/redfish/v1/EventService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- WARNING, GET command output for EventService URI\n")
    for i in data.items():
        print "%s: %s" % (i[0], i[1])

def get_event_service_subscriptions():
    response = requests.get('https://%s/redfish/v1/EventService/Subscriptions' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data=response.json()
    if data["Members"] == []:
        print("\n- WARNING, no subscriptions detected for iDRAC %s" % idrac_ip)
        sys.exit()
    else:
        print("\n- WARNING, subscriptions detected for iDRAC ip %s\n" % idrac_ip)
    for i in data["Members"]:
        for ii in i.items():
            print ii[1]
    print("\n")
    for i in data["Members"]:
        for ii in i.items():
            if args["s"] == "yy":
                response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                data=response.json()
                print("\n- Detailed information for subscription %s\n" % ii[1])
                for iii in data.items():
                    print("%s: %s" % (iii[0], iii[1]))
            else:
                pass

def delete_subscriptions():
    url = "https://%s%s" % (idrac_ip, args["delete"])
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False,auth=(idrac_username,idrac_password))
    if response.__dict__["status_code"] == 200:
        print("\n- PASS, DELETE command passed to delete subscription %s" % args["delete"])
    else:
        print("\n- FAIL, DELETE command failed and returned status code %s, error is %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit()

def scp_set_idrac_attribute():
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    payload = {"ImportBuffer":"<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"IPMILan.1#AlertEnable\">Enabled</Attribute></Component></SystemConfiguration>","ShareParameters":{"Target":"All"}}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    d=str(response.__dict__)
    try:
        z=re.search("JID_.+?,",d).group()
    except:
        print("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit()

    job_id=re.sub("[,']","",z)
    if response.status_code != 202:
        print("\n- FAIL, status code not 202\n, code is: %s" % response.status_code)  
        sys.exit()
    else:
        print("- %s successfully created for ImportSystemConfiguration method\n" % (job_id))

    response_output=response.__dict__
    job_id=response_output["headers"]["Location"]
    job_id=re.search("JID_.+",job_id).group()

    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        message_string=data[u"Messages"]
        final_message_string=str(message_string)
        if statusCode == 202 or statusCode == 200:
            pass
            time.sleep(1)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in final_message_string or "completed with errors" in final_message_string or "Not one" in final_message_string:
            print("\n- FAIL, detailed job message is: %s" % data[u"Messages"])
            sys.exit()
        elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or "Successfully imported" in final_message_string:
            print("- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = \n"+message_string[0][u"Message"])
            except:
                print("- Message = %s\n" % message_string[len(message_string)-1][u"Message"])
            break
        elif "No changes" in final_message_string:
            print("- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- Message = %s" % message_string[len(message_string)-1][u"Message"])
                sys.exit()
            break
        else:
            print("- Job not marked completed, current status is: %s" % data[u"TaskState"])
            print("- Message: %s\n" % message_string[0][u"Message"])
            time.sleep(1)
            continue
    
def get_set_ipmi_alert_iDRAC_setting():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    while True:
        try:
            attributes_dict=data[u'Attributes']
        except:
            print("\n- WARNING, iDRAC version detected does not support PATCH to set iDRAC attributes, executing Server Configuration Profile feature set iDRAC attribute \"IPMILan.1#AlertEnable\" locally\n")
            scp_set_idrac_attribute()
            break

        print("- WARNING, checking current value for iDRAC attribute \"IPMILan.1.AlertEnable\"")

        if attributes_dict["IPMILan.1.AlertEnable"] == "Disabled":
            print("- WARNING, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" is set to Disabled, setting value to Enabled")
            payload = {"Attributes":{"IPMILan.1.AlertEnable":"Enabled"}}
            headers = {'content-type': 'application/json'}
            url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
            statusCode = response.status_code
            if statusCode == 200:
                print("- PASS, PATCH command passed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
            else:
                print("- FAIL, PATCH command failed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                sys.exit()
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            attributes_dict=data[u'Attributes']
            if attributes_dict["IPMILan.1.AlertEnable"] == "Enabled":
                print("- PASS, iDRAC attribute \"IPMILan.1.AlertEnable\" successfully set to Enabled")
                break
            else:
                print("- FAIL, iDRAC attribute \"IPMILan.1.AlertEnable\" not set to Enabled")
                sys.exit()
        else:
            print("- WARNING, current value for iDRAC attribute \"IPMILan.1.AlertEnable\" already set to Enabled, ignore PATCH command")
            break

def create_subscription():
    url = "https://%s/redfish/v1/EventService/Subscriptions" % idrac_ip
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__["status_code"] == 201:
        print("- PASS, POST command passed, status code 201 returned, subscription successfully set for EventService")
    else:
        print("- FAIL, POST command failed, status code %s returned, error is %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit()
    
def submit_test_event():
    payload = {"Destination": destination,"EventTypes": event_type,"Context": "Root","Protocol": "Redfish","MessageId":message_id}
    url = "https://%s/redfish/v1/EventService/Actions/EventService.SubmitTestEvent" % idrac_ip
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__["status_code"] == 201:
        print("\n- PASS, POST command passed, status code 201 returned, event type \"%s\" successfully sent to destination \"%s\"" % (event_type, destination))
    else:
        print("\n- FAIL, POST command failed, status code %s returned, error is %s" % (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit()
    

if __name__ == "__main__":
    if args["e"] == "y":
        get_event_service_properties()
    elif args["s"] == "y" or args["s"] == "yy":
        get_event_service_subscriptions()
    elif args["c"] =="y" and args["D"] != "" and args["E"] != "" and args["V"] != "":
        get_set_ipmi_alert_iDRAC_setting()
        create_subscription()
    elif args["t"] =="y" and args["D"] != "" and args["E"] != "" and args["M"] != "":
        submit_test_event()
    elif args["delete"] != "":
        delete_subscriptions()
        
        
        





               

#
# IdracRecurringJobOemREDFISH. Python script using Redfish API with OEM to create recurring job for iDRAC or storage operation.
#
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


import requests, json, sys, re, time, warnings, argparse

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM to create recurring job for iDRAC or storage operation. Once the recurring job has executed and marked completed and 10 minutes have elapsed, the next recurring job will get automatically created and scheduled.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -g y, this example will get supported actions for creating recurring jobs. IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -grj y, this example will get current recurring auto job IDs and associated job ID(s). IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -drj /redfish/v1/JobService/Jobs/Auto32d880d7, this example will delete auto recurring job ID. IdracRecurringJobOemREDFISH.py -ip 192.168.0.120 -u root -p calvin -C 1 -s 2020-02-14T14:48:00-06:00 -m 5 -edw Monday, this example will create recurring job rebooting the server for the next 5 Mondays at 14:48.')
parser.add_argument('-t', help='Get currnt iDRAC date / time, pass in \"y\" ', required=False)
parser.add_argument('-g', help='Get supported actions for recurring job creation, pass in \"y\" ', required=False)
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-grj', help='Get current recurring job(s), pass in \"y\"', required=False)
parser.add_argument('-drj', help='Delete recurring job, pass in recurring auto job ID URI. If needed, use argument -grj to get this URI information', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disks, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-C', help='Create recurring job, pass in action type. Pass in 1 for \"ComputerSystem.Reset\", 2 for \"Manager.Reset\", 3 for \"Volume.CheckConsistency\", 4 for \"LogService.ClearLog\". Note: Only other required argument needed to create recurring job is argument -s', required=False)
parser.add_argument('-V', help='Pass in the virtual disk FQDD if you are creating a recurring job for storage check consistency', required=False)
parser.add_argument('-s', help='Pass in the initial start time/date for the recurring job to execute. Format is in UTC time. Example: 2020-02-05T04:51:28-06:00.Note: If needed, use argument -t to get current iDRAC date/time which returns the value in UTC format.', required=False)
parser.add_argument('-m', help='Max occurrences, pass in an integer value, how many times you want this recurring job to be executed. Note: This argument is optional for create recurring job', required=False)
parser.add_argument('-edw', help='Enable days of the week you want the recurring job to execute. Supported values are: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday or Every. Every value means it will enable all days of the week. If you pass in multiple string values, make sure to use comma separator. Note: This argument is optional for recurring job', required=False)
parser.add_argument('-edm', help='Enable days of the month you want the recurring job to execute, pass in integer value 1 to 31. If you pass in multiple integer values, make sure to use comma separator. If you pass in a value of 0, this will enable all days of the month. Note: This argument is optional for recurring job', required=False)
parser.add_argument('-r', help='Recurrence interval, distance until the next occurrence job type executes. Pass in an integer value. Example: I want the next recurring job to execute 90 days apart, pass in a value of 90. Note: This argument is optional for recurring job', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/JobService/Jobs' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    if response.__dict__['reason'] == "Unauthorized":
        print("\n- FAIL, unauthorized to execute Redfish command. Check to make sure you are passing in correct iDRAC username/password and the IDRAC user has the correct privileges")
        sys.exit()
    else:
        pass
    data = response.json()
    if response.status_code == 200:
        pass
    else:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()

def get_idrac_time():
    url = 'https://%s/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime' % (idrac_ip)
    method = "ManageTime"
    headers = {'content-type': 'application/json'}
    payload={"GetRequest":True}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data=response.json()
    if response.status_code == 200:
        print("\n-PASS: POST command passed for %s action GET iDRAC time, status code 200 returned\n" % method)
    else:
        print("\n-FAIL, POST command failed for %s action, status code is %s" % (method, response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()
    for i in data.items():
        if i[0] =="@Message.ExtendedInfo":
            pass
        else:
            print("%s: %s" % (i[0], i[1]))

def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["v"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("- FAIL, GET command failed, error is: %s" % data)
        sys.exit()
    vd_list=[]
    if data['Members'] == []:
        print("\n- WARNING, no volumes detected for %s" % args["v"])
        sys.exit()
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    print("\n- Virtual disk(s) detected for controller %s -" % args["v"])
    print("\n")
    supported_vds=[]
    volume_type=[]
    for ii in vd_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "VolumeType":
                if i[1] != "RawDevice":
                    supported_vds.append(ii)
                    volume_type.append(i[1])
                else:
                    pass
    if supported_vds == []:
        print("- WARNING, no virtual disk(s) detected for controller %s" % args["v"])
    else:
        for i,ii in zip(supported_vds,volume_type):
            print("%s, Volume Type: %s" % (i, ii))
    sys.exit()

def get_recurring_jobs():
    response = requests.get('https://%s/redfish/v1/JobService/Jobs' % (idrac_ip),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    recurring_jobs_list = []
    for i in data["Members"]:
        for ii in i.items():
            if "Auto" in ii[1]:
                recurring_jobs_list.append(ii[1])
    if recurring_jobs_list == []:
        print("\n- WARNING, no recurring jobs detected")
    else:
        count = 0
        for i in recurring_jobs_list:
            print("\n- Recurring auto job URI \"%s\" -\n" % i)
            response = requests.get('https://%s%s/Steps' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            for i in data["Members"]:
                for ii in i.items():
                    print("\n- Associated schedule job ID URI \"%s\" details -\n" % ii[1])
                    response = requests.get('https://%s%s' % (idrac_ip, ii[1]),verify=False,auth=(idrac_username, idrac_password))
                    data = response.json()
                    for ii in data.items():
                        print("%s: %s" % (ii[0], ii[1]))
                
            

def get_recurring_job_types():
    print("\n- Supported actions for recurring job types -\n")
    job_types = {"ComputerSystem.Reset":"Perform server reboot", "Manager.Reset":"Perform iDRAC reboot", "Volume.CheckConsistency":"Check consistency on a RAID volume", "LogService.ClearLog":"Clear iDRAC system event logs"}
    for i in job_types.items():
        print("%s: %s" % (i[0],i[1]))

def delete_recurring_job():
    uri = "https://%s%s" % (idrac_ip, args["drj"])
    headers = {'content-type': 'application/json'}
    payload = {}
    response = requests.delete(uri, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS, recurring URI \"%s\" successfully deleted" % args["drj"])
    else:
        data = response.json()
        print("\n- FAIL, recurring URI not successfully deleted, status code %s returned, detailed error results: \n%s" % (statusCode, data))
        sys.exit()
    
        
def create_recurring_job():
    uri = "https://%s/redfish/v1/JobService/Jobs" % idrac_ip
    payload = {"Payload":{},"Schedule":{"InitialStartTime":args["s"]}}
    if args["C"] == "1":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    elif args["C"] == "2":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Manager.Reset"
    elif args["C"] == "3" and args["V"]:
        payload["Payload"]["TargetUri"] = "/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s/Actions/Volume.CheckConsistency" % (args["V"])
    elif args["C"] == "4":
        payload["Payload"]["TargetUri"] = "/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Actions/LogService.ClearLog"
    else:
        print("- FAIL, invalid value entered for -C argument")
        sys.exit()
    if args["m"]:
        payload["Schedule"]["MaxOccurrences"] = int(args["m"])
    if args["edw"]:
        if "," in args["edw"]:
            split_string = args["e"].split(",")
            payload["Schedule"]["EnabledDaysOfWeek"] = split_string
        else:
            payload["Schedule"]["EnabledDaysOfWeek"] = [args["edw"]]
    if args["edm"]:
        if "," in args["edm"]:
            split_string = args["edm"].split(",")
            create_int_list = []
            for i in split_string:
                create_int_list.append(int(i))
            payload["Schedule"]["EnabledDaysOfMonth"] = create_int_list
        else:
            payload["Schedule"]["EnabledDaysOfMonth"] = ([int(args["edm"])])
    if args["r"]:
        payload["Schedule"]["RecurrenceInterval"] = "P%sD" % args["r"]
    print("\n- Parameters and values being used for POST command to create recurring job -\n")
    for i in payload.items():
        print("%s: %s" % (i[0], i[1]))
    headers = {'content-type': 'application/json'}
    response = requests.post(uri, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
    statusCode = response.status_code
    
    if statusCode == 200 or statusCode == 202:
        print("\n- PASS, POST command passed to create recurring job for URI \"%s\", status code %s returned" % (payload["Payload"]["TargetUri"], statusCode))
    else:
        print("\n- FAIL, POST command failed, status code %s returned\n" % statusCode)
        print(response.json())
        sys.exit()

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["g"]:
        get_recurring_job_types()
    elif args["C"] and args["s"]:
        create_recurring_job()
    elif args["c"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["t"]:
        get_idrac_time()
    elif args["grj"]:
        get_recurring_jobs()
    elif args["drj"]:
        delete_recurring_job()
    else:
        print("- FAIL, incorrect parameter(s) passed in or missing required parameters")
        
        


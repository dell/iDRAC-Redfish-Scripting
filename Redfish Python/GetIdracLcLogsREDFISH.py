#
# GetIdracLcLogsREDFISH. Python script using Redfish API to get iDRAC LC logs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 3.0
#
# Copyright (c) 2017, Dell, Inc.
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

parser=argparse.ArgumentParser(description="Python script using Redfish API to get iDRAC Lifecycle Controller(LC) logs, either latest 50 entries, all entries or failed entries.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will get latest 50 entries only. GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this example will get complete iDRAC LC logs. GetIdracLcLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin -f y, this example will get only failed entries from LC logs.')
parser.add_argument('-c', help='Get all iDRAC LC logs, pass in \"y\"', required=False)
parser.add_argument('-f', help='Get only failed entries from LC logs (searches for keywords \"Unable\" and \"Fail\", pass in \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]



def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, GET request failed, error results:\n%s" % data)
        sys.exit()
    else:
        pass
        

def get_LC_logs():
    try:
        os.remove("lc_logs.txt")
    except:
        pass
    f=open("lc_logs.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
            print(lc_log_entry)
            f.writelines("%s\n" % lc_log_entry)
        print("\n")
        f.writelines("\n")

    if args["c"]:
        number_list=[i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            if "Members" in data:
                pass
            else:
                break
            for i in data['Members']:
                for ii in i.items():
                    lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                    print(lc_log_entry)
                    f.writelines("%s\n" % lc_log_entry)
                print("\n")
                f.writelines("\n")

    else:
        pass
    
    print("\n- INFO, Lifecycle logs also captured in \"lc_logs.txt\" file")
    f.close()

def get_LC_log_failures():
    count = 0
    try:
        os.remove("lc_log_failures.txt")
    except:
        pass
    print("\n- INFO, checking iDRAC LC logs for failed entries, this may take awhile to complete depending on log size -\n")
    time.sleep(2)
    f=open("lc_log_failures.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    
    for i in data['Members']:
        for ii in i.items():
            if ii[0] == "Message":
                if "unable" in ii[1] or "Unable" in ii[1] or "fail" in ii[1] or "Fail" in ii[1] or "Error" in ii[1] or "error" in ii[1]:
                    count+=1
                    for ii in i.items():
                        lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                        print(lc_log_entry)
                        f.writelines("%s\n" % lc_log_entry)
                    print("\n")
                    f.writelines("\n")

    
    number_list=[i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if "Members" in data:
            pass
        else:
            break
        for i in data['Members']:
            for ii in i.items():
                if ii[0] == "Message":
                    if "unable" in ii[1] or "Unable" in ii[1] or "fail" in ii[1] or "Fail" in ii[1] or "Error" in ii[1] or "error" in ii[1]:
                        count+=1
                        for ii in i.items():
                            lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                            print(lc_log_entry)
                            f.writelines("%s\n" % lc_log_entry)
                        print("\n")
                        f.writelines("\n")
    if count == 0:
        print("- INFO, no failed entries detected in LC logs")
        try:
            os.remove("lc_log_failures.txt")
        except:
            pass
        sys.exit()
    else:
        print("\n- INFO, Lifecycle logs also captured in \"lc_log_failures.txt\" file")
        f.close()



if __name__ == "__main__":
    check_supported_idrac_version()
    if args["f"]:
        get_LC_log_failures()
    else:
        get_LC_logs()



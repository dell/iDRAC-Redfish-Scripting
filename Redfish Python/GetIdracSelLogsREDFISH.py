#
# GetIdracSelLogsREDFISH. Python script using Redfish API to get iDRAC System Event Logs (SEL) logs.
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

import requests, json, sys, re, time, os, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to get iDRAC System Event Logs (SEL) logs, either last 50 entries or all entries. By default, it will get the last 50 entries if you don't use \"-c\" argument.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetIdracSelLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will get the latest 50 entries in iDRAC system event log. GetIdracSelLogsREDFISH.py -ip 192.168.0.120 -u root -p calvin, this example will get the complete iDRAC system event log.')
parser.add_argument('-c', help='Get all iDRAC system event logs, pass in \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("iDRAC_SEL_logs.txt")
except:
    pass

def get_SEL_logs():
    f=open("iDRAC_SEL_logs.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    if response.status_code == 401:
        print("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish.")
        sys.exit()
    data = response.json()
    for i in data['Members']:
        for ii in i.items():
            SEL_log_entry = ("%s: %s" % (ii[0],ii[1]))
            print(SEL_log_entry)
            f.writelines("%s\n" % SEL_log_entry)
        print("\n")
        f.writelines("\n")

    if args["c"]:
        number_list=[i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Sel/Entries?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            if "Members" in data:
                pass
            else:
                break
            for i in data['Members']:
                for ii in i.items():
                    SEL_log_entry = ("%s: %s" % (ii[0],ii[1]))
                    print(SEL_log_entry)
                    f.writelines("%s\n" % SEL_log_entry)
                print("\n")
                f.writelines("\n")

    else:
        pass
    
    print("\n- WARNING, system event logs also captured in \"iDRAC_SEL_logs.txt\" file")
    f.close()

#Run Code

if __name__ == "__main__":
    get_SEL_logs()



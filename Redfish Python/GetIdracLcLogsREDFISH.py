#
# GetIdracLcLogsREDFISH. Python script using Redfish API to get iDRAC LC logs.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

import requests, json, sys, re, time, os, warnings

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password")
    sys.exit()

try:
    os.remove("lc_logs.txt")
except:
    pass

# Function to get lifecycle logs (LC)

def get_LC_logs():
    f=open("lc_logs.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    for i in data[u'Members']:
        for ii in i:
            if ii == "@odata.type":
                new_line="\n"
                f.writelines(new_line)
                print(new_line)
                name_value="%s: %s" % (ii, i[ii])
                print(name_value)
                f.writelines(name_value)
            else:
                name_value="%s: %s" % (ii, i[ii])
                print(name_value)
                f.writelines(name_value)
                f.writelines(new_line)    
    print("\n- WARNING, Lifecycle logs also captured in \"lc_logs.txt\" file")
    f.close()

#Run Code

if __name__ == "__main__":
    get_LC_logs()



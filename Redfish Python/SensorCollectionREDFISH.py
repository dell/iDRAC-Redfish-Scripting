#
# AggregationMetricValueCollectionREDFISH. Python script using Redfish API OEM extensoion to get iDRAC sensor collection data.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API OEM extension to sensor collection data.")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-n', help='Get all Dell Numeric Sensor Collection data, pass in \"y\"', required=False)
parser.add_argument('-ps', help='Get all Dell PS(power supply) Numeric Sensor Collection data, pass in \"y\"', required=False)
parser.add_argument('-pss', help='Get all Dell Presence And Status Sensor Collection data, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get all Dell Sensor Collection data, pass in \"y\"', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("sensor_collection.txt")
except:
    pass

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellNumericSensorCollection' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_sensor_data():
    f=open("sensor_collection.txt","a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    if args["n"]:
        sensor_key = "DellNumericSensorCollection"
    elif args["ps"]:
        sensor_key = "DellPSNumericSensorCollection"
    elif args["pss"]:
        sensor_key = "DellPresenceAndStatusSensorCollection"
    elif args["s"]:
        sensor_key = "DellSensorCollection"
    else:
        print("- FAIL, you must pass in at least one parameter to get sensor collection data")
        sys.exit()
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/%s' % (idrac_ip, sensor_key),verify=False,auth=(idrac_username,idrac_password))
    print("\n- Data collection data for \"%s\"\n" % sensor_key) 
    data = response.json()
    if data[u'Members'] == []:
        print("- WARNING, no data available for URI \"redfish/v1/Dell/Systems/System.Embedded.1/%s\"" % sensor_key)
        sys.exit()
    else:
        pass
    for i in data[u'Members']:
        for ii in i.items():
            sensor_entry = ("%s: %s" % (ii[0],ii[1]))
            print(sensor_entry)
            f.writelines("%s\n" % sensor_entry)
        print("\n")
        f.writelines("\n")
    if u'Members@odata.nextLink' in data:
        number_list=[i for i in range (1,100001) if i % 50 == 0]
        for seq in number_list:
            response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/%s?$skip=%s' % (idrac_ip, sensor_key, seq) ,verify=False,auth=(idrac_username,idrac_password))
            data = response.json()
            if "Members" in data:
                pass
            else:
                break
            for i in data[u'Members']:
                for ii in i.items():
                    lc_log_entry = ("%s: %s" % (ii[0],ii[1]))
                    print(lc_log_entry)
                    f.writelines("%s\n" % lc_log_entry)
                print("\n")
                f.writelines("\n")   
    print("\n- WARNING, \"%s\" data also captured in \"sensor_collection.txt\" file" % sensor_key)
    f.close()


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["n"] or args["p"] or args["pss"] or args["s"]:
        get_sensor_data()
    else:
        print(" - WARNING, either incorrect parameter value passed in or missing required parameter")
    



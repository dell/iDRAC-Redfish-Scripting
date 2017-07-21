#
# GetPowerStateREDFISH. Python script using Redfish API to get current server power state.
#
# NOTE: Recommended to run this script first to get current server power state before executing SetPowerStateREDFISH script.
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

import requests, json, sys, re, time, warnings

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]

except:
    print("- FAIL: You must pass in script name along with iDRAC IP / iDRAC username / iDRAC password. Example: \"script_name.py 192.168.0.120 root calvin\"")
    sys.exit()



response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
data = response.json()
print("\n- WARNING, Current server power state is: %s\n" % data[u'PowerState'])

print("- Supported values for server power control:\n\n- On\n- ForceOff\n- GracefulRestart\n- GracefulShutdown")



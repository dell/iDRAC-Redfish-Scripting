#
# GetBiosBootOrderBootSourceStateREDFISH. Python script using Redfish API to get the current boot order and current boot source state for the boot devices.
#
# NOTE: Recommended to run this script first to get current boot order / boot source state before execute ChangeBootOrderBootSourceStateREDFISH script.
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

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
except:
    print("""- FAIL: You must pass in script name along with iDRAC IP/iDRAC username/iDRAC password
      Example: \"script_name.py 192.168.0.120 root calvin\"""")
    sys.exit()

### Function to get BIOS current boot mode

def get_bios_boot_mode():
    global current_boot_mode
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_boot_mode = data[u'Attributes']["BootMode"]
    print("\n- Current boot mode is %s" % current_boot_mode)
                    
### Function to get current boot devices and their boot source state

def get_bios_boot_source_state():
    global boot_seq
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    
    if current_boot_mode == "Uefi":
        boot_seq = "UefiBootSeq"
    else:
        boot_seq = "BootSeq"
    get_boot_devices=data[u'Attributes'][boot_seq]
    with open('boot_devices.txt', 'w') as i:
        json.dump(get_boot_devices, i)
    
    print("- Current boot order devices and their boot source state:\n")
    
    for i in get_boot_devices:
        for ii in i:
            print("%s : %s" % (ii, i[ii]))
            if ii == "Name":
                print("\n")

    print("""\n- Boot source devices are also copied to \"boot_devices.txt\" file. If executing script to
enable / disable multiple boot sources, this file will be used.""")

       

### Run code

if __name__ == "__main__":
    get_bios_boot_mode()
    get_bios_boot_source_state()




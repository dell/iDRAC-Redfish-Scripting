#
# AssignHotSpareREDFISH. Python script using Redfish API to either assign dedicated or global hot spare
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2
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


import requests
import json
import sys
import time
import warnings
import argparse

from datetime import datetime

warnings.filterwarnings("ignore")

try:
    input = raw_input
except NameError:
    pass


class AssignHotSpare(object):
    def __init__(self, ip, iuser, ipass, verify_certs, controller):
        if __name__ == '__main__':
            self.whoAmI = True
        else:
            self.whoAmI = False
        self.ip = ip
        self.url = 'https://{0}/redfish/v1/'.format(self.ip)
        self.ipass = ipass
        self.iuser = iuser
        self.controller = controller
        self.verCert = verify_certs
        self.job_id = None

    def check_supported_idrac_version(self):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        try:
            response = requests.get(url + 'Dell/Systems/System.Embedded.1/DellRaidService', verify=self.verCert,
                                    auth=(usr, pw))
        except requests.exceptions.ConnectionError as e:
            print("Could not establish connection to host. Error: \n{}".format(e))
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        if response.status_code == 401:
            print("Incorrect iDRAC credentials.")
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        if response.status_code != 200:
            print("- WARNING, Non-iDRAC, server error, or version installed does not support this feature using "
                  "Redfish API. Code: {}".format(response.status_code))
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        else:
            json_dict = json.loads(response.text)
            #print('Dell Raid Service version found: {}\n'.format(json_dict.get(u'@odata.type')))
            return True

    def get_storage_controllers(self, c):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        response = requests.get(url + 'Systems/System.Embedded.1/Storage', verify=self.verCert, auth=(usr, pw))
        if response.status_code != 200:
            print("Storage controller query failed with code {0}".format(response.status_code))
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        data = response.json()
        print("\n- Server controller(s) detected -\n")
        controller_list = []
        for i in data[u'Members']:
            for ii in i.items():
                controller = ii[1].split("/")[-1]
                controller_list.append(controller)
                print(controller)
        if c == "yy":
            for i in controller_list:
                response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s' % i, verify=self.verCert,
                                        auth=(usr, pw))
                data = response.json()
                print("\n - Detailed controller information for %s -\n" % i)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
        if self.whoAmI:
            sys.exit()
        else:
            return True

    def get_pdisks(self, detailed, controller):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        disk_used_created_vds = []
        available_disks = []
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s' % controller, verify=self.verCert,
                                auth=(usr, pw))
        if response.status_code != 200:
            print("\n- FAIL, GET command failed. Check to make sure you passed in correct controller FQDD")
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        data = response.json()
        drive_list = []
        if not data[u'Drives']:
            print("- WARNING, no drives detected for %s" % controller)
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        else:
            print("- Drive(s) detected for %s -\n" % controller)
            for i in data[u'Drives']:
                for ii in i.items():
                    disk = ii[1].split("/")[-1]
                    drive_list.append(disk)
                    print(disk)
        if detailed:
            for i in drive_list:
                response = requests.get(url + 'Systems/System.Embedded.1/Storage/Drives/%s' % i,
                                        verify=self.verCert, auth=(usr, pw))
                data = response.json()
                print("\n - Detailed drive information for %s -" % i)
                for ii in data.items():
                    print("%s: %s" % (ii[0], ii[1]))
                    if ii[0] == "Links":
                        print("")
                        if ii[1]["Volumes"]:
                            disk_used_created_vds.append(i)
                        else:
                            available_disks.append(i)
        if self.whoAmI:
            sys.exit()
        else:
            return True

    def get_pdisks_hot_spare_type(self, controller):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        self.test_valid_controller_FQDD_string(controller)
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s' % controller, verify=self.verCert,
                                auth=(usr, pw))
        data = response.json()
        drive_list = []
        if not data[u'Drives']:
            print("\n- WARNING, no drives detected for %s" % controller)
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        else:
            for i in data[u'Drives']:
                for ii in i.items():
                    disk = ii[1].split("/")[-1]
                    drive_list.append(disk)
        print("\n- Drive FQDDs/Hot Spare Type for Controller %s -\n" % controller)
        for i in drive_list:
            response = requests.get(url + 'Systems/System.Embedded.1/Storage/Drives/%s' % i, verify=self.verCert,
                                    auth=(usr, pw))
            data = response.json()
            for ii in data.items():
                if ii[0] == "HotspareType":
                    print("%s: Hot Spare Type: %s" % (i, ii[1]))
        if self.whoAmI:
            sys.exit()
        else:
            return True

    def get_virtual_disks(self, controller):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        self.test_valid_controller_FQDD_string(controller)
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s/Volumes' % controller,
                                verify=self.verCert, auth=(usr, pw))
        data = response.json()
        vd_list = []
        if not data[u'Members']:
            print("\n- WARNING, no volume(s) detected for %s" % controller)
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        else:
            for i in data[u'Members']:
                for ii in i.items():
                    vd = ii[1].split("/")[-1]
                    vd_list.append(vd)
        print("- Volume(s) detected for %s controller -" % controller)
        for ii in vd_list:
            response = requests.get(url + 'Systems/System.Embedded.1/Storage/Volumes/%s' % ii, verify=self.verCert,
                                    auth=(usr, pw))
            data = response.json()
            for i in data.items():
                if i[0] == "VolumeType":
                    print("%s, Volume type: %s" % (ii, i[1]))
        if self.whoAmI:
            sys.exit()
        else:
            return True

    def get_virtual_disk_details(self, controller):
        usr = self.iuser
        pw = self.ipass
        url = self.url
        self.test_valid_controller_FQDD_string(controller)
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s/Volumes' % controller, verify=self.verCert,
                                auth=(usr, pw))
        data = response.json()
        vd_list = []
        if not data[u'Members']:
            print("\n- WARNING, no volume(s) detected for %s" % controller)
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        else:
            print("\n- Volume(s) detected for %s controller -" % controller)
            for i in data[u'Members']:
                for ii in i.items():
                    vd = ii[1].split("/")[-1]
                    vd_list.append(vd)
                    print(vd)
        for ii in vd_list:
            response = requests.get(url + 'Systems/System.Embedded.1/Storage/Volumes/%s' % ii, verify=self.verCert,
                                    auth=(usr, pw))
            data = response.json()
            print("\n - Detailed Volume information for %s -" % ii)
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
        if self.whoAmI:
            sys.exit()
        else:
            return True

    def assign_spare(self, disk_fqdd, hot_spare_type, virtual_disk_fqdd):
        usr = self.iuser
        pw = self.ipass
        method = "AssignSpare"
        url = self.url + 'Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.AssignSpare'
        headers = {'content-type': 'application/json'}
        if hot_spare_type and hot_spare_type.lower() == "global" and virtual_disk_fqdd == "global":
            payload = {"TargetFQDD": disk_fqdd}
        elif hot_spare_type and hot_spare_type.lower() == "dedicated":
            try:
                payload = {"TargetFQDD": disk_fqdd, "VirtualDiskArray": [virtual_disk_fqdd]}
            except:
                print("\n- FAIL, missing argument -V for passing in virtual disk FQDD. This is required for assigning dedicated hotspare")
                sys.exit()
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=self.verCert, auth=(usr, pw))
        if response.status_code == 202:
            print('\n-PASS: POST command passed to set disk "%s" as "%s" hot spare' % (disk_fqdd, hot_spare_type))
            try:
                self.job_id = response.headers['Location'].split("/")[-1]
            except:
                print("- FAIL, unable to locate job ID in JSON headers output: {}".format(json.dumps(response.json())))
                if self.whoAmI:
                    sys.exit(1)
                else:
                    return False
            print('- Job ID %s successfully created for storage method "%s"' % (self.job_id, method))
            return True
        else:
            print("\n-FAIL, POST command failed to set disk %s as %s hot spare" % (disk_fqdd, hot_spare_type))
            data = json.dumps(response.json())
            print("\n-POST command failure results:\n %s" % data)
            if self.whoAmI:
                sys.exit(1)
            else:
                return False

    def loop_job_status(self):
        start_time = datetime.now()
        url = self.url
        usr = self.iuser
        pw = self.ipass
        while True:
            req = requests.get(url + 'Managers/iDRAC.Embedded.1/Jobs/%s' % self.job_id, auth=(usr, pw),
                               verify=self.verCert)
            current_time = (datetime.now()-start_time)
            statuscode = req.status_code
            if statuscode == 200:
                pass
            else:
                print("\n- FAIL, Command failed to check job status, return code is %s" % statuscode)
                print("Extended Info Message: {0}".format(req.json()))
                if self.whoAmI:
                    sys.exit(1)
                else:
                    return False
            data = req.json()
            if str(current_time)[0:7] >= "2:00:00":
                print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
                if self.whoAmI:
                    sys.exit(1)
                else:
                    return False
            elif "Fail" in data[u'Message'] or "fail" in data[u'Message'] or data[u'JobState'] == "Failed":
                print("- FAIL: job ID %s failed, failed message is: %s" % (self.job_id, data[u'Message']))
                if self.whoAmI:
                    sys.exit(1)
                else:
                    return False
            elif data[u'JobState'] == "Completed":
                print("\n--- PASS, Final Detailed Job Status Results ---\n")
                for i in data.items():
                    if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                        pass
                    else:
                        print("%s: %s" % (i[0], i[1]))
                break
            else:
                print('"- WARNING, JobStatus not completed, current status: "%s", percent complete: "%s"' %
                      (data[u'Message'], data[u'PercentComplete']))
                time.sleep(3)

    def test_valid_controller_FQDD_string(self, x):
        url = self.url
        usr = self.iuser
        pw = self.ipass
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/%s' % x, verify=self.verCert, auth=(usr, pw))
        if response.status_code != 200:
            print("\n- FAIL, either controller FQDD does not exist or typo in FQDD string name (FQDD controller string "
                  "value is case sensitive)")
            if self.whoAmI:
                sys.exit(1)
            else:
                return False
        return True

    def get_pdisk_hot_spare_final_status(self, disk_fqdd, hot_spare_type):
        url = self.url
        usr = self.iuser
        pw = self.ipass
        response = requests.get(url + 'Systems/System.Embedded.1/Storage/Drives/%s' % disk_fqdd,
                                verify=self.verCert, auth=(usr, pw))
        data = response.json()
        for i in data.items():
            if i[0] == "HotspareType":
                if i[1] == hot_spare_type.title():
                    print('- PASS, disk "%s" successfully set to "%s" hotspare' % (disk_fqdd, i[1]))
                    if self.whoAmI:
                        sys.exit()
                    else:
                        return True
                else:
                    print('- FAIL, disk "%s" not set to "%s" hotspare, current hot spare status is %s' %
                          (disk_fqdd, hot_spare_type, i[1]))
                    if self.whoAmI:
                        sys.exit(1)
                    else:
                        return False


def main():

    parser = argparse.ArgumentParser(
        description="Python script using Redfish API with OEM extension to assign either dedicated or global hot spare")
    parser.add_argument('-ip', help='iDRAC IP address - If not specified, user will be prompted for this')
    parser.add_argument('-u', help='iDRAC username - If not specified, user will be prompted for this')
    parser.add_argument('-p', help='iDRAC password - If not specified, user will be prompted for this')
    parser.add_argument('script_examples', action="store_true",
                        help='AssignHotSpareREDFISH.py -ip 192.168.0.120 -u root -p calvin -H RAID.Mezzanine.1-1, this'
                             ' example will get disks and their hotspare status for controller RAID.Mezzanine.1-1. '
                             'AssignHotSpareREDFISH.py -ip 192.168.0.120 -u root -p calvin -k -t global -a Disk.Bay.5:Encl'
                             'osure.Internal.0-1:RAID.Mezzanine.1-1, this example will skip cert check and assign disk 5 as a global '
                             'hotspare')
    parser.add_argument('-k', help='Skip certificate verification. This is an insecure practice, use wisely.',
                        action='store_true', required=False)
    parser.add_argument('-c', help='Get server storage controller FQDDs, pass in "y"', required=False)
    parser.add_argument('-d',
                        help='Get server storage controller disk FQDDs only, pass in storage controller FQDD, Example '
                             '"RAID.Integrated.1-1"',
                        required=False)
    parser.add_argument('-H',
                        help='Get current hot spare type for each drive, pass in storage controller FQDD, Example '
                             '"RAID.Integrated.1-1"',
                        required=False)
    parser.add_argument('-dd',
                        help='Get server storage controller disks detailed information, pass in storage controller '
                             'FQDD, Example "RAID.Integrated.1-1"',
                        required=False)
    parser.add_argument('-v',
                        help='Get current server storage controller virtual disk(s) and virtual disk type, pass in '
                             'storage controller FQDD, Example "RAID.Integrated.1-1"',
                        required=False)
    parser.add_argument('-vv',
                        help='Get current server storage controller virtual disk detailed information, pass in storage '
                             'controller FQDD, Example "RAID.Integrated.1-1"',
                        required=False)
    parser.add_argument('-t',
                        help='Pass in the type of hot spare you want to assign. Supported values are "dedicated" and '
                             '"global". Requires -a and -V',
                        required=False)
    parser.add_argument('-a',
                        help='Assign global or dedicated hot spare, pass in disk FQDD, Example "Disk.Bay.0:Enclosure.'
                             'Internal.0-1:RAID.Slot.6-1". Note: You must use -V with -a if you want to assign '
                             'dedicated hot spare',
                        required=False)
    parser.add_argument('-V',
                        help='Pass in virtual disk FQDD you want to assign the dedicated hot spare disk.Note: -a is '
                             'required along with -V for assign DHS',
                        required=False)

    args = parser.parse_args()
    controller = None
    ver_certs = True
    if args.k:
        ver_certs = False
    if not args.ip:
        args.ip = input("Please enter an iDRAC IP/DNS name: ")
    if not args.u:
        args.u = input("Please enter your username: ")
    if not args.p:
        args.p = input("Please enter your password: ")
    if args.d:
        controller = args.d
    elif args.dd:
        controller = args.dd
    elif args.H:
        controller = args.H
    elif args.v:
        controller = args.v
    elif args.vv:
        controller = args.vv
    hotspare = AssignHotSpare(args.ip, args.u, args.p, ver_certs, controller)
    try:
        hotspare.check_supported_idrac_version()
    except requests.exceptions.SSLError:
        print("Error, certificate validation failed! This can mean that someone is trying to MitM your connection, or"
              " this host is using an unsigned/expired/invalid cert. If the latter cases are known, please use the -k "
              "flag")
        sys.exit(1)
    if args.c:
        hotspare.get_storage_controllers(args.c)
    elif args.d or args.dd:
        if args.dd:
            hotspare.get_pdisks(True, controller)
        else:
            hotspare.get_pdisks(False, controller)
    elif args.H:
        hotspare.get_pdisks_hot_spare_type(controller)
    elif args.v:
        hotspare.get_virtual_disks(controller)
    elif args.vv:
        hotspare.get_virtual_disk_details(controller)
    elif args.a and args.t and args.V:
        hotspare.assign_spare(args.a, args.t, args.V)
        hotspare.loop_job_status()
        hotspare.get_pdisk_hot_spare_final_status(args.a, args.t)
    elif args.a and args.t:
        hotspare.assign_spare(args.a, args.t, "global")
        hotspare.loop_job_status()
        hotspare.get_pdisk_hot_spare_final_status(args.a, args.t)
    else:
        print("\n- FAIL, either incorrect argument(s) passed in or argument(s) missing. Check help text(-h) if needed")


if __name__ == "__main__":
    main()

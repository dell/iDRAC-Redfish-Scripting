#
# GetIdracServerSlotInformationREDFISH. Python script using Redfish API with OEM extension to get iDRAC server slot information.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 2.0
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

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to get server slot information. Slot information includes: Fan, CPU, DIMM, PCI, Backplane, PSU")
parser.add_argument('script_examples',action="store_true",help='GetIdracServerSlotInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -s y, this example will get slot information for all server devices and also redirect output to a file. GetIdracServerSlotInformationREDFISH.py -ip 192.168.0.120 -u root -p calvin -x y, this example will convert output to XMl format, redirect to XML file.')
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-s', help='Get all server slot information, pass in \"y\". This option will print information to the screen and also capture output in text file.', required=False)
parser.add_argument('-x', help='Get all server slot information, pass in \"y\". This option will redirect slot information into XML format.', required=False)
args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]



def get_server_slot_info():
    try:
        os.remove(idrac_ip+"_server_slot_info.txt")
    except:
        pass
    f=open("%s_server_slot_info.txt" % idrac_ip,"a")
    d=datetime.now()
    current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
    f.writelines(current_date_time)
    f.writelines("\n\n")
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, GET request failed, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))
        sys.exit()
    for i in data[u'Members']:
        for ii in i.items():
            server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
            print(server_slot_entry)
            f.writelines("%s\n" % server_slot_entry)
        print("\n")
        f.writelines("\n")
    number_list=[i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200 or response.status_code == 202:
            pass
        else:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                f.close()
                print("\n- WARNING, iDRAC Server Slot Information also captured in \"%s_server_slot_info.txt\" file" % idrac_ip)
                sys.exit()
            else:
                print("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                sys.exit()
        if "Members" in data:
            pass
        else:
            break
        for i in data[u'Members']:
            for ii in i.items():
                server_slot_entry = ("%s: %s" % (ii[0],ii[1]))
                print(server_slot_entry)
                f.writelines("%s\n" % server_slot_entry)
            print("\n")
            f.writelines("\n")
    print("\n- WARNING, iDRAC Server Slot Information also captured in \"%s_server_slot_info.txt\" file" % idrac_ip)
    f.close()

def get_server_slot_info_xml():
    print("\n- WARNING, collecting server slot information and converting to XML format, copy to XML file")
    try:
        os.remove(idrac_ip+"_server_slot_info.xml")
    except:
        pass
    f=open("%s_server_slot_info.xml" % idrac_ip,"a")
    f.writelines("<CIM>\n")
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection' % idrac_ip,verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, GET request failed, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))
        sys.exit()
    
    for i in data[u'Members']:
        create_dict = {}
        for ii in i.items():
            if ii[0] == "Id":
                create_dict[ii[0]] = str(ii[1])
            elif ii[0] == "EmptySlot":
                create_dict[ii[0]] = str(ii[1])
            elif ii[0] == "NumberDescription":
                if ii[1] == "":
                    create_dict["Slot Number"] = "NA"
                else:
                    create_dict["Slot Number"] = str(ii[1])
        create_string = "<VALUE.NAMEDINSTANCE>\n<INSTANCENAME DEVICENAME=\""+create_dict["Id"]+"\">\n<KEYBINDING PROPERTY=\"Slot Number\">\n<VALUE>"+create_dict["Slot Number"]+"</VALUE>\n</KEYBINDING>\n</INSTANCENAME>\n<PROPERTY PROPERTY=\"EmptySlot\">\n<VALUE>"+create_dict["EmptySlot"]+"</VALUE>\n</PROPERTY>\n</VALUE.NAMEDINSTANCE>"  
        f.writelines(create_string)
    number_list=[i for i in range (1,100001) if i % 50 == 0]
    for seq in number_list:
        response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection?$skip=%s' % (idrac_ip, seq) ,verify=False,auth=(idrac_username,idrac_password))
        data = response.json()
        if response.status_code == 200 or response.status_code == 202:
            pass
        else:
            if "query parameter $skip is out of range" in data["error"]["@Message.ExtendedInfo"][0]["Message"]:
                f.writelines("\n</CIM>")
                f.close()
                print("\n- PASS, iDRAC Server Slot Information captured in \"%s_server_slot_info.xml\" file" % idrac_ip)
                sys.exit()
            else:
                print("\n- FAIL, GET request failed using skip query parameter, status code %s returned. Detailed error results: \n%s" % (response.status_code,data))    
                sys.exit()
        if "Members" in data:
            pass
        else:
            break
        for i in data[u'Members']:
            create_dict = {}
            for ii in i.items():
                if ii[0] == "Id":
                    create_dict[ii[0]] = str(ii[1])
                elif ii[0] == "EmptySlot":
                    create_dict[ii[0]] = str(ii[1])
                elif ii[0] == "NumberDescription":
                    create_dict["Slot Number"] = str(ii[1])
            create_string = "<VALUE.NAMEDINSTANCE>\n<INSTANCENAME DEVICENAME=\""+create_dict["Id"]+"\">\n<KEYBINDING PROPERTY=\"Slot Number\">\n<VALUE>"+create_dict["Slot Number"]+"</VALUE>\n</KEYBINDING>\n</INSTANCENAME>\n<PROPERTY PROPERTY=\"EmptySlot\">\n<VALUE>"+create_dict["EmptySlot"]+"</VALUE>\n</PROPERTY>\n</VALUE.NAMEDINSTANCE>"  
            f.writelines(create_string)
    print("\n- PASS, iDRAC Server Slot Information captured in \"%s_server_slot_info.xml\" file" % idrac_ip)
    f.writelines("\n</CIM>")
    f.close()
    

#Run Code

if __name__ == "__main__":
    if args["s"]:
        get_server_slot_info()
    if args["x"]:
        get_server_slot_info_xml()
    else:
        print("\n- FAIL, either missing parameter(s) or invalid paramter value(s) passed in. Refer to help text if needed for supported parameters and values along with script examples")



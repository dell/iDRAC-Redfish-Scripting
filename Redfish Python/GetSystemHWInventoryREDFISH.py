#
# GetSystemHWInventoryREDFISH. Python script using Redfish API to get system hardware inventory
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


import requests, json, sys, re, time, warnings, argparse, os

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to get system hardware inventory(output will be printed to the screen and also copied to a text file). This includes information for storage controllers, memory, network devices, general system details, power supplies, hard drives, fans, backplanes, processors")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('-x', help='Get script examples, pass in \"y\"', required=False)
parser.add_argument('-s', help='Get system information only, pass in \"y\"', required=False)
parser.add_argument('-m', help='Get memory information only, pass in \"y\"', required=False)
parser.add_argument('-c', help='Get processor information only, pass in \"y\"', required=False)
parser.add_argument('-f', help='Get fan information only, pass in \"y\"', required=False)
parser.add_argument('-ps', help='Get power supply information only, pass in \"y\"', required=False)
parser.add_argument('-S', help='Get storage information only, pass in \"y\"', required=False)
parser.add_argument('-n', help='Get network device information only, pass in \"y\"', required=False)
parser.add_argument('-a', help='Get all system information / device information, pass in \"y\"', required=False)



args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

try:
    os.remove("hw_inventory.txt")
except:
    pass



f=open("hw_inventory.txt","a")
d=datetime.now()
current_date_time="- Data collection timestamp: %s-%s-%s  %s:%s:%s\n" % (d.month,d.day,d.year, d.hour,d.minute,d.second)
f.writelines(current_date_time)
f.close()

def script_examples():
    print("\n- Script Examples -\n")
    print("\n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -m y, this example will get only memory information\n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y -m y, this example will get only processor and memory information\n- GetSystemHWInventoryREDFISH.py -ip 192.168.0.120 -u root -p calvin -a y, this example will get all system information(general system information, processor, memory, fans, power supplies, hard drives, storage controllers, network devices)")
    
    
    

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_system_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        message = "\n---- System Information ----\n"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    for i in data.items():
        if i[0] == u'@odata.id' or i[0] == u'@odata.context' or i[0] == u'Links' or i[0] == u'Actions' or i[0] == u'@odata.type' or i[0] == u'Description' or i[0] == u'EthernetInterfaces' or i[0] == u'Storage' or i[0] == u'Processors' or i[0] == u'Memory' or i[0] == u'SecureBoot' or i[0] == u'NetworkInterfaces' or i[0] == u'Bios' or i[0] == u'SimpleStorage' or i[0] == u'PCIeDevices' or i[0] == u'PCIeFunctions':
            pass
        elif i[0] == u'Oem':
            for ii in i[1][u'Dell'][u'DellSystem'].items():
                if ii[0] == u'@odata.context' or ii[0] == u'@odata.type':
                    pass
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    f.writelines(message)
                    f.writelines("\n")
                    print(message)
                
                
        elif i[0] == u'Boot':
            try:
                message = "BiosBootMode: %s" % i[1][u'BootSourceOverrideMode']
                f.writelines(message)
                f.writelines("\n")
                print(message)
            except:
                pass
        else:
            message = "%s: %s" % (i[0], i[1])
            f.writelines(message)
            f.writelines("\n")
            print(message)
    f.close()
    

def get_memory_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Memory' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        message = "\n---- Memory Information ----"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    for i in data[u'Members']:
        dimm = i[u'@odata.id'].split("/")[-1]
        try:
            dimm_slot = re.search("DIMM.+",dimm).group()
        except:
            print("\n- FAIL, unable to get dimm slot info")
            sys.exit()
        response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),verify=False,auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error is: %s" % sub_data)
            sys.exit()
        else:
            message = "\n- Memory details for %s -\n" % dimm_slot
            f.writelines(message)
            f.writelines("\n")
            print(message)
            for ii in sub_data.items():
                if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links':
                    pass
                elif ii[0] == u'Oem':
                    for iii in ii[1][u'Dell'][u'DellMemory'].items():
                        if iii[0] == u'@odata.context' or iii[0] == u'@odata.type':
                            pass
                        else:
                            message = "%s: %s" % (iii[0], iii[1])
                            f.writelines(message)
                            f.writelines("\n")
                            print(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    f.writelines(message)
                    f.writelines("\n")
                    print(message)
    f.close()
    

def get_cpu_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Processors' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        message = "\n---- Processor Information ----"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    for i in data[u'Members']:
        cpu = i[u'@odata.id'].split("/")[-1]
        response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),verify=False,auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error is: %s" % sub_data)
            sys.exit()
        else:
            message = "\n- Processor details for %s -\n" % cpu
            f.writelines(message)
            f.writelines("\n")
            print(message)
            for ii in sub_data.items():
                if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == u'Description' or ii[0] == u'@odata.type':
                    pass
                elif ii[0] == u'Oem':
                    for iii in ii[1][u'Dell'][u'DellProcessor'].items():
                        if iii[0] == u'@odata.context' or iii[0] == u'@odata.type':
                            pass
                        else:
                            message = "%s: %s" % (iii[0], iii[1])
                            f.writelines(message)
                            f.writelines("\n")
                            print(message)
                else:
                    message = "%s: %s" % (ii[0], ii[1])
                    f.writelines(message)
                    f.writelines("\n")
                    print(message)
    f.close()
    

def get_fan_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        message = "\n---- Fan Information ----"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    if data[u'Links'][u'CooledBy'] == []:
        print("- WARNING, no fans detected for system")
        
    else:
        for i in data[u'Links'][u'CooledBy']:
            response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                print("\n- FAIL, get command failed, error is: %s" % data)
                sys.exit()
            else:
                fan = i[u'@odata.id'].split("/")[-1]
                try:
                    fan_slot = re.search("\|\|.+",fan).group().strip("|")
                except:
                    pass
                try:
                    fan_slot = re.search("7CF.+",fan).group().strip("7C")
                except:
                    pass
                message = "\n- Fan details for %s -\n" % fan_slot
                f.writelines(message)
                f.writelines("\n")
                print(message)
                for ii in data.items():
                    if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == u'Description' or ii[0] == u'@odata.type':
                        pass
                    else:
                        message = "%s: %s" % (ii[0], ii[1])
                        f.writelines(message)
                        f.writelines("\n")
                        print(message)
    f.close()

def get_ps_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    else:
        message = "\n---- Power Supply Information ----"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    if data[u'Links'][u'PoweredBy'] == []:
        print("- WARNING, no power supplies detected for system")
        
    else:
        for i in data[u'Links'][u'PoweredBy']:
            response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                print("\n- FAIL, get command failed, error is: %s" % data)
                sys.exit()
            else:
                ps = i[u'@odata.id'].split("/")[-1]
                message = "\n- Power Suppy details for %s -\n" % ps
                f.writelines(message)
                f.writelines("\n")
                print(message)
                for ii in data.items():
                    if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == u'Description' or ii[0] == u'@odata.type' or ii[0] == u'RelatedItem':
                        pass
                    elif ii[0] == u'Oem':
                        for iii in ii[1][u'Dell'][u'DellPowerSupply'].items():
                            if iii[0] == u'@odata.context' or iii[0] == u'@odata.type':
                                pass
                            else:
                                message = "%s: %s" % (iii[0], iii[1])
                                f.writelines(message)
                                f.writelines("\n")
                                print(message)
                        for iii in ii[1][u'Dell'][u'DellPowerSupplyView'].items():
                            if iii[0] == u'@odata.context' or iii[0] == u'@odata.type':
                                pass
                            else:
                                message = "%s: %s" % (iii[0], iii[1])
                                f.writelines(message)
                                f.writelines("\n")
                                print(message)
                    else:
                        message = "%s: %s" % (ii[0], ii[1])
                        f.writelines(message)
                        f.writelines("\n")
                        print(message)
    f.close()

def get_storage_controller_information():
    f=open("hw_inventory.txt","a")
    global controller_list
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    message = "\n---- Storage Controller Information ----"
    f.writelines(message)
    f.writelines("\n")
    print(message)
    controller_list=[]
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
    for i in controller_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error is: %s" % data)
            sys.exit()
        message = "\n- Controller details for %s -\n" % i
        f.writelines(message)
        f.writelines("\n")
        print(message)
        if u'StorageControllers' not in data:
            message = "- WARNING, no information for controller"
            f.writelines(message)
            f.writelines("\n")
            print(message)
            return
        for ii in data.items():
            if ii[0] == u'StorageControllers':
                for iii in ii[1][0].items():
                    if iii[0] == u'@odata.id' or iii[0] == u'Links':
                        pass
                    else:
                        message = "%s: %s" % (iii[0], iii[1])
                        f.writelines(message)
                        f.writelines("\n")
                        print(message)
    f.close()

     

def get_storage_disks_information():
    f=open("hw_inventory.txt","a")
    for i in controller_list:
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error is: %s" % data)
            sys.exit()
        message = "\n---- Drive Information For Controller %s ----" % i
        f.writelines(message)
        f.writelines("\n")
        print(message)
        drive_list=[]
        if data[u'Drives'] == []:
            message = "\n- WARNING, no drives detected for %s" % i
            f.writelines(message)
            f.writelines("\n")
            print(message)
        else:
            pass
            for ii in data[u'Drives']:
                drive_list.append(ii[u'@odata.id'][53:])        
        for iii in drive_list:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, iii),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                print("\n- FAIL, get command failed, error is: %s" % data)
                sys.exit()  
            message = "\n- Detailed drive information for %s -\n" % iii
            f.writelines(message)
            f.writelines("\n")
            print(message)
            for iii in data.items():
                if iii[0] == u'@odata.id' or iii[0] == u'@odata.context' or iii[0] == u'Metrics' or iii[0] == u'Links' or iii[0] == u'Description' or iii[0] == u'@odata.type' or iii[0] == u'RelatedItem' or iii[0] == u'Actions':
                    pass
                elif iii[0] == u'Oem':
                        try:
                            for iiii in iii[1][u'Dell'][u'DellPhysicalDisk'].items():
                                if iiii[0] == u'@odata.context' or iiii[0] == u'@odata.type':
                                    pass
                                else:
                                    message = "%s: %s" % (iiii[0], iiii[1])
                                    f.writelines(message)
                                    f.writelines("\n")
                                    print(message)
                        except:
                            pass
                else:
                    message = "%s: %s" % (iii[0], iii[1])
                    f.writelines(message)
                    f.writelines("\n")
                    print(message)
    f.close()
    
                
def get_backplane_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Chassis' % (idrac_ip),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    message = "\n---- Backplane Information ----"
    f.writelines(message)
    f.writelines("\n")
    print(message)
    backplane_URI_list = []
    for i in data[u'Members']:
        backplane = i[u'@odata.id']
        if "Enclosure" in backplane:
            backplane_URI_list.append(backplane)
    if backplane_URI_list == []:
        message = "- WARNING, no backplane information detected for system\n"
        f.writelines(message)
        f.writelines("\n")
        print(message)
        sys.exit()
    for i in backplane_URI_list:
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        message = "\n- Detailed backplane information for %s -\n" % i.split("/")[-1]
        f.writelines(message)
        f.writelines("\n")
        print(message)
        for iii in data.items():
            if iii[0] == u'@odata.id' or iii[0] == u'@odata.context' or iii[0] == u'Metrics' or iii[0] == u'Links' or iii[0] == u'@Redfish.Settings' or iii[0] == u'@odata.type' or iii[0] == u'RelatedItem' or iii[0] == u'Actions' or iii[0] == u'PCIeDevices':
                pass
            else:
                message = "%s: %s" % (iii[0], iii[1])
                f.writelines(message)
                f.writelines("\n")
                print(message)
    f.close()
    

def get_network_information():
    f=open("hw_inventory.txt","a")
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/NetworkInterfaces' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        print("\n- FAIL, get command failed, error is: %s" % data)
        sys.exit()
    message = "\n---- Network Device Information ----"
    f.writelines(message)
    f.writelines("\n")
    print(message)
    network_URI_list = []
    for i in data[u'Members']:
        network = i[u'@odata.id']
        network_URI_list.append(network)
    if network_URI_list == []:
        message = "\n- WARNING, no network information detected for system\n"
        f.writelines(message)
        f.writelines("\n")
        print(message)
    for i in network_URI_list:
        message = "\n- Network device details for %s -\n" % i.split("/")[-1]
        f.writelines(message)
        f.writelines("\n")
        print(message)
        i=i.replace("Interfaces","Adapters")
        response = requests.get('https://%s%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            print("\n- FAIL, get command failed, error is: %s" % data)
            sys.exit()
        for ii in data.items():
            if ii[0] == u'NetworkPorts':
                network_port_urls = []
                url_port = ii[1][u'@odata.id']
                response = requests.get('https://%s%s' % (idrac_ip, url_port),verify=False,auth=(idrac_username, idrac_password))
                data = response.json()
                if response.status_code != 200:
                    print("\n- FAIL, get command failed, error is: %s" % data)
                    sys.exit()
                else:
                    port_uri_list = []
                    for i in data[u'Members']:
                        port_uri_list.append(i[u'@odata.id'])
            if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == u'@odata.type' or ii[0] == u'NetworkDeviceFunctions' or ii[0] == u'NetworkPorts':
                pass
            elif ii[0] == "Controllers":
                mesage = ii[1][0][u'ControllerCapabilities']
                f.writelines(message)
                print(message)
                message = "FirmwarePackageVersion: %s" % ii[1][0][u'FirmwarePackageVersion']
                f.writelines(message)
                f.writelines("\n")
                print(message)
            else:
                message = "%s: %s" % (ii[0], ii[1])
                f.writelines(message)
                f.writelines("\n")
                print(message)
        for z in port_uri_list:
            response = requests.get('https://%s%s' % (idrac_ip, z),verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                print("\n- FAIL, get command failed, error is: %s" % data)
                sys.exit()
            else:
                message = "\n- Network port details for %s -\n" % z.split("/")[-1]
                f.writelines(message)
                f.writelines("\n")
                print(message)
                for ii in data.items():
                    if ii[0] == u'@odata.id' or ii[0] == u'@odata.context' or ii[0] == u'Metrics' or ii[0] == u'Links' or ii[0] == u'@odata.type':
                        pass
                    elif ii[0] == u'Oem':
                        try:
                            for iii in ii[1][u'Dell'][u'DellSwitchConnection'].items():
                                if iii[0] == u'@odata.context' or iii[0] == u'@odata.type':
                                    pass
                                else:
                                    message = "%s: %s" % (iii[0], iii[1])
                                    f.writelines(message)
                                    f.writelines("\n")
                                    print(message)
                        except:
                            pass
                    else:
                        message = "%s: %s" % (ii[0], ii[1])
                        f.writelines(message)
                        f.writelines("\n")
                        print(message)
    f.close()
                
            
        
    


if __name__ == "__main__":
    check_supported_idrac_version()
    if args["x"]:
          script_examples()
    if args["s"]:
        get_system_information()
    if args["m"]:
        get_memory_information()
    if args["c"]:
        get_cpu_information()
    if args["f"]:
        get_fan_information()
    if args["ps"]:
        get_ps_information()
    if args["S"]:
        get_storage_controller_information()
        get_storage_disks_information()
        get_backplane_information()
    if args["n"]:
        get_network_information()
    if args["a"]:
        get_system_information()
        get_memory_information()
        get_cpu_information()
        get_fan_information()
        get_ps_information()
        get_storage_controller_information()
        get_storage_disks_information()
        get_backplane_information()
        get_network_information()
    print("\n- WARNING, output also captured in \"%s\hw_inventory.txt\" file" % os.getcwd())
        
        
        
    

    
    
    
        
            
        
        

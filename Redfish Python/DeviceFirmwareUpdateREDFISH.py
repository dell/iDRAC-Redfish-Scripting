#
# DeviceFirmwareUpdateREDFISH. Python script using Redfish API to update a device firmware. Supported file image types are Windows DUPs, d7/d9 image or pm files.
#
# NOTE: If you are updating a device which doesn't need a server reboot to apply the update (Example: iDRAC, DIAGS, Driver Pack, ISM, OSC), pass in a value of "Now" for Install Option. All other devices which require a server reboot to apply the update (BIOS, CPLD, NIC, PERC, PSU, FC, HDs, Backplane), pass in NowAndReboot or NextReboot for Install Option.
#
# NOTE: Supported values for Install_Option are: Now, NowAndReboot and NextReboot. Make sure you pass in the exact value as stated (values are case sensitive). For NextReboot value, the update job will still get created and scheduled but will not get applied until the next server reboot executed by the user.
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

import requests, json, sys, re, time, warnings

from datetime import datetime

warnings.filterwarnings("ignore")

# Code to validate all correct parameters are passed in

try:
    idrac_ip = sys.argv[1]
    idrac_username = sys.argv[2]
    idrac_password = sys.argv[3]
    firmware_image_location = sys.argv[4]
    file_image_name= sys.argv[5]
    Install_Option = sys.argv[6]
except:
    print("\n- FAIL, you must pass in script name along with iDRAC IP / iDRAC username / iDRAC password / Image Path / Filename / Install Option. Example: \" script_name.py 192.168.0.120 root calvin c:\Python26 bios.exe NowAndReboot\"")
    sys.exit()

start_time=datetime.now()

# Code to convert install option to correct string due to case sensitivity in iDRAC.
if Install_Option == "now":
    install_option = "Now"
elif Install_Option == "nowandreboot":
    install_option = "NowAndReboot"
elif Install_Option == "nextreboot":
    install_option = "NextReboot"
else:
    install_option = Install_Option

# Function to check if current iDRAC version supports Redfish firmware features

def check_idrac_fw_support():
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    if statusCode == 400:
        print("\n- WARNING, current server iDRAC version does not support Redfish firmware features. Refer to Dell online Redfish documentation for information on which iDRAC version supports firmware features.")
        sys.exit()
    else:
        pass
   
# Function to download the image payload to the iDRAC

def download_image_payload():
    print("\n- WARNING, downloading \"%s\" image payload to iDRAC" % file_image_name)
    global Location
    global new_FW_version
    global dup_version
    global ETag
    req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/' % (idrac_ip), auth=(idrac_username, idrac_password), verify=False)
    statusCode = req.status_code
    data = req.json()
    filename = file_image_name.lower()
    ImageLocation = firmware_image_location
    ImagePath = ImageLocation + "\\" + filename
    ETag = req.headers['ETag']
    url = 'https://%s/redfish/v1/UpdateService/FirmwareInventory' % (idrac_ip)
    files = {'file': (filename, open(ImagePath, 'rb'), 'multipart/form-data')}
    headers = {"if-match": ETag}
    response = requests.post(url, files=files, auth = (idrac_username, idrac_password), verify=False, headers=headers)
    d = response.__dict__
    s=str(d['_content'])
    if response.status_code == 201:
        print("\n- PASS: POST command passed to download image payload to iDRAC, 201 status code returned")
    else:
        print("\n- FAIL: POST command failed to download image payload, error is %s" % response)
        print("\nMore details on status code error: %s " % d['_content'])
        sys.exit()
    d = response.__dict__
    z=re.search("Available.+?,",s).group()
    z = re.sub('[",]',"",z)
    new_FW_version = re.sub('Available','Installed',z)
    zz=z.find("-")
    zz=z.find("-",zz+1)
    dup_version = z[zz+1:]
    print("- Firmware image version of downloaded payload is: %s" % dup_version)
    Location = response.headers['Location']

# Function to install the downloaded image payload and loop checking job status

def install_image_payload():
    global job_id
    print("\n- WARNING, executing POST command to create firmware update job ID")
    url = 'https://%s/redfish/v1/UpdateService/Actions/Oem/DellUpdateService.Install' % (idrac_ip)
    InstallOption = install_option
    payload = "{\"SoftwareIdentityURIs\":[\"" + Location + "\"],\"InstallUpon\":\""+ InstallOption +"\"}"
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=payload, auth = (idrac_username, idrac_password), verify=False, headers=headers)
    d=str(response.__dict__)
    job_id_location = response.headers['Location']
    job_id = re.search("JID_.+",job_id_location).group()
    print("- PASS, %s firmware update job ID successfully created" % job_id) 
    
# Function to check the new FW version installed

def check_new_FW_version():
    if ".pm" in file_image_name:
        pass
    else:
        print("\n- WARNING, checking new firmware version installed for updated device")
        req = requests.get('https://%s/redfish/v1/UpdateService/FirmwareInventory/%s' % (idrac_ip, new_FW_version), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        if dup_version == data[u'Version']:
            print("\n- PASS, New installed firmware version is: %s" % data[u'Version'])
        else:
            print("\n- FAIL, New installed firmware version incorrect, error is: %s" % data)
            sys.exit()

# Function to check the job status for host reboot needed

def check_job_status_host_reboot():
    print("\n- WARNING, script will now loop polling the job status until marked completed") 
    time.sleep(15)
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        message_string=data[u"Messages"]
        current_time=(datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            time.sleep(1)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in data[u"Messages"] or "completed with errors" in data[u"Messages"] or "Failed" in data[u"Messages"]:
            print("- FAIL: Job failed, current message is: %s" % data[u"Messages"])
            sys.exit()
        elif data[u"TaskState"] == "Completed":
            print("\n- PASS, job ID %s successfuly marked completed, detailed final job status results:\n" % data[u"Id"])
            for i in data[u'Oem'][u'Dell'].items():
                print("%s: %s" % (i[0],i[1]))
            #print("\n- Job ID = "+data[u"Id"])
            #print("- Name = "+data[u"Name"])
            #try:
                #print("- Message = "+message_string[0][u"Message"])
            #except:
                #print("- Message = "+data[u"Messages"][0][u"Message"])
            #print("- JobStatus = "+data[u"TaskState"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            if data[u"Name"] == "Firmware Update: iDRAC":
                print("\n- WARNING, iDRAC update performed. Script will wait 3 minutes for iDRAC to reset and come back up before checking new firmware version")
                time.sleep(180)
                break
            else:
                break
        elif data[u"TaskState"] == "Completed with Errors" or data[u"TaskState"] == "Failed":
            print("\n- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- "+data[u"Messages"][0][u"Message"])
            print("- JobStatus = "+data[u"TaskState"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            print("- Message: %s" % message_string[0][u"Message"])
            time.sleep(1)
            continue

# Function to check job status for next manual reboot

def check_job_status(): 
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        data = req.json()
        message_string=data[u"Messages"]
        current_time=(datetime.now()-start_time)
        if statusCode == 202 or statusCode == 200:
            #print("\n- Query job ID command passed\n")
            time.sleep(10)
        else:
            print("Query job ID command failed, error code is: %s" % statusCode)
            sys.exit()
        if "failed" in data[u"Messages"] or "completed with errors" in data[u"Messages"]:
            print("- FAIL: Job failed, current message is: %s" % data[u"Messages"])
            sys.exit()
        elif data[u"TaskState"] == "Pending":
            print("\n- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- Message = "+data[u"Messages"][0][u"Message"])
            print("- JobStatus = "+data[u"TaskState"])
            print("\n- %s scheduled in: %s" % (job_id, str(current_time)[0:7]))
            print("\n- WARNING, Host manual reboot is now needed to complete the process of applying the firmware image.\n")
            break
        elif data[u"TaskState"] == "Completed":
            print("\n- WARNING, device selected is immediate update, incorrect install option passed in.")
            print("- %s still marked completed and firmware updated" % (job_id))
            break
        elif data[u"TaskState"] == "Completed with Errors" or data[u"TaskState"] == "Failed":
            print("\n- Job ID = "+data[u"Id"])
            print("- Name = "+data[u"Name"])
            try:
                print("- Message = "+message_string[0][u"Message"])
            except:
                print("- "+data[u"Messages"][0][u"Message"])
            print("- JobStatus = "+data[u"TaskState"])
            print("\n- %s completed in: %s" % (job_id, str(current_time)[0:7]))
            sys.exit()
        else:
            print("- Job not marked completed, current status is: %s" % data[u"TaskState"])
            print("- Message: %s\n" % message_string[0][u"Message"])
            print("- Current job execution time is: %s\n" % str(current_time)[0:7])
            time.sleep(1)
            continue


# Run code

if __name__ == "__main__":
    check_idrac_fw_support()
    download_image_payload()
    install_image_payload()
    if install_option == "NowAndReboot" or install_option == "Now":
        check_job_status_host_reboot()
        check_new_FW_version()
    else:
        check_job_status()



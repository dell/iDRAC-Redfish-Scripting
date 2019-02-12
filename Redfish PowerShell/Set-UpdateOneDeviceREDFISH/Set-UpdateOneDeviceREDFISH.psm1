<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 5.0

Copyright (c) 2017, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
   Cmdlet used to update firmware on one device using iDRAC Redfish API with Powershell
.DESCRIPTION
   Cmdlet used to update fimrware on one device iDRAC supports or upload a PM file. Supported file types are .exe, .pm (personal module) and .d9 (iDRAC only image). For updating iDRAC devices, you will be using Dell Windows Update Packages (DUP) with .exe extension. 
   
   # idrac_ip, username, password, image_directory_path, image_filename and install_option parameters are all required for performing update

   # idrac_ip, username, password, view_fw_inventory_only parameters are all required to get firmware inventory only

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: pass in iDRAC IP
   - idrac_username: pass in iDRAC username
   - idrac_password: pass in iDRAC password
   - image_directory_path: pass in the directory path where the upload image is. Example: "C:\firmware_share"
   - image_filename: pass in the name of the upload image. Example: "H330_SAS-RAID_Firmware_03NXN_WN64_25.5.2.0001_A07.EXE"
   - install_option: supported values are "Now", "NextReboot" and "NowAndReboot". You must make sure you pass in the exact syntax since these values are case sensitive. 
     For the value of "Now", you only want to use this value for devices which are immediate updates. Devices are DIAGS, DriverPack, OSC, ISM and iDRAC.
     All other devices need a server reboot to apply the update. Devices are BIOS, NIC, FW, RAID (controllers, backplane, disks), PSUs, CPLD.
     For the value of "NowAndReboot", this will download the image and automatically reboot the server to apply the image.
     For the value of "NextReboot", this will download the image but not reboot the server. Download job will stay in scheduled state and won't be applied until the next server reboot.
   - view_fw_inventory_only: this will return only the firmware inventory of devices on the system iDRAC supports for updates.

.EXAMPLE
   Set-UpdateOneDeviceREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -view_fw_inventory_only y 
   # This example will only return Firmware inventory for devices iDRAC supports
.EXAMPLE
   Set-UpdateOneDeviceREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -image_directory_path C:\ -image_filename H330_SAS-RAID_Firmware_03NXN_WN64_25.5.2.0001_A07.EXE -install_option NowAndReboot
   # This example will download the PERC H330 firmware and reboot the server now to perform the update 
#>

function Set-UpdateOneDeviceREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$image_directory_path,
    [Parameter(Mandatory=$False)]
    [string]$image_filename,
    [Parameter(Mandatory=$False)]
    [string]$install_option,
    [Parameter(Mandatory=$False)]
    [string]$view_fw_inventory_only
    )


# Function to ignore SSL certs

function Ignore-SSLCertificates
{
    $Provider = New-Object Microsoft.CSharp.CSharpCodeProvider
    $Compiler = $Provider.CreateCompiler()
    $Params = New-Object System.CodeDom.Compiler.CompilerParameters
    $Params.GenerateExecutable = $false
    $Params.GenerateInMemory = $true
    $Params.IncludeDebugInformation = $false
    $Params.ReferencedAssemblies.Add("System.DLL") > $null
    $TASource=@'
        namespace Local.ToolkitExtensions.Net.CertificatePolicy
        {
            public class TrustAll : System.Net.ICertificatePolicy
            {
                public bool CheckValidationResult(System.Net.ServicePoint sp,System.Security.Cryptography.X509Certificates.X509Certificate cert, System.Net.WebRequest req, int problem)
                {
                    return true;
                }
            }
        }
'@ 
    $TAResults=$Provider.CompileAssemblyFromSource($Params,$TASource)
    $TAAssembly=$TAResults.CompiledAssembly
    ## We create an instance of TrustAll and attach it to the ServicePointManager
    $TrustAll = $TAAssembly.CreateInstance("Local.ToolkitExtensions.Net.CertificatePolicy.TrustAll")
    [System.Net.ServicePointManager]::CertificatePolicy = $TrustAll
}



Ignore-SSLCertificates

# Setting up iDRAC login information

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
$ErrorActionPreference = "Stop"

# Code to check if system iDRAC version supports update feature

$u = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorAction Stop -Headers @{"Accept"="application/json"}
    }
    catch
    {
    }
	    if ($result.StatusCode -ne 200)
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support update feature using Redfish API`n"
	    return
	    }
	    else
	    {
	    }


if ($InstallOption -ne "")
{
Write-Host "`n- WARNING, validating '$image_filename' image. This may take a few minutes to complete depending on image size"
} 

$u = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory"

# GET command to get software inventory for all devices
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} 
$ETag=$result.Headers.ETag
$matches = ([regex]'Installed-.+?}').Matches($result)
$new_count=$matches.count - 1

if ($view_fw_inventory_only -eq "y")
{
Write-Host
Write-Host "--- Firmware Inventory ---"
Write-Host
$count = 0
While ($count -ne $new_count)
{
$install_entry = $matches[$count].Value
$new=$install_entry.Replace("}","")
$new=$new.Replace('"',"")
$u9 = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory/$new"
try 
{
$result = Invoke-WebRequest -Uri $u9 -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
}
catch
{
#pass
}
$content_search=$result.Content
$name=[regex]::Match($content_search, '"Name.+?,').captures.groups[0].value
$name = $name.Replace(",","")
$updateable=[regex]::Match($content_search, '"Updateable.+?,').captures.groups[0].value
$updateable = $updateable.Replace(",","")
Write-Host "- " $name
$current_version=$new.Split("-")[-1]
Write-Host "-  ""Installed version"": $current_version"
#[String]::Format('-  "{0}" ',$new)
#Write-Host "-  " $new
Write-Host "- " $updateable
Write-Host
#$current_version=$new.Split("-")[-1]
#Write-Host "Installed version: $current_version"
$count++
}
return
}

if ($view_fw_inventory_only -eq "n")
{
return
}

#Write-Host "`n- WARNING, validating firmware image, this may take up to one minute.`n"
$complete_path=$image_directory_path + "\" + $image_filename
$headers = @{"if-match" = $ETag; "Accept"="application/json"}

# Code to read the image file for download to the iDRAC

$CODEPAGE = "iso-8859-1"
$fileBin = [System.IO.File]::ReadAllBytes($complete_path)
$enc = [System.Text.Encoding]::GetEncoding($CODEPAGE)
$fileEnc = $enc.GetString($fileBin)
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"
$bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$image_filename`"",
		"Content-Type: application/octet-stream$LF",
        $fileEnc,
        "--$boundary",
        "Content-Disposition: form-data; name=`"importConfig`"; filename=`"$image_filename`"",
		"Content-Type: application/octet-stream$LF",
        #$importConfigFileEnc,
        #$fileBin,
        "--$boundary--$LF"
) -join $LF

# POST command to download the image payload to the iDRAC
$result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -ContentType "multipart/form-data; boundary=`"$boundary`"" -Headers $headers -Body $bodyLines 

$get_content=$result1.Content
$Location = $result1.Headers['Location']
$get_version=[regex]::Match($get_content, 'Available.+?,').captures.groups[0].value
$get_version=$get_version.Replace(",","")
$get_version=$get_version.Replace('"',"")
$get_fw_version=$get_version.Split("-")

Write-Host
Write-Host "- Warning, image version to install is:"$get_fw_version[-1]
$compare_version=$get_version.Replace("Available","Installed")
#Write-Host
#Write-Host $compare_version
#Write-Host

if ($result1.StatusCode -eq 201)
{
    [String]::Format("- PASS, statuscode {0} returned successfully for POST command to download payload image to iDRAC",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$result1.StatusCode,$result1)
    return
}

$InstallOption=$install_option
$u2 = "https://$idrac_ip/redfish/v1/UpdateService/Actions/Oem/DellUpdateService.Install"
$JsonBody="{""SoftwareIdentityURIs"":[""$Location""],""InstallUpon"":""$InstallOption""}"

# POST command to create update job ID

$result2 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} 
 

$job_id_search=$result2.Headers['Location']
$job_id=$job_id_search.Split("/")[-1]

if ($result2.StatusCode -eq 202)
{
    [String]::Format("- PASS, statuscode {0} returned successfully for POST command to create update job ID {1}",$result2.StatusCode, $job_id)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$result2.StatusCode,$result2)
    return
}
 

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date

# Code to check what type of install option was passed in

if ($InstallOption -eq "Now" -or $InstallOption -eq "NowAndReboot")
{
$end_time = $start_time.AddMinutes(30)
$force_count=0
Write-Host "- WARNING, script will now loop polling the job status until marked completed`n"
while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to loop query the job until marked completed or failed

$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobState -eq "Failed")
{
Write-Host
[String]::Format("- FAIL, job marked as failed, detailed error info: {0}",$overall_job_output)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}

# elseif statement for if the server cannot gracefully reboot, code will perform a forced reboot

elseif ($force_count -eq 8 -and $overall_job_output.Message -eq "Task successfully scheduled." )
{
Write-Host
Write-Host "- WARNING, graceful shutdown of the server failed after retries for 5 minutes, forcing server reboot"
Write-Host
$force_count++
$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress 


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power OFF the server

$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power OFF the server",$result1.StatusCode)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power ON the server

$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}


if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}
else
{
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 1
if ($InstallOption -eq "NowAndReboot")
{
Start-Sleep 15
$force_count++
}
}
}
#Write-Host
#[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "`n- PASS, Job ID $job_id successfully marked completed. Job completed in $final_completion_time`n"
Write-Host "- Detailed final job status results for job ID '$job_id':"
$overall_job_output
if ($overall_job_output.Name -eq "update:DCIM:INSTALLED#iDRAC.Embedded.1-1#IDRACinfo")
{
Write-Host "`n- WARNING, iDRAC update detected. Script will wait 5 minutes for iDRAC to reset and come back up before verify firmware version`n"
Start-Sleep 300
}
else
{
Start-Sleep 10
} 
}

# Code for NextReboot install option, this will check for job status of scheduled

if ($InstallOption -eq "NextReboot")
{
$end_time = $start_time.AddMinutes(5)
while ($overall_job_output.Message -ne "Task successfully scheduled.")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to loop query the job until marked completed or failed

$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobState -eq "Failed")
{
Write-Host
[String]::Format("- FAIL, job marked as failed, detailed error info: {0}",$overall_job_output)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 5 minutes has been reached before marking the job completed"
return
}
else
{
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 1
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as scheduled",$job_id)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "  Job ID was scheduled in $final_completion_time"
Write-Host
Write-Host "- WARNING, update job ID $job_id will stay in scheduled state and not be applied until next server reboot"
return
}


# GET command to check final version was installed successfully

if ($image_filename.Contains(".pm"))
{
return
}
else
{

$u = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory/$compare_version"
try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
	    if ($result.StatusCode -eq 200)
	    {
        $new_version = $compare_version.Split("-")[-1]
        Write-Host "- PASS, verified new image version installed is: $new_version"
	    }
	    else
	    {
        $new_version = $compare_version.Split("-")[-1]
        Write-Host "- FAIL, new version not installed is: $new_version"
	    }
return
}
}



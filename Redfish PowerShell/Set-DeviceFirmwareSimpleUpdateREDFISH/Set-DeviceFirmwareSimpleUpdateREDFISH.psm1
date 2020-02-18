<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 1.0

Copyright (c) 2020, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
   Cmdlet using Redfish DMTF action SimpleUpdate to update device firmware using a firmware image stored locally.
.DESCRIPTION
   Cmdlet used to update fimrware for one supported device or upload a PM file. Supported file types are .exe, .pm (personal module) and .d9 (iDRAC only image). For updating devices, you will be using Dell Windows Update Packages (DUP) with .exe extension. 

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - image_directory_path: Pass in the directory path where the upload image is. Example: "C:\firmware_directory"
   - image_filename: Pass in the name of the upload image. Example: "H330_SAS-RAID_Firmware_03NXN_WN64_25.5.2.0001_A07.EXE"
   - reboot_server: Pass in "y" to automatically reboot the server to apply the update or "n" to not reboot the server. Passing in "n" means the update job will still get scheduled and will execute on next server manual reboot. NOTE: There are devices which perform an update immediately and devices that need a reboot to apply the update. For more details on this behavior, refer to Lifecycle Controller User Guide update section.
   - view_fw_inventory_only: this will return only the firmware inventory of devices on the system iDRAC supports for updates.

.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -view_fw_inventory_only y 
   # This example will only return Firmware inventory for all devices in the server. If needed, you can redirect output into a variable allowing you to get only specific properties.
.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -image_directory_path C:\Downloads -image_filename BIOS_8G2RV_WN64_2.4.8.EXE -reboot_server y
   # This example will download BIOS firmware and reboot the server now to perform the update 
.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -image_directory_path C:\Downloads -image_filename iDRAC-with-Lifecycle-Controller_Firmware_4JCPK_WN64_4.00.00.00_A00.EXE
   # This example will update iDRAC firmware and get applied immediately. Since this device gets update immediately, no server reboot is needed.
.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -image_directory_path C:\Downloads -image_filename BIOS_8G2RV_WN64_2.4.8.EXE -reboot_server n
   # This example will download BIOS firmware and NOT reboot the server to apply the update. The update job will still get scheduled and will execute on next manual server reboot.
#>

function Set-DeviceFirmwareSimpleUpdateREDFISH {

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
    [string]$reboot_server,
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
    $TrustAll = $TAAssembly.CreateInstance("Local.ToolkitExtensions.Net.CertificatePolicy.TrustAll")
    [System.Net.ServicePointManager]::CertificatePolicy = $TrustAll
}

# Function to set up iDRAC credentials 

function setup_idrac_creds
{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}


# Function get current firmware versions

function get_firmware_versions
{
Write-Host "`n--- Getting Firmware Inventory For iDRAC $idrac_ip ---`n"

$expand_query ='?$expand=*($levels=1)'
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$expand_query"
try
{
$get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}
$get_fw_inventory = $get_result.Content | ConvertFrom-Json
$get_fw_inventory.Members

return
}

# Function download image payload

function download_image_payload
{

$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory"
try
{
$result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

$ETag=$result.Headers.ETag

Write-Host "`n- WARNING, validating firmware image, this may take a few minutes depending of the size of the image"

$complete_path=$image_directory_path + "\" + $image_filename
$headers = @{"if-match" = $ETag; "Accept"="application/json"}

# Code to read the image file, download to the iDRAC

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

try
{
$result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType "multipart/form-data; boundary=`"$boundary`"" -Headers $headers -Body $bodyLines -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
} 

$get_content=$result1.Content
$Location = $result1.Headers['Location']
$get_version=[regex]::Match($get_content, 'Available.+?,').captures.groups[0].value

$get_version=$get_version.Replace(",","")
$get_version=$get_version.Replace('"',"")
$available_entry = $get_version
$global:available_entry = $available_entry
$get_fw_version=$get_version.Split("-")

Write-Host "- Warning, firmware image version to install is:"$get_fw_version[-1]
$compare_version=$get_version.Replace("Available","Installed")


if ($result1.StatusCode -eq 201)
{
    [String]::Format("- PASS, statuscode {0} returned successfully for POST command to download payload image to iDRAC",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$result1.StatusCode,$result1)
    return
}

}

# Function install image payload, query job status, reboot server

function install_image_payload_query_job_status_reboot_server

{

$uri = "https://$idrac_ip/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate"
$image_uri = "/redfish/v1/UpdateService/FirmwareInventory/$available_entry"
$JsonBody = @{'ImageURI'= $image_uri} | ConvertTo-Json -Compress

try
{
$result2 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}
 

if ($result2.StatusCode -eq 202)
{
    $job_id_search=$result2.Headers['Location']
    $job_id=$job_id_search.Split("/")[-1]
    #$global:job_id
    [String]::Format("- PASS, statuscode {0} returned successfully for POST command to create update job ID {1}",$result2.StatusCode, $job_id)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$result2.StatusCode,$result2)
    return
}

# Loop job status until marked completed or scheduled 

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)
$force_count=0
Write-Host "- WARNING, script will now loop polling the job status every 5 seconds until marked either scheduled or completed`n"
while ($true)
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/TaskService/Tasks/$job_id"

try
{
$result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.Messages.Message.Contains("Fail") -or $overall_job_output.Messages.Message.Contains("Failed") -or $overall_job_output.Messages.Message.Contains("fail") -or $overall_job_output.Messages.Message.Contains("failed") -or $overall_job_output.Messages.Message.Contains("Job for this device is already present") -or $overall_job_output.Messages.Message.Contains("unable") -or $overall_job_output.Messages.Message.Contains("Unable"))
{
Write-Host
[String]::Format("- FAIL, job id $job_id marked as failed, error message: {0}",$overall_job_output.Messages.Message)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}

elseif ($overall_job_output.Messages.Message -eq "Task successfully scheduled.")
{
Write-Host "`n- PASS, job ID '$job_id' successfully marked as scheduled."
$job_completed = "no"
break
}
elseif ($overall_job_output.Messages.Message -eq "The specified job has completed successfully." -or $overall_job_output.Messages.Message -eq  "Job completed successfully." -or $overall_job_output.Messages.Message.Contains("complete"))
{
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$job_id' successfully marked as completed"
Write-Host "`nFirmware update job execution time:"
$final_completion_time
return
}
else
{
Write-Host "- Job ID '$job_id' not marked scheduled or completed, checking job status again"
Start-Sleep 5
}

}

# Reboot server

if ($reboot_server -eq "n" -or $reboot_server -eq "N" -and $job_completed -eq "no")
{
Write-Host "- WARNING, user selected to not automatically reboot the server. Update job is scheduled and will be applied on next server manual reboot"
return
}

if ($reboot_server -eq "y" -or $reboot_server -eq "Y" -and $job_completed -eq "yes")
{
Write-Host "- WARNING, no server reboot is needed since job ID is already marked completed, immediate update was performed"
return
}

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
try
{
$result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result.StatusCode -eq 200)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned successfully to get current power state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$result_output = $result.Content | ConvertFrom-Json
$power_state = $result_output.PowerState

if ($power_state -eq "On")
{
Write-Host "- WARNING, Server current power state is ON, performing graceful shutdown"
}


$JsonBody = @{ "ResetType" = "GracefulShutdown"
    } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

try
{
$result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned to gracefully power OFF the server",$result1.StatusCode)
    Start-Sleep 15
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$count = 1
while($true)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
try
{
$result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

$result_output = $result.Content | ConvertFrom-Json
$power_state = $result_output.PowerState

if ($power_state -eq "Off")
{
Write-Host "- PASS, validated server graceful shutdown completed, server in OFF state"
break
}
elseif ($count -eq 5)
{
Write-Host "- WARNING, server did not accept graceful shutdown request, performing force off"

$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

try
{
$result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned to force power OFF the server",$result1.StatusCode)
    Start-Sleep 15
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

}
else
{
Write-Host "- WARNING, server still in ON state waiting for graceful shutdown to complete, will check server status again in 1 minute"
Start-Sleep 60
}

$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

try
{
$result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    break
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}


if ($power_state -eq "Off")
{
$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power ON the server

try
{
$result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

}

# Loop job status until marked completed 

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(50)
$force_count=0
Write-Host "- WARNING, script will now loop polling the job status every 30 seconds until marked completed`n"
while ($true)
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/TaskService/Tasks/$job_id"

try
{
$result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.Messages.Message.Contains("Fail") -or $overall_job_output.Messages.Message.Contains("Failed") -or $overall_job_output.Messages.Message.Contains("fail") -or $overall_job_output.Messages.Message.Contains("failed"))
{
Write-Host
[String]::Format("- FAIL, job id $job_id marked as failed, error message: {0}",$overall_job_output.Messages.Message)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 50 minutes has been reached before marking the job completed"
return
}
elseif ($overall_job_output.Messages.Message -eq "The specified job has completed successfully." -or $overall_job_output.Messages.Message -eq  "Job completed successfully." -or $overall_job_output.Messages.Message.Contains("complete"))
{
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$job_id' successfully marked as completed"
Write-Host "`nFirmware update job execution time:"
$final_completion_time
return
}
else
{
Write-Host "- Job ID '$job_id' not marked completed, checking job status again"
Start-Sleep 30
}

}

}

# Run cmdlet

Ignore-SSLCertificates
setup_idrac_creds

# Code to check for supported iDRAC version installed

$query_parameter = "?`$expand=*(`$levels=1)" 
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$query_parameter"
try
{
$get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
if ($get_result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
}
else
{
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
$get_result
return
}


if ($view_fw_inventory_only -eq "y" -or $view_fw_inventory_only -eq "Y")
{
get_firmware_versions
}

elseif ($image_directory_path -ne "" -and $image_filename -ne "")
{
download_image_payload
install_image_payload_query_job_status_reboot_server
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s)"
}



}







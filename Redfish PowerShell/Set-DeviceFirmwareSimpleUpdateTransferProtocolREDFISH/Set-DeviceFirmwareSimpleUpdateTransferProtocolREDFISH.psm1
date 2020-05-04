<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 6.0

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
   Cmdlet using Redfish DMTF action SimpleUpdate to update one device firmware using a firmware image stored on a supported network share.
.DESCRIPTION
   Cmdlet used to update fimrware for one device iDRAC supports using a supported network share which contains the firmware image. Supported image types are Dell Windows Update Packages (DUP) with .EXE extension. 

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - view_fw_inventory_only: this will return only the firmware inventory of devices on the system iDRAC supports for updates.
   - get_supported_protocols: Get current supported transfer protocols for SimpleUpdate action, pass in "y"
   - uri_path: Pass in the complete URI path of the network share along with the firmware image name
   - protocol_type: Pass in the transfer protocol type you are using for the URI path

.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateTransferProtocolREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -view_fw_inventory_only y 
   # This example will only return Firmware inventory for all devices in the server. If needed, you can redirect output into a variable allowing you to get only specific properties.
.EXAMPLE
   Set-DeviceFirmwareSimpleUpdateTransferProtocolREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -protocol_type HTTP -uri_path http://192.168.0.130/http_share/SAS-RAID_Firmware_G7N2C_WN32_25.5.6.0009_A14.EXE -protocol_type HTTP
   # This example using HTTP share will download RAID controller firmware and reboot the server now to perform the update 
#>

function Set-DeviceFirmwareSimpleUpdateTransferProtocolREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$view_fw_inventory_only,
    [Parameter(Mandatory=$False)]
    [string]$get_supported_protocols,
    [Parameter(Mandatory=$False)]
    [string]$uri_path,
    [Parameter(Mandatory=$False)]
    [string]$protocol_type
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


# Function to get Powershell Version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


# Function get current firmware versions

function get_firmware_versions
{
Write-Host
Write-Host "--- Getting Firmware Inventory For iDRAC $idrac_ip ---"
Write-Host

$expand_query ='?$expand=*($levels=1)'
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$expand_query"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
    $get_fw_inventory = $result.Content | ConvertFrom-Json
    $get_fw_inventory.Members
    break
}



# Function get supported protocols

function get_supported_protocols
{
$uri = "https://$idrac_ip/redfish/v1/UpdateService"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
$get_output=$get_result.RawContent
try
{
$get_supported_protocols=[regex]::Match($get_output, "TransferProtocol.+?,").captures.groups[0].value
$get_supported_protocols=$get_supported_protocols.Replace(",","")
}
catch
{
Write-Host "- FAIL, unable to get supported transfer protocols"
break
}
Write-Host "`n- Supported Transfer Protocol(s) for SimpleUpdate Action -`n"
$get_supported_protocols
break
}


# Function Install image payload, query job status, reboot server

function install_image_payload_query_job_status_reboot_server

{

$uri = "https://$idrac_ip/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate"
$JsonBody = @{'ImageURI'= $uri_path ; 'TransferProtocol' = $protocol_type} | ConvertTo-Json -Compress
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result2 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result2 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 
 
if ($result2.StatusCode -eq 202)
{
    $job_id_search=$result2.Headers['Location']
    $job_id=$job_id_search.Split("/")[-1]
    [String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to create update job ID '{1}'",$result2.StatusCode, $job_id)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$result2.StatusCode,$result2)
    break
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
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.Messages.Message.Contains("Fail") -or $overall_job_output.Messages.Message.Contains("Failed") -or $overall_job_output.Messages.Message.Contains("fail") -or $overall_job_output.Messages.Message.Contains("failed") -or $overall_job_output.Messages.Message.Contains("Job for this device is already present") -or $overall_job_output.Messages.Message.Contains("Unable") -or $overall_job_output.Messages.Message.Contains("unable"))
{
Write-Host
[String]::Format("- FAIL, job id $job_id marked as failed, error message: {0}",$overall_job_output.Messages.Message)
break
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
break
}

elseif ($overall_job_output.Messages.Message -eq "Task successfully scheduled.")
{
Write-Host "`n- PASS, job ID '$job_id' successfully marked as scheduled. Server will now reboot to execute the firmware update"
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
break
}
else
{
Write-Host "- Job ID '$job_id' not marked scheduled or completed, checking job status again"
Start-Sleep 5
}

}

# Check for iDRAC current firmware version

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
$get_output = $get_result.Content | ConvertFrom-Json
$get_iDRAC_fw_version = [int]$get_output.FirmwareVersion.Split(".")[0]

# Reboot server if iDRAC version is at an version older than 4.00

if ($get_iDRAC_fw_version -lt 4)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

if ($result.StatusCode -eq 200)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned successfully to get current power state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    break
}

$result_output = $result.Content | ConvertFrom-Json
$power_state = $result_output.PowerState

if ($power_state -eq "On")
{
Write-Host "- WARNING, Server current power state is ON, performing graceful shutdown"



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
break
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned to attempt graceful server shutdown",$result1.StatusCode)
    Start-Sleep 15
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
}

$count = 1
while($true)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

$result_output = $result.Content | ConvertFrom-Json
$power_state = $result_output.PowerState

if ($power_state -eq "Off")
{
Write-Host "- PASS, validated server in OFF state"
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
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned to force power OFF the server",$result1.StatusCode)
    Start-Sleep 15
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
}

}
else
{
Write-Host "- WARNING, server still in ON state waiting for graceful shutdown to complete, will check server status again in 1 minute"
$count++
Start-Sleep 60
continue
}
}

$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    $power_state = "On"
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
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
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
}
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
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.Messages.Message.Contains("Fail") -or $overall_job_output.Messages.Message.Contains("Failed") -or $overall_job_output.Messages.Message.Contains("fail") -or $overall_job_output.Messages.Message.Contains("failed"))
{
Write-Host
[String]::Format("- FAIL, job id $job_id marked as failed, error message: {0}",$overall_job_output.Messages.Message)
break
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 50 minutes has been reached before marking the job completed"
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
break
}
else
{
Write-Host "- Job ID '$job_id' not marked completed, checking job status again"
Start-Sleep 30
}

}


}

# Run cmdlet

get_powershell_version
setup_idrac_creds

# Code to check for supported iDRAC version installed

$query_parameter = "?`$expand=*(`$levels=1)" 
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$query_parameter"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
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


if ($view_fw_inventory_only.ToLower() -eq "y")
{
get_firmware_versions
}

elseif ($get_supported_protocols.ToLower() -eq "y")
{
get_supported_protocols
}

elseif ($uri_path -and $protocol_type)
{
install_image_payload_query_job_status_reboot_server
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s)"
}

}







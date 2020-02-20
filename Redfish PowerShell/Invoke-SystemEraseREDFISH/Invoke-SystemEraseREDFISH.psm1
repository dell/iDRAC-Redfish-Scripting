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
   Cmdlet using Redfish API with OEM extension to perform iDRAC System Erase feature. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash. 
.DESCRIPTION
   Cmdlet using Redfish API with OEM extension to perform iDRAC System Erase feature. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash. WARNING, this feature is desctructive and the main purpose for using this feature is to repurpose or retire server hardware. For erasing hard drives, there is no option to select a specific drive. Once you pass in either CryptographicErasePD or OverwritePD component value to erase drives, iDRAC is going to erase any supported drive it detects for that value. For more details on each supported component, refer to iDRAC Lifecycle Controller User Guide.
   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - get_supported_system_erase_components: Pass in 'y' to get the list of supported components for System Erase feature. The string values returned, these exact values will be used for 'execute_system_erase' argument.
   - execute_system_erase: Pass in the system erase component(s) you want to erase. If passing in multiple components, make sure to use comma separator and surround the value with double quotes. Example: "BIOS,IDRAC,DIAG". NOTE: These values are case sensitive, make sure to pass in exact string values you get from 'get_system_erase_components' argument.
   - power_on_server: Pass in 'y' if you want the server to automatically power ON after system erase process is complete/iDRAC reboot. By default, once the system erase job ID is marked completed, server will be in OFF state, reboot the iDRAC and stay in OFF state.

.EXAMPLE
   Invoke-SystemEraseREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_system_erase_components y
   # This example will get supported component string values you can pass in for executing System Erase operation 
.EXAMPLE
   Invoke-SystemEraseREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -execute_system_erase DIAG -power_on_server y
   # This example will execute System Erase operation erasing remote DIAGs on the iDRAC. Once the iDRAC is back up after System Erase process completes, server will get automatically powered ON.
.EXAMPLE
   Invoke-SystemEraseREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -execute_system_erase "BIOS,IDRAC"
   # This example will execute System Erase operation reseting BIOS and iDRAC to default settings. Once the iDRAC is back up after System Erase process completes, server will still be in OFF state.
#>

function Invoke-SystemEraseREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_system_erase_components,
    [Parameter(Mandatory=$False)]
    [string]$execute_system_erase,
    [Parameter(Mandatory=$False)]
    [string]$power_on_server
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


# Get System Erase Supported Components

function get_system_erase_components
{
Write-Host "`n- Supported Components for System Erase iDRAC Feature -`n"
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService"
try
{
$get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
break
}

$get_content_key=$get_result.Content | ConvertFrom-Json
$system_erase_action="#DellLCService.SystemErase"
$allow_values = "Component@Redfish.AllowableValues"
$get_content_key.Actions.$system_erase_action.$allow_values
Write-Host
break
}


# Function to execute System Erase feature

$Global:job_id = $null
$Global:bios_component = $null
function execute_system_erase
{

# Create body payload for POST command


if ($execute_system_erase.Contains(","))
{
$string_split = $execute_system_erase.Split(",")
    if ($string_split.Contains("BIOS"))
    {
    $Global:bios_component = "yes"
    }
    else
    {
    $Global:bios_component = "no"
    }
$JsonBody = @{"Component"=[System.Collections.ArrayList]@()}
    foreach ($item in $string_split)
    {
    $JsonBody["Component"]+=$item
    }
Write-Host "`n- Keys and Values being passed in for POST action 'SystemErase' -`n"
$JsonBody
$JsonBody = $JsonBody | ConvertTo-Json -Compress
}
else
{
    if ($execute_system_erase.Contains("BIOS"))
    {
    $Global:bios_component = "yes"
    }
    else
    {
    $Global:bios_component = "no"
    }
$JsonBody = @{"Component"=[System.Collections.ArrayList]@()}
$JsonBody["Component"]+=$execute_system_erase
   
Write-Host "`n- Keys and Values being passed in for POST action 'SystsemErase' -`n"
$JsonBody
$JsonBody = $JsonBody | ConvertTo-Json -Compress
}

$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SystemErase"

try
{
$post_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
}
catch
{
Write-Host "`n- FAIL, POST command failed to execute System Erase, detailed error results:`n"
$RespErr
break
}


if ($post_result.StatusCode -eq 202 -or $post_result.StatusCode -eq 200)
{
    $job_id_search=$post_result.Headers['Location']
    $Global:job_id=$job_id_search.Split("/")[-1]
    [String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to create update job ID '{1}'",$post_result.StatusCode, $Global:job_id)
    Write-Host
    return
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode,$post_result)
    break
}

}



function loop_job_status
{

$job_message_old = ""
$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(50)
$force_count=0
Write-Host "- WARNING, script will now loop polling the job status until marked completed`n"
while ($true)
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$Global:job_id"

    try
    {
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
$get_output = $result.Content | ConvertFrom-Json
$job_message_new = $get_output.Message
    try
    {
    $SA_report_file_location = $result.Headers.Location
    }
    catch
    {
    }
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.Message.Contains("Fail") -or $overall_job_output.Message.Contains("Failed") -or $overall_job_output.Message.Contains("fail") -or $overall_job_output.Message.Contains("failed") -or $overall_job_output.Message.Contains("already"))
{
Write-Host
[String]::Format("- FAIL, job id $Global:job_id marked as failed, error message: {0}",$overall_job_output.Message)
break
}
elseif ($overall_job_output.Message.Contains("partially") -or $overall_job_output.Message.Contains("part"))
{
Write-Host
[String]::Format("- WARNING, job id $Global:job_id completed with issues, check iDRAC Lifecyle Logs for more details. Final job message: {0}",$overall_job_output.Message)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$Global:job_id' successfully marked as completed"
Write-Host "`nSystem Erase job execution time:"
$final_completion_time
break
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 50 minutes has been reached before marking the job completed"
break
}
elseif ($overall_job_output.Message -eq "The System Erase Operation is completed successfully." -or $overall_job_output.Message -eq  "Job completed successfully." -or $overall_job_output.Message.Contains("complete"))
{
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$Global:job_id' successfully marked as completed"
Write-Host "`nSystem Erase job execution time:"
$final_completion_time
break
}
else
{
    if ($job_message_new -ne $job_message_old)
    {
    Write-Host "- Job ID '$Global:job_id' not marked completed, checking job status again. Current job message: $job_message_new"
    $job_message_old = $job_message_new
    }
    else
    {
    }
}


}

}

# Function to power on server

function power_on_server

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
break
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    break
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
}

}


function finish_bios_reset_to_default
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
break
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server. Cmdlet will now loop checking the server power status until reported OFF",$result1.StatusCode)
    Start-Sleep 120
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    break
}

while ($true)
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
break
}

$result_output = $result.Content | ConvertFrom-Json
$power_state = $result_output.PowerState
    if ($power_state -eq "Off")
    { 
    Write-Host "- PASS, verified server is in OFF state, BIOS reset to default process is complete"
    break
    }
    else
    {
    Write-Host "- WARNING, server still in ON state, checking server power status again"
    Start-Sleep 60
    }


}




}



# Run cmdlet

Ignore-SSLCertificates
setup_idrac_creds

# Check to validate iDRAC version detected supports this feature

$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService"
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
$get_actions = $get_result.Content | ConvertFrom-Json
$system_erase_action_name = "#DellLCService.SystemErase"
$validate_supported_idrac = $get_actions.Actions.$system_erase_action_name
    try
    {
    $test = $validate_supported_idrac.GetType()
    }
    catch
    {
    Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
    return
    }
}
else
{
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
return
}

if ($get_system_erase_components.ToLower() -eq "y")
{
get_system_erase_components
}

elseif ($execute_system_erase)
{
execute_system_erase
loop_job_status
    if ($Global:bios_component -eq "yes")
    {
    Write-Host "- WARNING, BIOS component detected. Cmdlet will wait 5 minutes for iDRAC to come back up, then power ON server to complete BIOS reset to default process"
    Start-Sleep 300
    finish_bios_reset_to_default
        if ($power_on_server.ToLower() -eq "y")
        {
        Write-Host "`n- User selected to power ON server after System Erase process completes"
        power_on_server
        return
        }
    }
    if ($power_on_server.ToLower() -eq "y")
    {
    Write-Host "`n- User selected to power ON server after System Erase process completes. Cmdlet will wait 5 minutes for iDRAC to come back up before executing power ON"
    Start-Sleep 300
    power_on_server
    return
    }
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s)"
}



}







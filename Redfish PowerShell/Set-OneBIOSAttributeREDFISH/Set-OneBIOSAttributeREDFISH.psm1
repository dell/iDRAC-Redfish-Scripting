<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 4.0

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
   Cmdlet used to set one BIOS attribute or get current value of BIOS attributes using REDFISH API
   IMPORTANT: Make sure you are using latest Powershell version 5 or newer to execute this cmdlet. Execute "Get-Host" to check the version.
.DESCRIPTION
   Cmdlet used to either set one BIOS attribute or get current value of BIOS attributes. When setting BIOS attribute, make sure you pass in exact name of the attribute and value since these are case sensitive. Example: For attribute MemTest, you must pass in "MemTest". Passing in "memtest" will fail.
   - idrac_ip, REQUIRED, pass in idrac IP
   - idrac_username, REQUIRED, pass in idrac user name
   - idrac_password, REQUIRED, pass in idrac password
   - attribute_name, OPTIONAL, pass in name of the attribute
   - attribute_value, OPTIONAL, pass in the value you want to set the attribute to
   - view_attribute_list_only, OPTIONAL, this will return all attributes along with their current values
.EXAMPLE
	This example shows only getting BIOS attributes and current values
    Set-OneBIOSAttributeREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -view_attribute_list_only y 
.EXAMPLE
	This example shows setting BIOS attribute MemTest to Disabled
    Set-OneBIOSAttributeREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -attribute_name MemTest -attribute_value Disabled
#>

function Set-OneBIOSAttributeREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$attribute_name,
    [Parameter(Mandatory=$False)]
    [string]$attribute_value,
    [Parameter(Mandatory=$False)]
    [string]$view_attribute_list_only

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

# Function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

get_powershell_version

function check_supported_idrac_version
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"
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
    Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API"
    $RespErr
    break
    }
}


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


check_supported_idrac_version

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"

# GET command to get all attributes

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
Write-Host
$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes

if ($view_attribute_list_only -eq "y")
{
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get attributes",$result.StatusCode)
    Write-Host
    $get_all_attributes.Attributes
    return
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
}

if ($view_attribute_list_only -eq "n")
{
return
}


$get_attribute_name_and_value= $get_all_attributes.Attributes | Select $attribute_name
$get_attribute_value_only=$attribute_name

if ($get_attribute_name_and_value.$get_attribute_value_only -eq $attribute_value)
{
    [String]::Format("- WARNING, {0} current value is: {1}, pending value is: {2},",$attribute_name,$get_attribute_name_and_value.$get_attribute_value_only,$attribute_value)
    $choice = Read-Host "  do you still want to apply changes? Type (y) or (n)"
if ($choice -eq "n")
{
return
}
}

Write-Host
[String]::Format("- WARNING, {0} current value is: {1}, changing value to: {2}",$attribute_name,$get_attribute_name_and_value.$get_attribute_value_only,$attribute_value)
Write-Host

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios/Settings"

if ($attribute_value -match "^[\d\.]+$")
{
$attribute_value = [int]$attribute_value
}

$JsonBody = @{ Attributes = @{
    "$attribute_name"=$attribute_value
    }} | ConvertTo-Json -Compress

# PATCH command to set attribute pending value

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Patch -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Patch -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($result1.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned to successfully set attribute pending value",$result1.StatusCode)
    
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}


$JsonBody = @{ "TargetSettingsURI" ="/redfish/v1/Systems/System.Embedded.1/Bios/Settings"
    } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"

# POST command to create BIOS config job and schedule it

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
$get_raw_content=$result1.RawContent | ConvertTo-Json -Compress
$job_status_search=[regex]::Match($get_raw_content, "JID_.+?r").captures.groups[0].value
$job_id=$job_status_search.Replace("\r","")
Start-Sleep 3

if ($result1.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned to successfully create job: {1}",$result1.StatusCode,$job_id)
    Start-Sleep 5
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to check BIOS job status of scheduled before reboot the server

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

if ($overall_job_output.JobState -eq "Scheduled")
{
[String]::Format("- PASS, {0} job ID marked as scheduled",$job_id)
}
else 
{
Write-Host
[String]::Format("- FAIL, {0} job ID not marked as scheduled",$job_id)
[String]::Format("- Extended error details: {0}",$overall_job_output)
return
}

# POST command to power ON or OFF/ON the server

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
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
$get_content = $result.Content | ConvertFrom-Json
$host_power_state = $get_content.PowerState

if ($host_power_state -eq "On")
{
Write-Host "- WARNING, server power state ON, performing graceful shutdown"
$JsonBody = @{ "ResetType" = "GracefulShutdown" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
    [String]::Format("- PASS, statuscode {0} returned to gracefully shutdown the server",$result1.StatusCode)
    Start-Sleep 15
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

Start-Sleep 10
$count = 1
while ($true)
{

if ($count -eq 5)
{
Write-Host "- FAIL, retry count to validate graceful shutdown has been hit. Manually check server status and reboot to execute the configuration job"
return 
}

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
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
$get_content = $result.Content | ConvertFrom-Json
$host_power_state = $get_content.PowerState

if ($host_power_state -eq "Off")
{
Write-Host "- PASS, verified server is in OFF state"
$host_power_state = ""
break
}
else
{
Write-Host "- WARNING, server still in ON state waiting for graceful shutdown to complete, polling power status again"
Start-Sleep 15
$count++
}

}

$JsonBody = @{ "ResetType" = "On" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}

if ($host_power_state -eq "Off")
{
Write-Host "- WARNING, server power state OFF, performing power ON operation"
$JsonBody = @{ "ResetType" = "On" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

Start-Sleep 10
}

Write-Host
Write-Host "- WARNING, cmdlet will now poll job ID every 15 seconds until marked completed"
Write-Host

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)

while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to loop query the job until marked completed or failed

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
else
{
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 15
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "  Job completed in $final_completion_time"

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"

# GET command to check BIOS attribute new current value

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

Write-Host
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get attribute(s)",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
}

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes
$get_attribute_name_and_value= $get_all_attributes.Attributes | Select $attribute_name
$get_attribute_value_only=$attribute_name

if ($get_attribute_name_and_value.$get_attribute_value_only -eq $attribute_value)
{
    [String]::Format("- PASS, {0} attribute successfully set to {1}",$attribute_name,$get_attribute_name_and_value.$get_attribute_value_only)
}
else
{
    [String]::Format("- FAIL, {0} not set to {1}",$attribute_name,$new_value)
    return
}

}
<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0

Copyright (c) 2018, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
   Cmdlet used to set, change or delete BIOS passwords (system or setup)
   IMPORTANT: Make sure you are using latest Powershell version 5 or newer to execute this cmdlet. Execute "Get-Host" to check the version.
.DESCRIPTION
   Cmdlet used to either set, change or delete BIOS passwords (system or setup) using Redfish API. 
   - idrac_ip, REQUIRED, pass in idrac IP
   - idrac_username, REQUIRED, pass in idrac user name
   - idrac_password, REQUIRED, pass in idrac password
   - password_type, REQUIRED, Set, Change or Delete BIOS password, pass in the type of password you want to change. Supported values are: Sys or Setup. NOTE: Make sure to pass in exact string value as listed (case sensitive values)
   - old_password, OPTIONAL, Change BIOS password, pass in the old password. If you are setting new password, pass in '""' for value
   - new_password, OPTIONAL, Change BIOS password, pass in the new password. If you are clearing the password, pass in '""' for value
   
.EXAMPLE
	This example shows set BIOS system password
    Set-BiosChangePasswordREDFISH idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -password_type Sys -old_password '""' -new_password p@ssw0rd
.EXAMPLE
	This example shows change BIOS system password
    Set-BiosChangePasswordREDFISH idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -password_type Sys -old_password p@ssw0rd -new_password newPassW0rd
.EXAMPLE
	This example shows delete BIOS setup password
    Set-BiosChangePasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -password_type Setup -old_password p@ssw0rd -new_password '""'
#>

function Set-BiosChangePasswordREDFISH {





param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$password_type,
    [Parameter(Mandatory=$True)]
    [string]$old_password,
    [Parameter(Mandatory=$True)]
    [string]$new_password
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



Ignore-SSLCertificates


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)

# Function to check supported iDRAC version

function check_supported_idrac_version
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    catch
    {
    }
	    if ($result.StatusCode -ne 200)
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API"
	    return
	    }
	    else
	    {
	    }
return
}

check_supported_idrac_version

# Compile hash table and execute POST command to either set, change or delete BIOS password

$u2 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ChangePassword/"
if ($old_password -eq '""')
    {
    $JsonBody = @{"PasswordName"= $password_type+"Password";"OldPassword" = ""; "NewPassword" = $new_password} | ConvertTo-Json -Compress
    }
elseif ($new_password -eq '""')
    {
    $JsonBody = @{"PasswordName"= $password_type+"Password";"OldPassword" = $old_password; "NewPassword" = ""} | ConvertTo-Json -Compress
    }
else
    {
    $JsonBody = @{"PasswordName"= $password_type+"Password";"OldPassword" = $old_password; "NewPassword" = $new_password} | ConvertTo-Json -Compress
    }

try
{
$result1 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}


if ($result1.StatusCode -eq 200)
{
if ($old_password -eq '""')
    {
[String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to SET '{1}' password",$result1.StatusCode, $password_type)
    if ($password_type -eq "Sys")
        {
        Write-Host
        Write-Host "- WARNING, after task completes in Automated task Application to set System password, you will be prompted in POST to enter the new System password. You must do this for the server to complete POST and mark the job ID completed"
        Write-Host
    }
    }
elseif ($new_password -eq '""')
    {
[String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to DELETE '{1}' password",$result1.StatusCode, $password_type)
    }
else
    {
[String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to CHANGE '{1}' password",$result1.StatusCode, $password_type)
    if ($password_type -eq "Sys")
        {
        Write-Host
        Write-Host "- WARNING, after task completes in Automated task Application to set System password, you will be prompted in POST to enter the new System password. You must do this for the server to complete POST and mark the job ID completed"
        Write-Host
    }
    }
}
else
{
Write-Host "`n- FAIL, unable to $password_change $password_type password, status code $result1.StatusCode returned"
}

# POST command to create BIOS config job

$JsonBody = @{ "TargetSettingsURI" ="/redfish/v1/Systems/System.Embedded.1/Bios/Settings"
    } | ConvertTo-Json -Compress


$u2 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"


$result1 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$raw_content=$result1.RawContent | ConvertTo-Json -Compress
$jobID_search=[regex]::Match($raw_content, "JID_.+?r").captures.groups[0].value
$job_id=$jobID_search.Replace("\r","")
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


$u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to check job status of scheduled before rebooting the server

$result = Invoke-WebRequest -Uri $u3 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
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
Exit
}


$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power OFF the server

$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}


if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power OFF the server",$result1.StatusCode)
    Start-Sleep 30
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
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
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
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to loop query the job status until marked completed or failed

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

}

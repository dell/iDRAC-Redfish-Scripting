
<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 3.0

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
  Cmdlet used to import server configuration profile (SCP) locally using a SCP configuration file with Redfish API.
.DESCRIPTION
   Cmdlet used to import server configuration profile locally with SCP configuration file using Redfish API. 
   - idrac_ip (iDRAC IP) REQUIRED
   - idrac_username (iDRAC user name) REQUIRED
   - idrac_password (iDRAC user name password) REQUIRED
   - FileName (Pass in the filename of the SCP configuration file) REQUIRED
   - Target (Supported values: ALL, RAID, BIOS, iDRAC, NIC, FC, LifecycleController, System, Alerts. Pass in the related component name for the attributes you are trying to set. Or just pass in ALL to handle any type of attributes you are trying to configure) REQUIRED
   - ShutdownType (Supported Values: Graceful, Forced, NoReboot. If this parameter is not passed in, default value is Graceful) OPTIONAL
   - HostPowerState (Supported Values: On, Off. If this parameter is not passed in, default value is On) OPTIONAL
   

.EXAMPLE
   Set-ImportServerConfigurationProfileLocalFilenameREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target ALL -FileName 03212018-213336_scp_file.xml
   This example will set ALL attributes that have a configuration change detected in local the SCP file.
.EXAMPLE
   Set-ImportServerConfigurationProfileLocalFilenameREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target "BIOS,iDRAC" -ShutdownType Forced -FileName 03212018-213336_scp_file.xml
   This example will perform forced shutdown, set iDRAC and BIOS attributes only from the local SCP file.
#>

function Set-ImportServerConfigurationProfileLocalFilenameREDFISH {


param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$True)]
    $idrac_username,
    [Parameter(Mandatory=$True)]
    $idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$Target,
    [Parameter(Mandatory=$False)]
    [string]$ShutdownType,
    [Parameter(Mandatory=$False)]
    [string]$HostPowerState,
    [Parameter(Mandatory=$True)]
    [string]$FileName
    )


$SCP_file = Get-Content $FileName

$share_info = @{"ImportBuffer"=[string]$SCP_file;"ShareParameters"=@{"Target"=$Target}}


if ($ShutdownType)
{
$share_info["ShutdownType"] = $ShutdownType
}
if ($HostPowerState)
{
$share_info["HostPowerState"] = $HostPowerState
}

$JsonBody = $share_info | ConvertTo-Json -Compress



# Function to igonre SSL certs

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

$global:get_powershell_version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

get_powershell_version

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


$full_method_name="EID_674_Manager.ImportSystemConfiguration"

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"


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
$get_result = $result1.RawContent | ConvertTo-Json
$search_jobid = [regex]::Match($get_result, "JID_.+?r").captures.groups[0].value
$job_id = $search_jobid.Replace("\r","")

if ($result1.StatusCode -eq 202)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned to successfully create import server configuration profile (SCP) job: {1}",$result1.StatusCode,$job_id)
    Write-Host
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)


while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
if ($overall_job_output.JobState -eq "Failed") {
Write-Host
[String]::Format("- FAIL, final job status is: {0}, no configuration changes were applied",$overall_job_output.JobState)

if ($overall_job_output.Message -eq "The system could not be shut down within the specified time.")
{
[String]::Format("- FAIL, 10 minute default shutdown timeout reached, final job message is: {0}",$overall_job_output.Message)
return
}
else 
{
[String]::Format("- FAIL, final job message is: {0}",$overall_job_output.Message)
return
}
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}
elseif ($overall_job_output.Message -eq "Import of Server Configuration Profile operation completed with errors.") {
Write-Host
[String]::Format("- WARNING, final job status is: {0}",$overall_job_output.Message)
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
Write-Host "`n- Detailed final job status and configuration results for import job ID '$job_id' -`n"

$get_final_results = [string]$result.Content 
$get_final_results.Split(",")
return
}
elseif ($overall_job_output.JobState -eq "Completed") {
break
}
else {
[String]::Format("- WARNING, import job ID not marked completed, current job status: {0}",$overall_job_output.Message)
Start-Sleep 10
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
$final_message = $overall_job_output.Message
if ($final_message.Contains("No changes were applied"))
{
[String]::Format("`n- Final job status is: {0}",$overall_job_output.Message)
return
}

$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "  Job completed in $final_completion_time"

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
Write-Host "`n- Detailed final job status and configuration results for import job ID '$job_id' -`n"

$get_final_results = [string]$result.Content 
$get_final_results.Split(",")
break

}

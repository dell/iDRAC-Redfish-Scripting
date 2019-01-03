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
  Cmdlet used to import server configuration profile (SCP) locally using Redfish API.
.DESCRIPTION
   Cmdlet used to import server configuration profile locally using Redfish API. Before executing the cmdlet, first edit $share_info hashtable with the attributes you want to set. Make sure to follow the correct format as it shows in current hashtable.
   - idrac_ip (iDRAC IP) REQUIRED
   - idrac_username (iDRAC user name) REQUIRED
   - idrac_password (iDRAC user name password) REQUIRED
   - Target (Supported values: ALL, RAID, BIOS, iDRAC, NIC, FC, LifecycleController, System, Alerts. Once you edit the hashtable for the attributes you want to set, pass in the related component name for Target or pass in All) REQUIRED
   - ShutdownType (Supported Values: Graceful, Forced, NoReboot. If this parameter is not passed in, default value is Graceful) OPTIONAL
   - HostPowerState (Supported Values: On, Off. If this parameter is not passed in, default value is On) OPTIONAL
   

.EXAMPLE
   Set-ImportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target iDRAC
   This example will set iDRAC attributes you passed in the $share_info hashtable
.EXAMPLE
   Set-ImportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target "BIOS,iDRAC" -ShutdownType Forced
   This example will perform forced shutdown, set iDRAC and BIOS attributes you passed in the $share_info hashtable
#>

function Set-ImportServerConfigurationProfileLocalREDFISH {


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
    [string]$HostPowerState
    )

# Hashtable you must edit first with the attributes you want to configure on the server. Make sure to use exact XML format in the string value for ImportBuffer key.

$share_info = @{"ImportBuffer"="<SystemConfiguration><Component FQDD='iDRAC.Embedded.1'><Attribute Name='Telnet.1#Enable'>Enabled</Attribute><Attribute Name='Telnet.1#Port'>24</Attribute></Component></SystemConfiguration>";"ShareParameters"=@{"Target"=$Target}}

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

Ignore-SSLCertificates

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


$full_method_name="EID_674_Manager.ImportSystemConfiguration"

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"

# POST command to import or export server configuration profile file

try
{
$result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$q=$result1.RawContent | ConvertTo-Json
$j=[regex]::Match($q, "JID_.+?r").captures.groups[0].value
$job_id=$j.Replace("\r","")

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
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}

$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.JobState -eq "Failed") 
{
Write-Host
[String]::Format("- FAIL, final job status is: {0}",$overall_job_status.JobState)
Return
}
if ($overall_job_output.Message -eq "The system could not be shut down within the specified time.")
{
[String]::Format("- FAIL, 10 minute default shutdown timeout reached, final job message is: {0}",$overall_job_output.Message)
return
}

if ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}
if ($overall_job_output.Message -eq "Import of Server Configuration Profile operation completed with errors." -or $overall_job_output.Message -eq "Unable to complete application of configuration profile values.") 
{
$u5 ="https://$idrac_ip/redfish/v1/TaskService/Tasks/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
Write-Host "- WARNING, failure detected for import job id '$job_id'. Check 'Messages' property below for more information on the failure."
$result.Content | ConvertFrom-Json

return
}
if ($overall_job_output.Message -eq "No changes were applied since the current component configuration matched the requested configuration.")
{
Write-Host "- WARNING, import job id '$job_id' completed. No changes were applied since the current component configuration matched the requested configuration."
return
}
if ($overall_job_output.Message -eq "No reboot Server Configuration Profile Import job scheduled, Waiting for System Reboot to complete the operation.")
{
Write-Host "- WARNING, ShutdownType NoReboot selected. Configuration changes will not be applied until next server manual reboot"
return
}


Write-Host "- Import job id '$job_id' successfully completed. Detailed final job status results -`n"
$u6 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result6 = Invoke-WebRequest -Uri $u6 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$result6.Content | ConvertFrom-Json


}
}



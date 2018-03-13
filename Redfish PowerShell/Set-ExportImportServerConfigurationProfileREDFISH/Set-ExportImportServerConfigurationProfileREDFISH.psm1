<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0

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
  Cmdlet used to export or import server configuration profile to network share
.DESCRIPTION
   Cmdlet used to export or import server configuration profile or SCP. It will call either ExportSystemConfiguration or ImportSystemConfiguration method.
   - idrac_ip (iDRAC IP) REQUIRED
   - idrac_username (iDRAC user name) REQUIRED
   - idrac_password (iDRAC user name password) REQUIRED
   - Method (Supported values: Export or Import) REQUIRED
   - network_share_IPAddress (Supported value: IP address of your network share) REQUIRED
   - ShareName (Supported value: Name of your network share) REQUIRED
   - ShareType (Supported values: NFS, CIFS, HTTP and HTTPS) REQUIRED
   - FileName (Supported value: Pass in a name of the exported or imported file) REQUIRED
   - Username (Supported value: Name of your username that has access to CIFS share) REQUIRED only for CIFS
   - Password (Supported value: Name of your user password that has access to CIFS share) REQUIRED only for CIFS
   - Target (Supported values: ALL, RAID, BIOS, iDRAC, NIC, FC, LifecycleController, System, Alerts) REQUIRED
   - ExportFormat (supported values: XML or JSON) REQUIRED for Export only
   - ExportUse (Supported values: Default, Clone and Replace) OPTIONAL for export only. If not passed in, value will be "Default" used.
   - ShutdownType (Supported values: Graceful, Forced and NoReboot) OPTIONAL, only valid for import, if you don't pass in this parameter, default value will be"Graceful"
  
  NOTE: For parameter values with static strng values, make sure you pass in the exact text since these are case senstive values. Example: For ExportUse, pass in a value of "Clone.
  Passing in a value of "clone" will fail.

.EXAMPLE
   Set-ExportImportServerConfigurationProfile -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Method export -IPAddress 192.168.0.130 -ShareType NFS -ShareName /nfs_tex -FileName export_ps.xml
.EXAMPLE
   Set-ExportImportServerConfigurationProfile -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Method import -IPAddress 192.168.0.130 -ShareType CIFS -ShareName cifs -Username administrator - Password password -Target RAID -FileName export_ps.xml
#>

function Set-ExportImportServerConfigurationProfileREDFISH {

param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$True)]
    $idrac_username,
    [Parameter(Mandatory=$True)]
    $idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$Method,
    [Parameter(Mandatory=$True)]
    [string]$Target,
    [Parameter(Mandatory=$True)]
    [string]$ShareType,
    [Parameter(Mandatory=$True)]
    [string]$ShareName,
    [Parameter(Mandatory=$True)]
    [string]$network_share_IPAddress,
    [Parameter(Mandatory=$True)]
    [string]$FileName,
    [Parameter(Mandatory=$False)]
    [string]$cifs_username,
    [Parameter(Mandatory=$False)]
    [string]$cifs_password,
    [Parameter(Mandatory=$False)]
    [string]$ExportUse,
    [Parameter(Mandatory=$False)]
    [string]$ExportFormat,
    [Parameter(Mandatory=$False)]
    [string]$ShutdownType
    )

# Building the hash table for export or import operation

$method=(Get-Culture).textinfo.totitlecase($method.tolower())

if ($ShareType -eq "NFS" -or $ShareType -eq "HTTP" -or $ShareType -eq "HTTPS" -and $Method -eq "Export")
{
$share_info=@{"ExportFormat"=$ExportFormat;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName}}
}

if ($ShareType -eq "NFS" -or $ShareType -eq "HTTP" -or $ShareType -eq "HTTPS" -and $Method -eq "Export" -and $ExportUse)
{
$share_info=@{"ExportFormat"=$ExportFormat;"ExportUse"=$ExportUse;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName}}
}


if ($ShareType -eq "NFS" -or $ShareType -eq "HTTP" -or $ShareType -eq "HTTPS" -and $Method -eq "Import")
{
$share_info=@{"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName}}
}

if ($ShareType -eq "NFS" -or $ShareType -eq "HTTP" -or $ShareType -eq "HTTPS" -and $Method -eq "Import" -and $ShutdownType)
{
$share_info=@{"ShutdownType"=$ShutdownType;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName}}
}

if ($ShareType -eq "CIFS" -and $Method -eq "Export")
{ 
$share_info=@{"ExportFormat"=$ExportFormat;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName;"UserName"=$cifs_username;"Password"=$cifs_password}}
}

if ($ShareType -eq "CIFS" -and $Method -eq "Export" -and $ExportUse)
{ 
$share_info=@{"ExportFormat"=$ExportFormat;"ExportUse"=$ExportUse;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName;"UserName"=$cifs_username;"Password"=$cifs_password}}
}

if ($ShareType -eq "CIFS" -and $Method -eq "Import")
{
$share_info=@{"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName;"UserName"=$cifs_username;"Password"=$cifs_password}}
}

if ($ShareType -eq "CIFS" -and $Method -eq "Import" -and $ShutdownType)
{
$share_info=@{"ShutdownType"=$ShutdownType;"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName;"UserName"=$cifs_username;"Password"=$cifs_password}}
}

Write-Host
Write-Host "- WARNING, Parameter details for $Method operation"
$share_info 
Write-Host
Write-Host "ShareParameters details:"
Write-Host
$share_info.ShareParameters

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


$full_method_name="EID_674_Manager."+$Method +"SystemConfiguration"

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"

# POST command to import or export server configuration profile file

$result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'
$raw_content_output=$result1.RawContent | ConvertTo-Json -Compress
$job_id_search=[regex]::Match($raw_content_output, "JID_.+?r").captures.groups[0].value
$job_id=$job_id_search.Replace("\r","")

if ($result1.StatusCode -eq 202)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned to successfully create job: {1}",$result1.StatusCode,$job_id)
    Write-Host
    Start-Sleep 5
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$overall_job_output=""

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)

if ( $ShutdownType -eq "NoReboot")
{
while ($overall_job_output.Message -ne "No reboot Server Configuration Profile Import job scheduled, Waiting for System Reboot to complete the operation.")
{
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobState -eq "Failed") {
Write-Host
[String]::Format("- FAIL, final job status is: {0}, no configuration changes were applied",$overall_job_output.JobState)
return
}
else {
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
}
}
Write-Host
Write-Host "- WARNING, NoReboot passed in for ShutdownType, no configuration changes will be applied until next server reboot"
Write-Host
return
}



while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
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
[String]::Format("- WARNING, final job status is: {0} Check configuration results for more information",$overall_job_output.Message)
return
}
elseif ($overall_job_output.JobState -eq "Completed") {
break
}
else {
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 5
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
[String]::Format("- Final job status is: {0}",$overall_job_output.Message)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "  Job completed in $final_completion_time"
return

}

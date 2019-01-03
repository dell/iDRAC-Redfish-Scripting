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
  Cmdlet used to preview import server configuration profile file
.DESCRIPTION
   Cmdlet used to execute import preview. It will execute ImportSystemConfigurationPreview method.
   - idrac_ip (iDRAC IP) REQUIRED
   - idrac_username (iDRAC user name) REQUIRED
   - idrac_password (iDRAC user name password) REQUIRED
   - network_share_IPAddress (Supported value: IP address of your network share) REQUIRED
   - ShareName (Supported value: Name of your network share) REQUIRED
   - ShareType (Supported values: NFS, CIFS, HTTP and HTTPS) REQUIRED
   - FileName (Supported value: Pass in a name of the exported or imported file) REQUIRED
   - Username (Supported value: Name of your username that has access to CIFS share) REQUIRED only for CIFS
   - Password (Supported value: Name of your user password that has access to CIFS share) REQUIRED only for CIFS
   - Target (Supported values: ALL, RAID, BIOS, iDRAC, NIC, FC, LifecycleController, System, Alerts) REQUIRED
  
  

.EXAMPLE
   Set-ImportServerConfigurationProfilePreviewREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -IPAddress 192.168.0.130 -ShareType NFS -ShareName /nfs_tex -FileName export_ps.xml
   # This example shows executing import preivew on a configuration file which has already been eported to NFS share.
   #>

function Get-ImportServerConfigurationProfilePreviewREDFISH {

param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$True)]
    $idrac_username,
    [Parameter(Mandatory=$True)]
    $idrac_password,
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
    [Parameter(Mandatory=$True)]
    [string]$Target
    )


if ($ShareType -eq "NFS" -or $ShareType -eq "HTTP" -or $ShareType -eq "HTTPS")
{
$share_info=@{"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName}}
}

if ($ShareType -eq "CIFS")
{ 
$share_info=@{"ShareParameters"=@{"Target"=$Target;"IPAddress"=$network_share_IPAddress;"ShareName"=$ShareName;"ShareType"=$ShareType;"FileName"=$FileName;"UserName"=$cifs_username;"Password"=$cifs_password}}
}


Write-Host
Write-Host "- WARNING, Parameter details for import preview operation"
$share_info
Write-Host
Write-Host "ShareParameters details:"
Write-Host
$share_info.ShareParameters

$JsonBody = $share_info | ConvertTo-Json -Compress


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

$full_method_name="EID_674_Manager.ImportSystemConfigurationPreview"

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"

# POST command to import preview configuration file

$result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$raw_content=$result1.RawContent | ConvertTo-Json -Compress
$job_id_search=[regex]::Match($raw_content, "JID_.+?r").captures.groups[0].value
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
$end_time = $start_time.AddMinutes(10)

# While loop to query the job status until marked completed

while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
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
Write-Host "- FAIL, timeout of 10 minutes has been reached before marking the job completed"
return
}
elseif ($overall_job_output.JobState -eq "Completed") 
{
break
}
else 
{
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 2
}
}
Write-Host
[String]::Format("- {0} job ID marked as completed",$job_id)
[String]::Format("- Final job status is: {0}",$overall_job_output.Message)
}



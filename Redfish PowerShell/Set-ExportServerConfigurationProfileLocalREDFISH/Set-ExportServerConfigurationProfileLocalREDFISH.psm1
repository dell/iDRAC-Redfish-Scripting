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
  Cmdlet used to export server configuration profile (SCP) locally using Redfish API.
.DESCRIPTION
   Cmdlet used to export server configuration profile locally using Redfish API. It will display the attributes locally to the screen along with copying them to a file.
   - idrac_ip (iDRAC IP) REQUIRED
   - idrac_username (iDRAC user name) REQUIRED
   - idrac_password (iDRAC user name password) REQUIRED
   - Target (Supported values: ALL, RAID, BIOS, iDRAC, NIC, FC, LifecycleController, System, Alerts) REQUIRED
   - ExportUse (Supported values: Default, Clone and Replace) OPTIONAL. Note: If argument not used, value of "Default" will be used for export.
   

.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target ALL
   This example will export ALL server component attributes locally to the screen and copy them to a file.
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target "RAID,BIOS"
   This example will export only RAID and BIOS server component attributes locally to the screen and copy them to a file.
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target RAID -ExportUse Clone
   This example will perform a clone export and export only RAID component attributes locally to the screen and copy them to a file.
#>

function Set-ExportServerConfigurationProfileLocalREDFISH {

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
    [string]$ExportUse
    )


$ExportFormat = "XML"

$share_info=@{"ExportFormat"=$ExportFormat;"ShareParameters"=@{"Target"=$Target}}

if ($ExportUse -ne "")
{
$share_info["ExportUse"] = $ExportUse
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


$full_method_name="EID_674_Manager.ExportSystemConfiguration"
$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"

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
    [String]::Format("- PASS, statuscode {0} returned to successfully create export server configuration profile (SCP) job: {1}",$result1.StatusCode,$job_id)
    Write-Host
    #Start-Sleep 5
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(5)

while ($overall_job_output.JobState -ne "Complete")
{
$loop_time = Get-Date

$u5 ="https://$idrac_ip/redfish/v1/TaskService/Tasks/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}

try
{
$overall_job_status=$result.Content | ConvertFrom-Json
}
catch
{
}
$overall_job_output=$result.Content
$u6 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result6 = Invoke-WebRequest -Uri $u6 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$result6.Content | ConvertFrom-Json         
if ($overall_job_status.TaskState -eq "Failed") {
Write-Host
[String]::Format("- FAIL, final job status is: {0}",$overall_job_status.TaskState)
Return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 5 minutes has been reached before marking the job completed"
Return
}
elseif ($overall_job_output.Contains("SystemConfiguration")) {
Write-Host "`n- Exported server attributes for target '$Target' -`n"
$overall_job_output
$s=Get-Date
$s=[string]$s
$s=$s.Replace("/","")
$s=$s.Replace(":","")
$s=$s.Replace(" ","-")
$filename = $s+"_scp_file."+$ExportFormat.ToLower()

Add-Content $filename $overall_job_output
Write-Host "`n- WARNING, SCP exported attributes also copied to '$filename' file" -ForegroundColor Yellow
Write-Host "`n- Detailed Final Job Status Results -`n"
$u6 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result6 = Invoke-WebRequest -Uri $u6 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$result6.Content | ConvertFrom-Json
break
}
else 
{
}
}

}



<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 11.0

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
  iDRAC cmdlet used to export server configuration profile (SCP) locally using Redfish API.
.DESCRIPTION
   iDRAC cmdlet used to export server configuration profile locally using Redfish API. It will display the attributes locally to the screen along with copying them to a file. For more details on SCP feature, refer to document "https://downloads.dell.com/Manuals/Common/dellemc-server-config-profile-refguide.pdf"
   - idrac_ip: pass in iDRAC IP. 
   - idrac_username: pass in iDRAC user name 
   - idrac_password: pass in iDRAC user name password 
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - Target: Supported values: ALL, RAID, BIOS, IDRAC, NIC, FC, LifecycleController, System, EventFilters
   - ExportUse: Supported values: Default, Clone and Replace. Note: If argument not used, value of default will be used.
   - IncludeInExport: Supported values: Default, IncludeReadOnly, IncludePasswordHashValue, 'IncludeReadOnly,IncludePasswordHashValues' and IncludeCustomTelemetry. Note: If argument not used, value of default will be used.
   - ExportFormat: Supported values: XML and JSON. Note: If argument not used, default value of XML will be used. 
   

.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target ALL
   This example will perform default export for ALL server component attributes locally to the screen and copy them to a file in XML format.
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -Target ALL -ExportFormat JSON -ExportUse Clone
   This example will first prompt to enter iDRAC credentials using Get-Credential, then perform clone export for ALL server component attributes locally to the screen and copy them to a file in JSON format.
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -Target ALL -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   This example will perform default export for ALL server component attributes locally to the screen and copy them to a file in XML format using iDRAC X-auth token session. 
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target "RAID,BIOS" -IncludeInExport IncludeReadOnly
   This example will perform default export for only RAID and BIOS server component attributes and also get read only attributes, echo locally to the screen and copy them to a file in XML format.
.EXAMPLE
   Set-ExportServerConfigurationProfileLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -Target "RAID,IDRAC" -ExportUse Clone -IncludeInExport "IncludeReadOnly,IncludePasswordHashValues" - ExportFormat JSON
   This example will perform a clone export and export only RAID and IDRAC component attributes along with read only attributes, password hashes, echo locally to the screen and copy them to a file in JSON format.
#>

function Set-ExportServerConfigurationProfileLocalREDFISH {

param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$False)]
    $idrac_username,
    [Parameter(Mandatory=$False)]
    $idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$Target,
    [ValidateSet("Default", "Clone", "Replace")]
    [Parameter(Mandatory=$False)]
    [string]$ExportUse,
    [ValidateSet("IncludeReadOnly", "IncludePasswordHashValues", "IncludeReadOnly,IncludePasswordHashValues", "IncludeCustomTelemetry")]
    [Parameter(Mandatory=$False)]
    [string]$IncludeInExport,
    [ValidateSet("XML", "JSON")]
    [Parameter(Mandatory=$False)]
    [string]$ExportFormat,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token
    )




$export_parameters = @{"ExportFormat"=$ExportFormat;"ShareParameters"=@{"Target"=@($Target)}}

if ($ExportFormat)
{
$export_parameters["ExportFormat"] = $ExportFormat
}
else
{
$export_parameters["ExportFormat"] = "XML"
$ExportFormat = "XML"
}

if ($ExportUse)
{
$export_parameters["ExportUse"] = $ExportUse
}

if ($IncludeInExport)
{
$export_parameters["IncludeInExport"] = $IncludeInExport
}

$JsonBody = $export_parameters | ConvertTo-Json -Compress

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

$global:get_powershell_version = $null

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

get_powershell_version 


function setup_idrac_creds
{

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12

if ($x_auth_token)
{
$global:x_auth_token = $x_auth_token
}
elseif ($idrac_username -and $idrac_password)
{
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}
else
{
    if ($idrac_username)
    {
    $get_creds = Get-Credential -Message "Enter $idrac_username password to run cmdlet" -UserName $idrac_username
    $global:credential = New-Object System.Management.Automation.PSCredential($get_creds.UserName, $get_creds.Password)
    }
    else
    {
    $get_creds = Get-Credential -Message "Enter iDRAC username and password to run cmdlet"
    $global:credential = New-Object System.Management.Automation.PSCredential($get_creds.UserName, $get_creds.Password)
    }
}
}
setup_idrac_creds

function get_iDRAC_version
{

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1?`$select=Model"


if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
if ($get_content.Model.Contains("12G") -or $get_content.Model.Contains("13G") -or $get_content.Model.Contains("14G") -or $get_content.Model.Contains("15G") -or $get_content.Model.Contains("16G"))
{
$global:iDRAC_version = "old"
}
else
{
$global:iDRAC_version = "new"
}
}

get_iDRAC_version


if ($global:iDRAC_version -eq "old")
{
$full_method_name="EID_674_Manager."+"ExportSystemConfiguration"
}
else
{
$full_method_name="OemManager."+"ExportSystemConfiguration"
}
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/$full_method_name"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


else
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

$get_job_id_location = $result1.Headers.Location
if ($get_job_id_location.Count -gt 0 -eq $true)
{
}
else
{
[String]::Format("`n- FAIL, unable to locate job ID in Headers output. Check to make sure you passed in correct Target value")
return
}

$get_result = $result1.RawContent | ConvertTo-Json
$job_id_search = [regex]::Match($get_result, "JID_.+?r").captures.groups[0].value
$job_id = $job_id_search.Replace("\r","")
$get_job_id_location = $result1.Headers.Location

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
$job_uri ="https://$idrac_ip$get_job_id_location"



if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}




try
{
$overall_job_status=$result.Content | ConvertFrom-Json
}
catch
{
}
$overall_job_output=$result.Content
$job_uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}
$get_result.Content | ConvertFrom-Json         
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
$get_date_string = Get-Date
$get_date_string = [string]$get_date_string
$get_date_string = $get_date_string.Replace("/","")
$get_date_string = $get_date_string.Replace(":","")
$get_date_string = $get_date_string.Replace(" ","-")
$filename = $get_date_string+"_scp_file."+$ExportFormat.ToLower()

Add-Content $filename $overall_job_output
Write-Host "`n- WARNING, SCP exported attributes also copied to '$filename' file" -ForegroundColor Yellow
Write-Host "`n- Detailed Final Job Status Results -`n"
$job_uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $job_uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}
$get_result.Content | ConvertFrom-Json
return
}
else 
{
}
}

}






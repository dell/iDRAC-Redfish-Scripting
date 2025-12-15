<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 11.0

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
   iDRAC cmdlet used to get complete iDRAC lifecycle logs 
.DESCRIPTION
   iDRAC cmdlet using Redfish API with OEM extension to get complete iDRAC Lifecycle logs, echo to the screen. NOTE: Recommended to redirect output to a file due to large amount of data returned.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended).
   - get_all: Pass in this argument to get all iDRAC LC logs
   - get_severity: Get only specific severity entries from LC logs. Supported values: informational, warning or critical
   - get_date_range: Get only specific entries within a given date range from LC logs. You must also use arguments --start-date and --end-date to create the filter date range. NOTE: This is only supported for iDRAC9. 
   - start_date: Pass in the start date, time for the date range of LC log entries. Value must be in this format: YYYY-MM-DDTHH:MM:SS-offset (example: 2023-03-14T10:10:10-05:00). Note: If needed run --get-all argument to dump all LC logs, look at Created property to get your date time format.
   - end_date: Pass in the end date, time for the date range of LC log entries. Value must be in this format: YYYY-MM-DDTHH:MM:SS-offset (example: 2023-03-15T14:55:10-05:00)
   - get_message_id: Get only entries for a specific message ID. To get the correct message ID string format to pass in use argument -get_all to return complete LC logs. Examples of correct message string ID value to pass in: IDRAC.2.9.PDR1001, IDRAC.2.9.LC011. Note: You can also pass in an abbreviated message ID value, example: IDRAC.2.9.LC which will return any message ID that starts with LC.
   - get_category: Get LC log entries from only a specific category. Supported values: audit, configuration, updates, systemhealth or storage. NOTE: This argument is only supported on iDRAC9 or newer.
.EXAMPLE
   Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_all
   This example will get complete iDRAC Lifecycle Logs, echo output to the screen.
.EXAMPLE
   Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -get_all
   This example will first prompt to enter username, password using Get-Credential, then execute getting LC logs. 
.EXAMPLE
   Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -x_auth_token 163490d51b708f8dc24ca853ef2fc6e7 -get_all
   This example will get complete iDRAC Lifecycle Logs using X-auth token session.
.EXAMPLE
   Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_all >  R640_iDRAC_LC_logs.txt
   This example will get complete iDRAC Lifecycle Logs and redirect output to a file.
.EXAMPLE
    Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_category updates
    This example will return only update category entries from the LC logs on iDRAC9.
.EXAMPLE
    Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_message_id IDRAC.2.9.CTL129
    This example will return only LC log entries with message ID IDRAC.2.9.CTL129.
.EXAMPLE
    Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_date_range -start_date "2023-09-26T13:29:51-05:00" -end_date "2023-09-28T14:02:11-05:00"
    This example will return only LC logs which happended during start and end dates passed in as arguments for iDRAC9. 
#>

function Get-IdracLifecycleLogsREDFISH {

param(
    [Parameter(Mandatory=$False)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$False)]
    [string]$idrac_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [Parameter(Mandatory=$False)]
    [switch]$get_all,
    [ValidateSet("critical", "warning", "informational")]
    [Parameter(Mandatory=$False)]
    [string]$get_severity,
    [Parameter(Mandatory=$False)]
    [switch]$get_date_range,
    [Parameter(Mandatory=$False)]
    [string]$start_date,
    [Parameter(Mandatory=$False)]
    [string]$end_date,
    [Parameter(Mandatory=$False)]
    [string]$get_message_id,
    [ValidateSet("audit", "configuration", "updates", "systemhealth", "storage")]
    [Parameter(Mandatory=$False)]
    [string]$get_category
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
if ($get_content.Model.Contains("12G") -or $get_content.Model.Contains("13G"))
{
$global:iDRAC_version_uri = "redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog"
$global:iDRAC_version = "old"
}
else
{
$global:iDRAC_version_uri = "redfish/v1/Managers/iDRAC.Embedded.1/LogServices/Lclog/Entries"
$global:iDRAC_version = "new"
}
}

get_iDRAC_version

function get_all_LC_logs
{

Write-Host -ForegroundColor Green "`n- INFO, getting Lifecycle Logs for iDRAC $idrac_ip. This may take a few minutes to complete depending on log file size`n"
Start-Sleep 2
$next_link_value = 0

while ($true)
{
$skip_uri ="?"+"$"+"skip="+$next_link_value
$uri = "https://$idrac_ip/{0}$skip_uri" -f ($global:iDRAC_version_uri)


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
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
    {
    Write-Host -ForegroundColor Yellow "`n- INFO, cmdlet execution complete. Note: If needed, execute cmdlet again and redirect output to a file."
    break
    }
    else
    {
    Write-Host
    $RespErr
    return
    }
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
    if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
    {
    Write-Host -ForegroundColor Yellow "`n- INFO, cmdlet execution complete. Note: If needed, execute cmdlet again and redirect output to a file."
    break
    }
    else
    {
    Write-Host
    $RespErr
    return
    }
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
$get_content=$result.Content | ConvertFrom-Json
if ($get_content.Members.Count -eq 0)
{
Write-Host -ForegroundColor Green "`n- INFO, cmdlet execution complete. Note: If needed, execute cmdlet again and redirect output to a file."
break
}
else
{
$get_content.Members
$next_link_value = $next_link_value+50
}
}

}

function get_severity_entries_only
{

Write-Host -ForegroundColor Green "`n- INFO, getting only severity $get_severity entries from LC logs. This may take a few minutes to complete depending on LC log size`n"
Start-Sleep 2
$next_link_value = 50

if ($get_severity.ToLower() -eq "informational")
{
$uri = "https://$idrac_ip/{0}?`$filter=Severity eq 'OK'" -f ($global:iDRAC_version_uri)
}
elseif ($get_severity.ToLower() -eq "critical")
{
$uri = "https://$idrac_ip/{0}?`$filter=Severity eq 'Critical'" -f ($global:iDRAC_version_uri)
}
elseif ($get_severity.ToLower() -eq "warning")
{
$uri = "https://$idrac_ip/{0}?`$filter=Severity eq 'Warning'" -f ($global:iDRAC_version_uri)
}
else
{
Write-Host "- INFO, invalid value entered for argument get_severity"
return
}

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
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
$get_content = $result.Content | ConvertFrom-Json
    if ($get_content.Members.Count -eq 0)
    {
    Write-Host -ForegroundColor Yellow "- WARNING, no $get_severity entries detected in LC logs"
    return 
    }
    else
    {
    $get_content.Members
    }
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$next_link_property = "Members@odata.nextLink"
if ($get_content.$next_link_property -ne $null)
    {
    while ($true)
    {
        $severity_string_value = (Get-Culture).textinfo.totitlecase($get_severity.tolower())
        $uri = "https://$idrac_ip/{0}?`$filter=Severity%20eq%20'{1}'&`$skip={2}" -f ($global:iDRAC_version_uri, $severity_string_value, $next_link_value) 
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
                $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
                if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
                {
                return
                }
                else
                {
                $RespErr
                return
                }
            }
        if ($get_content.$next_link_property -eq $null)
        {
        return
        }
        elseif ($result.StatusCode -eq 200)
        {
        $get_content = $result.Content | ConvertFrom-Json
        $get_content.Members
        $next_link_value = $next_link_value+50
        }
        else
        {
        [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
        return
        }
    }

}
else
{
return
}

}

}

function get_date_range_entries_only
{

if ($global:iDRAC_version -eq "old")
{
Write-Host -ForegroundColor Yellow "`n- WARNING, iDRAC7/8 version not supported for this argument"
return
}

Write-Host -ForegroundColor Green "`n- INFO, getting only specific data range from LC logs. This may take a few minutes to complete depending on LC log size`n"
Start-Sleep 2
$next_link_value = 50

$uri = "https://$idrac_ip/{0}?`$filter=Created ge '{1}' and Created le '{2}'" -f ($global:iDRAC_version_uri, $start_date, $end_date)

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
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
$get_content = $result.Content | ConvertFrom-Json
    if ($get_content.Members.Count -eq 0)
    {
    Write-Host -ForegroundColor Yellow "- WARNING, no entries detected in LC logs within that specific date range"
    return 
    }
    else
    {
    $get_content.Members
    }
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$next_link_property = "Members@odata.nextLink"
if ($get_content.$next_link_property -ne $null)
    {
    while ($true)
    {
        $uri = "https://$idrac_ip/{0}?`$filter=Created ge '{1}' and Created le '{2}'&`$skip={3}" -f ($global:iDRAC_version_uri, $start_date, $end_date, $next_link_value)
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
                $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
                if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
                {
                return
                }
                else
                {
                $RespErr
                return
                }
            }
        if ($get_content.$next_link_property -eq $null)
        {
        return
        }
        elseif ($result.StatusCode -eq 200)
        {
        $get_content = $result.Content | ConvertFrom-Json
        $get_content.Members
        $next_link_value = $next_link_value+50
        }
        else
        {
        [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
        return
        }
    }

}
else
{
return
}

}

}

function get_message_id_entries_only
{

Write-Host -ForegroundColor Green "`n- INFO, getting only message ID $get_message_id entries from LC logs. This may take a few minutes to complete depending on LC log size`n"
Start-Sleep 2
$next_link_value = 50


$uri = "https://$idrac_ip/{0}?`$filter=MessageId eq '{1}'" -f ($global:iDRAC_version_uri, $get_message_id)


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
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
$get_content = $result.Content | ConvertFrom-Json
    if ($get_content.Members.Count -eq 0)
    {
    Write-Host -ForegroundColor Yellow "- WARNING, no entries detected in LC logs for this specific message ID"
    return 
    }
    else
    {
    $get_content.Members
    }
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$next_link_property = "Members@odata.nextLink"
if ($get_content.$next_link_property -ne $null)
    {
    while ($true)
    {
        $uri = "https://$idrac_ip/{0}?`$filter=MessageId eq '{1}'&`$skip={2}" -f ($global:iDRAC_version_uri, $get_message_id, $next_link_value)
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
                $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
                if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
                {
                return
                }
                else
                {
                $RespErr
                return
                }
            }
        if ($get_content.$next_link_property -eq $null)
        {
        return
        }
        elseif ($result.StatusCode -eq 200)
        {
        $get_content = $result.Content | ConvertFrom-Json
        $get_content.Members
        $next_link_value = $next_link_value+50
        }
        else
        {
        [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
        return
        }
    }

}
else
{
return
}

}

}

function get_category_entries_only
{

if ($global:iDRAC_version -eq "old")
{
Write-Host -ForegroundColor Yellow "`n- WARNING, iDRAC7/8 version not supported for this argument"
return
}

$supported_category_values = @("audit", "configuration", "updates", "systemhealth", "storage")
$locate_entries = "no"

if ($supported_category_values -notcontains $get_category.ToLower())
{
Write-Host -ForegroundColor Yellow "`n- WARNING, incorrect value entered for argument -get_category"
return
}

Write-Host -ForegroundColor Green "`n- INFO, getting '$get_category' category entries from LC logs. This may take a few minutes to complete depending on LC log size`n"
Start-Sleep 2
$next_link_value = 50

$uri = "https://$idrac_ip/{0}" -f ($global:iDRAC_version_uri)

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
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
$get_content = $result.Content | ConvertFrom-Json
    if ($get_content.Members.Count -eq 0)
    {
    Write-Host -ForegroundColor Yellow "- WARNING, no '$get_category' category entries detected in LC logs"
    return 
    }
    foreach ($item in $get_content.Members)
    {
    $category_string = $item.Oem.Dell.Category
        if ($category_string.ToLower() -eq $get_category.ToLower())
        {
        $item
        $locate_entries = "yes"
        }    
    }

}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$next_link_property = "Members@odata.nextLink"

if ($get_content.$next_link_property -ne $null)
    {
    while ($true)
    {
        $uri = "https://$idrac_ip/{0}?`$skip={1}" -f ($global:iDRAC_version_uri, $next_link_value)
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
                $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
                if ([string]$RespErr.Contains("Unable to complete the operation because the value"))
                {
                    if ($locate_entries -eq "no")
                    {
                    Write-Host -ForegroundColor Yellow "- WARNING, no entries detected for category '$get_category'"
                    }
                return
                }
                else
                {
                $RespErr
                return
                }
            }
        if ($get_content.$next_link_property -eq $null)
        {
        return
        }
        elseif ($result.StatusCode -eq 200)
        {
        $get_content = $result.Content | ConvertFrom-Json
            foreach ($item in $get_content.Members)
            {
            $category_string = $item.Oem.Dell.Category
                if ($category_string.ToLower() -eq $get_category.ToLower())
                {
                $item
                $locate_entries = "yes"
                }    
            }
        $next_link_value = $next_link_value+50
        }
        else
        {
        [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
        return
        }
    }

}
else
{
return
}

if ($locate_entries -eq "no")
{
Write-Host -ForegroundColor Yellow "- WARNING, no entries detected for category '$get_category'"
}

}

else
{
return
}


}



if ($get_all)
{
get_all_LC_logs
}

elseif ($get_severity)
{
get_severity_entries_only
}

elseif ($get_date_range -and $start_date -and $end_date)
{
get_date_range_entries_only
}

elseif ($get_message_id)
{
get_message_id_entries_only
}

elseif ($get_category)
{
get_category_entries_only
}

else
{
Write-Host -ForegroundColor Red "- FAIL, either incorrect parameter(s) used or missing required parameters(s), please see help or examples for more information."
}


}







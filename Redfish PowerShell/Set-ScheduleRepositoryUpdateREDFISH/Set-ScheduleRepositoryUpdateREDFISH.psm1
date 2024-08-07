<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 1.0

Copyright (c) 2024, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
  iDRAC cmdlet using Redfish API with OEM extension to schedule a repository update at a future reoccurrence date time.
.DESCRIPTION
   iDRAC cmdlet using Redfish API with OEM extension to schedule a repository update at a future reoccurrence date time.
   - idrac_ip (iDRAC IP)
   - idrac_username (iDRAC user name) 
   - idrac_password (iDRAC user name password) 
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - get: Get current repository update schedule details.
   - get_idrac_time: Get current iDRAC date time. 
   - clear: Clear repository update schedule settings.
   - set: Set repository update schedule settings. Note: Minimum arguments required for set are repeat, time and apply_reboot. 
   - shareip: Pass in the IP address of the network share.
   - sharetype: Pass in the share type of the network share. Supported values are NFS, CIFS, HTTP, HTTPS. NOTE: For HTTP/HTTPS, recommended to use either IIS or Apache webserver.
   - sharename: Pass in the network share name.
   - username: Pass in the auth username for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled.
   - password: Pass in the auth username password for network share. Required for CIFS and optional for HTTP/HTTPS if auth is enabled.
   - workgroup: Pass in the workgroup of your CIFS network share. This argument is optional.
   - ignorecertwarning: Ignore HTTPS certificate check, supported values are Off and On. This argument is only required if using HTTPS for share type.
   - time: Set repository update schedule, pass in time value. Value format: HH:MM, example: \"06:00\".
   - repeat: Specify the number of recurrences of the repository update schedule. Possible values are 1-366.
   - day_of_week: Specify day of week on which the update is scheduled. The possible values are * (Any), Mon, Tue, Wed, Thu, Fri, Sat, Sun. The default value is *. Note: day_of_week and day_of_month are mutually exclusive arguments, only pass in one for setting update schedule.
   - day_of_month: Specify day of month on which the update is scheduled. The possible values are * (Any) or a number between 1-28. The default value is *. Note: day_of_week and day_of_month are mutually exclusive arguments, only pass in one for setting update schedule.
   - week_of_month: Specify week of the month in which the update is scheduled. The possible values are * (Any) or a number between 1 and 4. The default value is *.
   - apply_reboot: Reboot the server immediately to run any scheduled updates detected which need a server reboot to apply. Supported values: NoReboot and RebootRequired.

.EXAMPLE
   Set-ScheduleRepositoryUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get
This example will get current scheduled repository update settings.
.EXAMPLE
   Set-ScheduleRepositoryUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -clear
This example will clear current scheduled repository update settings.
.EXAMPLE
   Set-ScheduleRepositoryUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -set -shareip 192.168.0.130 -sharetype NFS -sharename nfs/T360_repo_new -repeat 1 -time 23:00 -apply_reboot RebootRequired -day_of_month 10
This example will set repository update schedule. It will run at 23:00 on the 10th day of the month and only repeat 1 time. 
.EXAMPLE
   Set-ScheduleRepositoryUpdateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -set -shareip 192.168.0.130 -sharetype HTTP -sharename http_share/T360_repo_new -repeat 5 -time 12:00 -apply_reboot RebootRequired -day_of_week Mon 
This example will set repository update schedule. It will run at 12:00 on every Monday and repeat 5 times.
#>

function Set-ScheduleRepositoryUpdateREDFISH {

param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$False)]
    $idrac_username,
    [Parameter(Mandatory=$False)]
    $idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [Parameter(Mandatory=$False)]
    [switch]$get,
    [Parameter(Mandatory=$False)]
    [switch]$get_idrac_time,
    [Parameter(Mandatory=$False)]
    [switch]$set,
    [Parameter(Mandatory=$False)]
    [switch]$clear,
    [Parameter(Mandatory=$False)]
    [string]$shareip,
    [ValidateSet("NFS", "CIFS", "HTTP", "HTTPS")]
    [Parameter(Mandatory=$False)]
    [string]$sharetype,
    [Parameter(Mandatory=$False)]
    [string]$sharename,
    [Parameter(Mandatory=$False)]
    [string]$username,
    [Parameter(Mandatory=$False)]
    [string]$password,
    [ValidateSet("Off", "On")]
    [Parameter(Mandatory=$False)]
    [string]$ignorecertwarning,
    [Parameter(Mandatory=$False)]
    [string]$time,
    [Parameter(Mandatory=$False)]
    [string]$repeat,
    [Parameter(Mandatory=$False)]
    [string]$day_of_week,
    [Parameter(Mandatory=$False)]
    [string]$day_of_month,
    [Parameter(Mandatory=$False)]
    [string]$week_of_month,
    [ValidateSet("NoReboot", "RebootRequired")]
    [Parameter(Mandatory=$False)]
    [string]$apply_reboot
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

# Function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


# Function Get current repository update schedule details 

function get_update_schedule_details
{
$JsonBody = @{} | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetUpdateSchedule"

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($post_result.StatusCode -eq 200)
{
}
else
{
[String]::Format("- FAIL, POST command failed to GET repository update schedule details, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
break
}
$post_result.Content | ConvertFrom-Json
}

# Function to get current iDRAC time

function get_idrac_time
{

$JsonBody = @{"GetRequest"= $True} | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellTimeService/Actions/DellTimeService.ManageTime"

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 


if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
Write-Host "`n- Current iDRAC date time -`n"
}
else
{
[String]::Format("- FAIL, POST command failed to get current iDRAC time, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
break
}

$post_result = $post_result.Content | ConvertFrom-Json
$post_result.TimeData

}

# Function to clear repository update schedule 

function clear_update_schedule_details
{

# PATCH call to disable auto update LC attribute

$JsonBody = @{"Attributes"=@{"LCAttributes.1.AutoUpdate"="Disabled"}} 
$JsonBody = $JsonBody | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes"
 if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}



if ($result1.StatusCode -eq 200)
{
    Start-Sleep 1
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$JsonBody = @{} | ConvertTo-Json -Compress

# POST command to clear update schedule 

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.ClearUpdateSchedule"

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 

if ($post_result.StatusCode -eq 200)
{
}
else
{
[String]::Format("- FAIL, POST command failed to clear schedule update details, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
break
}
Write-Host "`n- PASS, POST command passed to clear scheduled repository update"
}

# Function to set scheduled repository update

function set_scheduled_repository_update
{

# PATCH commane to enable auto update LC attribute

$JsonBody = @{"Attributes"=@{"LCAttributes.1.AutoUpdate"="Enabled"}} 
$JsonBody = $JsonBody | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes"
 if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}



if ($result1.StatusCode -eq 200)
{
    Start-Sleep 1
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

# Create body payload for POST command

$JsonBody = @{}

if ($shareip)
{
$JsonBody["IPAddress"] = $shareip
}
if ($sharename)
{
$JsonBody["ShareName"] = $sharename
}
if ($sharetype)
{
$JsonBody["ShareType"] = $sharetype
}
if ($username)
{
$JsonBody["UserName"] = $username
}
if ($password)
{
$JsonBody["Password"] = $password
}
if ($workgroup)
{
$JsonBody["Workgroup"] = $workgroup
}
if ($ignorecertwarning)
{
$JsonBody["IgnoreCertWarning"] = $ignorecertwarning
}
if ($time)
{
$JsonBody["Time"] = $time
}
if ($repeat)
{
$JsonBody["Repeat"] = [int]$repeat
}
if ($day_of_week)
{
$JsonBody["DayofWeek"] = $day_of_week
}
if ($day_of_month)
{
$JsonBody["DayofMonth"] = $day_of_month
}
if ($week_of_month)
{
$JsonBody["WeekofMonth"] = $week_of_month
}
if ($apply_update)
{
$JsonBody["ApplyReboot"] = $apply_update
}

$JsonBody = $JsonBody | ConvertTo-Json -Compress

# Run POST command to set update schedule

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.SetUpdateSchedule"

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 


if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
Write-Host "`n- PASS, POST command passed to set scheduled repository update"
break
}
else
{
[String]::Format("- FAIL, POST command failed to set scheduled repository update, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
return
}

}


# Run cmdlet

get_powershell_version 
setup_idrac_creds

# Check to validate iDRAC version detected supports this feature

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellSoftwareInstallationService"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
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
$schedule_repo_update_action_name = "#DellSoftwareInstallationService.SetUpdateSchedule"
$validate_supported_idrac = $get_actions.Actions.$schedule_repo_update_action_name
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
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in`n"
return
}


if ($get)
{
get_update_schedule_details
}

elseif ($get_idrac_time)
{
get_idrac_time
}

elseif ($clear)
{
clear_update_schedule_details
}

elseif ($set -and $repeat -and $time -and $apply_reboot)
{
set_scheduled_repository_update
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s), see help or examples for more information."
}

}



<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 6.0
Copyright (c) 2021, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>




<#
.Synopsis
   Cmdlet using iDRAC with Redfish OEM extension to either get storage controllers, get controller encryption mode settings or rekey storage controller key.
.DESCRIPTION
   Cmdlet using iDRAC with Redfish OEM extension to either get storage controllers, get controller encryption mode settings or rekey the storage controller key, either Local key Management (LKM) or Secure Enterprise key Manager (SEKM).
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - get_storage_controllers: Get current storage controller FQDDs for the server.
   - get_controller_encryption_mode_settings: Pass in the controller FQDD to get current controller encryption mode settings. Example, pass in "RAID.Integrated.1-1".
   - rekey_controller_key: Rekey controller key, pass in the controller FQDD (Example, pass in "RAID.Slot.6-1").
   - mode: Pass in current controller encryption mode for rekey. Supported values are LKM and SEKM. If using LKM, you must also pass in arguments old_key_passphrase, new_key_passphrase and key_id.
   - old_key_passphrase: Pass in old/current key passpharse for the controller. NOTE: If you want to pass in this value as a secure string, don't pass in this argument and the script will prompt to enter.
   - new_key_passphrase: Pass in new key passpharse for the controller. NOTE: If you want to pass in this value as a secure string, don't pass in this argument and the script will prompt to enter.
   - key_id: Pass in either old/current key ID or set a new key ID.
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_controller_encryption_mode_settings RAID.Mezzanine.1-1
   This example will return current encryption mode information for storage controller.
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -get_controller_encryption_mode_settings RAID.Mezzanine.1-1
   This example will first prompt for iDRAC username/password using Get-Credential, return current encryption mode information for storage controller.
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -get_controller_encryption_mode_settings RAID.Mezzanine.1-1 -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   This example will return current encryption mode information for storage controller using iDRAC x-auth token session. 
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -rekey_controller_key RAID.Mezzanine.1-1 -old_key_passphrase Oldpass12# -new_key_passphrase NewPass34$ -key_id testkeyid -mode LKM
   This example will rekey LKM controller key for RAID.Mezzanine.1-1 controller.
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -rekey_controller_key RAID.Mezzanine.1-1 -key_id testkeyid -mode LKM
   This example will first prompt to enter old and new key passpharse as a secure string (will not be echoed to the screen) and then rekey LKM controller key for RAID.Mezzanine.1-1 controller.
.EXAMPLE
   .\Invoke-StorageRekeyControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -rekey_controller_key RAID.Mezzanine.1-1 -mode SEKM
   This example will rekey SEKM controller key for RAID.Mezzanine.1-1 controller.
#>

function Invoke-StorageRekeyControllerKeyREDFISH {

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$False)]
    [string]$idrac_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [Parameter(Mandatory=$False)]
    [switch]$get_storage_controllers,
    [Parameter(Mandatory=$False)]
    [string]$get_controller_encryption_mode_settings,
    [Parameter(Mandatory=$False)]
    [string]$rekey_controller_key,
    [Parameter(Mandatory=$False)]
    [string]$old_key_passphrase,
    [Parameter(Mandatory=$False)]
    [string]$new_key_passphrase,
    [Parameter(Mandatory=$False)]
    [string]$key_id,
    [Parameter(Mandatory=$False)]
    [string]$mode
    )

################################
# Function to ignore SSL certs #
################################

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

#######################################
# Function to Setup iDRAC credentials #  
#######################################

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
$get_creds = Get-Credential
$global:credential = New-Object System.Management.Automation.PSCredential($get_creds.UserName, $get_creds.Password)
}
}

######################################
# Function to get Powershell version #
######################################

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


#############################################
#Function to get storage controller details #
#############################################

function get_storage_controller_details
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$result.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
$number_of_controller_entries = $get_content.Members.Count
$count = 0
Write-Host
while ($count -ne $number_of_controller_entries)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
if ($result.StatusCode -ne 200)
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
$get_content = $get_content.Members[$count]
$get_content = [string]$get_content
$get_content = $get_content.Replace("@{@odata.id=","")
$get_content = $get_content.Replace('}',"")
$uri = "https://$idrac_ip"+$get_content
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

$get_content = $result.Content | ConvertFrom-Json
[String]::Format("- Detailed information for controller {0} -`n", $get_content.Id)
$result.Content | ConvertFrom-Json
Write-Host
$count+=1

}
Write-Host
return
}

############################################
# Function to get storage controller FQDDs #
############################################

function get_storage_controllers
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$result.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_content = $result.Content

Write-Host
$regex = [regex] '/Storage/.+?"'
$allmatches = $regex.Matches($get_content)
$get_all_matches = $allmatches.Value.Replace('/Storage/',"")
$controllers = $get_all_matches.Replace('"',"")
Write-Host "- Server controllers detected -`n"
$controllers
Write-Host
return
}


#############################################################
#Function to get storage controller encryption mode details #
#############################################################

function get_controller_encryption_mode_settings
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_controller_encryption_mode_settings"
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
    #
}
else
{
    [String]::Format("`n- FAIL, GET command failed to get storage controller encryption details, statuscode {0} returned",$result.StatusCode)
    return
}

$get_content = $result.RawContent
$regex = [regex] 'SecurityStatus.+?,'
$security_status = $regex.Matches($get_content).Value.Replace(",","")
$regex = [regex] 'EncryptionMode.+?,'
$encryption_mode = $regex.Matches($get_content).Value.Replace(",","")
$regex = [regex] 'EncryptionCapability.+?,'
$encryption_capability = $regex.Matches($get_content).Value.Replace(",","")
$regex = [regex] 'KeyID.+?,'
$key_id = $regex.Matches($get_content).Value.Replace(",","")
Write-Host "`n- Encryption information for storage controller $get_controller_encryption_mode_settings -`n"
$security_status
$encryption_mode
$encryption_capability
$key_id
Write-Host
return
}

############################################
# Function to rekey storage controller key #
############################################

function rekey_storage_controller_key
{

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService/Actions/DellRaidService.ReKey"
if ($mode -eq "LKM")
{
    if ($old_key_passphrase.Length -eq 0)
    {
    $old_key_passphrase = Read-Host "`n- Enter old controller key passphrase" -AsSecureString
    $old_key_passphrase = [System.Net.NetworkCredential]::new("", $old_key_passphrase).Password
    $new_key_passphrase = Read-Host "`n- Enter new controller key passphrase to set" -AsSecureString
    $new_key_passphrase = [System.Net.NetworkCredential]::new("", $new_key_passphrase).Password
    }
    else
    {
    }
$JsonBody = @{"TargetFQDD"=$rekey_controller_key; "OldKey" = $old_key_passphrase; "NewKey" = $new_key_passphrase; "Keyid" = $key_id; "Mode" = $mode} | ConvertTo-Json -Compress
}
elseif ($mode -eq "SEKM")
{
$JsonBody = @{"TargetFQDD"=$rekey_controller_key; "Mode" = $mode} | ConvertTo-Json -Compress
}
else
{
Write-Host "- WARNING, invalid value entered for Mode property, refer to help text for supported values."
return
}


if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}
    if ($result1.StatusCode -eq 202 -or $result1.StatusCode -eq 200)
    {
    $job_id=$result1.Headers.Location.Split("/")[-1]

    [String]::Format("`n- PASS, statuscode {0} returned to successfully rekey controller key for {2} mode, {1} job ID created",$result1.StatusCode,$job_id, $mode)
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned to rekey controller key",$result1.StatusCode)
    return
    }


$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
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
    #[String]::Format("`n- PASS, statuscode {0} returned to successfully query job ID {1}",$result.StatusCode,$job_id)
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
 
$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
{
$job_type = "realtime_config"
Write-Host "`n- INFO, real time job created, no server reboot needed to apply the changes"
}
if ($overall_job_output.JobType -eq "RAIDConfiguration")
{
$job_type = "staged_config"
Write-Host "`n- INFO, staged job created, server reboot needed to apply the changes"
}

if ($job_type -eq "realtime_config")
{
    while ($overall_job_output.JobState -ne "Completed")
    {
    $uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id" 
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

    $overall_job_output=$result.Content | ConvertFrom-Json
        if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
        {
        Write-Host
        [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
        Write-Host "`n- If needed, check iDRAC Lifecycle Logs for more details about the job failure.`n"
        return
        }
        else
        {
        [String]::Format("- INFO, job not marked completed, current status: {0}",$overall_job_output.Message)
        Start-Sleep 3
        }
    }
Write-Host
Start-Sleep 10
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
return
}

if ($job_type -eq "staged_config")
{
    while ($overall_job_output.Message -ne "Task successfully scheduled.")
    {
    $uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
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
 
    $overall_job_output=$result.Content | ConvertFrom-Json
    if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
    {
    Write-Host
    [String]::Format("- FAIL, job not marked as scheduled, detailed error info: {0}",$overall_job_output)
    return
    }
    else
    {
    [String]::Format("- INFO, job not marked scheduled, current message: {0}",$overall_job_output.Message)
    Start-Sleep 1
    }
    }
}
Write-Host "`n- PASS, $job_id successfully scheduled, rebooting server"



while ($overall_job_output.JobState -ne "Completed")
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
    {
    Write-Host
    [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
    return
    return
    }
    else
    {
    [String]::Format("- INFO, job not marked completed, current status: {0}",$overall_job_output.Message)
    Start-Sleep 10
    }
}
Start-Sleep 10
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
return
}




############
# Run code #
############

get_powershell_version
setup_idrac_creds

# Code to check for supported iDRAC version installed

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Oem/Dell/DellRaidService"
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


if ($get_storage_controllers)
{
get_storage_controllers
}
elseif ($get_storage_controllers)
{
get_storage_controller_details
}
elseif ($get_controller_encryption_mode_settings)
{
get_controller_encryption_mode_settings
}
elseif ($rekey_controller_key)
{
rekey_storage_controller_key
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}

}





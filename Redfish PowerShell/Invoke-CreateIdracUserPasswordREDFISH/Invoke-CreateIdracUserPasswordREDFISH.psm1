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
   iDRAC cmdlet using Redfish API to either get current iDRAC user account details, create or delete iDRAC user.
.DESCRIPTION
   iDRAC cmdlet using Redfish API to either get current iDRAC user account details, create or delete iDRAC user.
   PARAMETERS 
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - idrac_user_id: Pass in the user account ID you want to create or get details for only this user account. Note iDRAC9 supports up to 16 users, iDRAC10 supports up to 32 users.
   - idrac_new_username: Pass in the new user name you want to create
   - idrac_new_password: Pass in the new password you want to set for the new user
   - idrac_user_privilege: Pass in the privilege level for the user you are creating. Supported values are: Administrator, Operator and ReadOnly. Note: these values are case sensitive. Note if iDRAC10 or newer installed you can pass custom user role name here.
   - idrac_user_enable: Enable of disable the new iDRAC user you are creating. Pass in 'true' to enable the user, pass in 'false' to disable the user
   - get_idrac_user_accounts: Get current settings for all iDRAC user accounts. If you want to get only a specific user account, also pass in argument 'idrac_user_id'
   - delete_idrac_user: Delete iDRAC user, pass in the user account id
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_idrac_user_accounts
   This example shows getting all iDRAC user account information
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -get_idrac_user_accounts -idrac_user_id 3
   This example will first prompt for iDRAC username/password using Get-Credential, then return only information for iDRAC user account 3
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -idrac_user_id 3 -idrac_new_username user3 -idrac_new_password test123 -idrac_user_privilege ReadOnly -idrac_user_enable true
   This example shows creating iDRAC user for account ID 3 with Read Only privileges and enabling the account
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_user_id 3 -idrac_user_privilege ReadOnly -idrac_user_enable true
   This example will first prompt for iDRAC username/password using Get-Credential, then prompt to pass in new username and password using Get-Credential for the new user you're creating which is account ID 3. This new user will be created with Read Only privileges and enabled
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -delete_idrac_user 3
   This example shows deleting iDRAC user account 3
#>

function Invoke-CreateIdracUserPasswordREDFISH {

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
    [int]$idrac_user_id,
    [Parameter(Mandatory=$False)]
    [string]$idrac_new_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_new_password,
    [Parameter(Mandatory=$False)]
    [string]$idrac_user_privilege,
    [ValidateSet("true", "false")]
    [Parameter(Mandatory=$False)]
    [string]$idrac_user_enable,
    [Parameter(Mandatory=$False)]
    [switch]$get_idrac_user_accounts,
    [Parameter(Mandatory=$False)]
    [string]$delete_idrac_user
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
$get_creds = Get-Credential -Message "Enter iDRAC username and password to run cmdlet"
$global:credential = New-Object System.Management.Automation.PSCredential($get_creds.UserName, $get_creds.Password)
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


function get_one_user_account_details
{
Write-Host "`n- INFO, executing GET command to get iDRAC user account $idrac_user_id information"

if ($global:iDRAC_version -eq "old")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
}
else
{
$uri = "https://$idrac_ip/redfish/v1/AccountService/Accounts/$idrac_user_id"
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
$result.Content | ConvertFrom-Json
return
}


function get_all_idrac_user_account_details
{
Write-Host "`n- INFO, executing GET command to get iDRAC user account information`n"
if ($global:iDRAC_version -eq "old")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts?`$expand=*(`$levels=1)"
}
else
{
$uri = "https://$idrac_ip/redfish/v1/AccountService/Accounts?`$expand=*(`$levels=1)"
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
$get_results = $result.Content | ConvertFrom-Json
$get_results.Members
return
}


function create_new_idrac_user_account_iDRAC9
{

# Check if user account is already created

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
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
$get_results = $result.Content | ConvertFrom-Json

if ([string]::IsNullOrWhitespace($get_results.UserName))
{

if ($idrac_user_enable -eq "true")
{
$enable_status = $true
}
if ($idrac_user_enable -eq "false")
{
$enable_status = $false
}

if ($idrac_new_username -and $idrac_new_password)
{
$JsonBody = @{UserName = $idrac_new_username; Password= $idrac_new_password; RoleId = $idrac_user_privilege; Enabled = $enable_status} | ConvertTo-Json -Compress
}
else
{
$get_creds = Get-Credential -Message 'Enter NEW iDRAC username and password to create'
$JsonBody = @{"UserName" = $get_creds.UserName; "Password" = $get_creds.GetNetworkCredential().Password; "RoleId" = $idrac_user_privilege; "Enabled" = $enable_status} | ConvertTo-Json -Compress
}
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"

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
    [String]::Format("`n- PASS, statuscode {0} returned successfully for PATCH command to create iDRAC user {1}",$result1.StatusCode, $idrac_new_username)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
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

$check_username = $result.Content | ConvertFrom-Json
if ($check_username.UserName -eq $idrac_new_username -or $check_username.UserName -eq $get_creds.UserName)
{
Write-Host "- PASS, iDRAC user ID '$idrac_user_id' successfully created`n"
}

else
{
Write-Host "- FAIL, iDRAC user ID '$idrac_user_id' not successfully created"
return
}
return

}

else
{
Write-Host "`n- WARNING, user already detected for ID $idrac_user_id, new user will not be created"
return
}

}

function create_new_idrac_user_account_iDRAC10
{

if ($idrac_user_enable -eq "true")
{
$enable_status = $true
}
if ($idrac_user_enable -eq "false")
{
$enable_status = $false
}

if ($idrac_new_username -and $idrac_new_password)
{
$JsonBody = @{UserName = $idrac_new_username; Password= $idrac_new_password; RoleId = $idrac_user_privilege; Enabled = $enable_status; "Id" = [string]$idrac_user_id} | ConvertTo-Json -Compress
}
else
{
$get_creds = Get-Credential -Message 'Enter NEW iDRAC username and password to create'
$JsonBody = @{"UserName" = $get_creds.UserName; "Password" = $get_creds.GetNetworkCredential().Password; "RoleId" = $idrac_user_privilege; "Enabled" = $enable_status; "Id" = [string]$idrac_user_id} | ConvertTo-Json -Compress
}
$uri = "https://$idrac_ip/redfish/v1/AccountService/Accounts"

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


if ($result1.StatusCode -eq 201)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully for PATCH command to create iDRAC user {1}",$result1.StatusCode, $idrac_new_username)
}
else
{
    [String]::Format("- FAIL, POST command failed to create new user, statuscode {0} returned",$result1.StatusCode)
    $result1
    return
}

$uri = "https://$idrac_ip/redfish/v1/AccountService/Accounts/$idrac_user_id"
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

$check_username = $result.Content | ConvertFrom-Json
if ($check_username.UserName -eq $idrac_new_username -or $check_username.UserName -eq $get_creds.UserName)
{
Write-Host "- PASS, iDRAC user ID '$idrac_user_id' successfully created`n"
}

else
{
Write-Host "- FAIL, iDRAC user ID '$idrac_user_id' not successfully created"
return
}
return
}


function delete_idrac_user_account_iDRAC9
{
Write-Host "`n- INFO, deleting iDRAC user account $delete_idrac_user"
$JsonBody = @{Enabled = $false; RoleId = "None"} | ConvertTo-Json

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"
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

$JsonBody = @{UserName = ""} | ConvertTo-Json -Compress

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"

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
    [String]::Format("`n- PASS, statuscode {0} returned successfully for PATCH command to delete iDRAC user {1}",$result1.StatusCode, $delete_idrac_user)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"
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

$check_username = $result.Content | ConvertFrom-Json
if ($check_username.UserName -eq "")
{
Write-Host "- PASS, iDRAC user id '$delete_idrac_user' successfully deleted`n"
}

else
{
Write-Host "- FAIL, iDRAC user $delete_idrac_user not successfully deleted"
return
}
return

}

function delete_idrac_user_account_iDRAC10
{
Write-Host "`n- INFO, deleting iDRAC user account $delete_idrac_user"
$uri = "https://$idrac_ip/redfish/v1/AccountService/Accounts/$delete_idrac_user"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Delete -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Delete -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Delete -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Delete -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


if ($result1.StatusCode -eq 204)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to delete iDRAC user {1}",$result1.StatusCode, $delete_idrac_user)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    $result1
    return
}
}

# Run cmdlet 

if ($get_idrac_user_accounts -and $idrac_user_id)
{
get_one_user_account_details
}

elseif ($get_idrac_user_accounts)
{
get_all_idrac_user_account_details
}

elseif ($idrac_user_id -and $idrac_user_privilege -and $idrac_user_enable -or $idrac_new_username -or $idrac_new_password)
{
    if ($global:iDRAC_version -eq "old")
    {
    create_new_idrac_user_account_iDRAC9
    }
    else
    {
    create_new_idrac_user_account_iDRAC10
    }
}

elseif ($delete_idrac_user)
{
    if ($global:iDRAC_version -eq "old")
    {
    delete_idrac_user_account_iDRAC9
    }
    else
    {
    delete_idrac_user_account_iDRAC10
    }
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s), please see help or examples for more information."
}

}










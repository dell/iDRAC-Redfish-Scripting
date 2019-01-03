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
   Cmdlet using Redfish API to either create or delete iDRAC user
.DESCRIPTION
   Cmdlet using Redfish API to either create or delete iDRAC user
   PARAMETERS 
   - idrac_ip: "pass in iDRAC IP address"
   - idrac_username: "pass in iDRAC username"
   - idrac_password: "pass in iDRAC username password"
   - idrac_user_id: "pass in the user account ID you want to configure"
   - idrac_new_username: "pass in the new user name you want to create"
   - idrac_new_password: "pass in the new password you want to set for the new user"
   - idrac_user_privilege: "pass in the privilege level for the user you are creating. Supported values are: Administrator, Operator, ReadOnly and None. Note: these values are case sensitive"
   - idrac_user_enable: "enable of disable the new iDRAC user you are creating. Pass in 'true' to enable the user, pass in 'false' to disable the user"
   - get_idrac_user_accounts: "get current settings for all iDRAC user accounts, pass in 'y'. If you want to get only a specific user account, also pass in argument 'idrac_user_id'"
   - delete_idrac_user: "delete iDRAC user, pass in the user account id"
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_idrac_user_accounts y
   This example shows getting all iDRAC user account information
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -idrac_user_id 3 -idrac_new_username user3 -idrac_new_password test123 -idrac_user_privilege ReadOnly -idrac_user_enable true
   This example shows creating iDRAC user for account ID 3 with Read Only privileges and enabling the account.
.EXAMPLE
   Invoke-CreateIdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -delete_idrac_user 3
   This example shows deleting iDRAC user account 3
#>

function Invoke-CreateIdracUserPasswordREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [int]$idrac_user_id,
    [Parameter(Mandatory=$False)]
    [string]$idrac_new_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_new_password,
    [Parameter(Mandatory=$False)]
    [string]$idrac_user_privilege,
    [Parameter(Mandatory=$False)]
    [string]$idrac_user_enable,
    [Parameter(Mandatory=$False)]
    [string]$get_idrac_user_accounts,
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

Ignore-SSLCertificates


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)

if ($get_idrac_user_accounts -ne "" -and $idrac_user_id -ne "")
{
Write-Host "`n- WARNING, executing GET command to get iDRAC user account $idrac_user_id information"

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
try {
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$result.Content | ConvertFrom-Json
}
catch {
Write-Host "`n- FAIL, GET command failed for iDRAC user account id $idrac_user_id"
return
}
return
}


if ($get_idrac_user_accounts -ne "")
{
Write-Host "`n- WARNING, executing GET command to get iDRAC user account information`n"
$count_range = 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
foreach ($i in $count_range)
{
$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$i"
try {
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$result.Content | ConvertFrom-Json
}
catch {
Write-Host "`n- FAIL, GET command failed for iDRAC user account id $i"
return
}
}
return
}


if ($idrac_new_username -ne "" -and $idrac_new_password -ne "" -and $idrac_user_privilege -ne "" -and $idrac_user_enable -ne "")
{

if ($idrac_user_enable -eq "true")
{
$enable_status = $true
}
if ($idrac_user_enable -eq "false")
{
$enable_status = $false
}

$JsonBody = @{UserName = $idrac_new_username; Password= $idrac_new_password; RoleId = $idrac_user_privilege; Enabled = $enable_status} | ConvertTo-Json -Compress

Write-Host "`n- Parameters being used to create iDRAC user id $idrac_user_id -`n"

$parameters_used = $JsonBody.Replace("{","")
$parameters_used = $parameters_used.Replace("}","")
$parameters_used

$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"

try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
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

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}

if ($result.StatusCode -ne 200)
{
[String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
return
}

$check_username = $result.Content | ConvertFrom-Json
if ($check_username.UserName -eq $idrac_new_username)
{
Write-Host "- PASS, iDRAC user '$idrac_new_username' successfully created`n"
}

else
{
Write-Host "- FAIL, iDRAC user $idrac_new_username not successfully created"
return
}
return

}


if ($delete_idrac_user -ne "")
{
Write-Host "`n- WARNING, deleting iDRAC user account $delete_idrac_user"
$JsonBody = @{Enabled = $false; RoleId = "None"} | ConvertTo-Json

$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}

$JsonBody = @{UserName = ""} | ConvertTo-Json -Compress

$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"

try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
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

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$delete_idrac_user"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
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

}






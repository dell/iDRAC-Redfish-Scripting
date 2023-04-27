<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 9.0

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
   Cmdlet using iDRAC with Redfish API to get either server current power state or change the server power state
.DESCRIPTION
   Cmdlet using iDRAC with Redfish API to get either server current power state or change the server power state. If you're changing the server power state, make sure you pass in the exact string value since the values are case sensitive.
   
   Supported parameters:
   - idrac_ip: Pass in the iDRAC IP
   - idrac_username: Pass in the iDRAC user name
   - idrac_password: Pass in the iDRAC user name password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - power_request_value: Pass in the value you want to change the server power state to
   - get_power_state_only: Get current server power state and supported values to change server power state
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_ password calvin -get_power_state_only 
   This example will get current server power state and supported values to change server power state.
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 -get_power_state_only 
   This example will first prompt to enter iDRAC username and password using Get-Credentials, then get current server power state.
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 get_power_state_only -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   This example will get current server power state using iDRAC X-auth token session.
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -power_request_value On
   This example will execute action to power ON the server.
#>

function Set-PowerControlREDFISH {


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
    [string]$power_request_value,
    [Parameter(Mandatory=$False)]
    [switch]$get_power_state_only

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

# Function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

get_powershell_version

# Function to setup iDRAC creds

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

setup_idrac_creds

# Get current server power state

if ($get_power_state_only)
{

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
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
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned successfully to get current power state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}


$get_content = $result.Content | ConvertFrom-json
$power_state = $get_content.PowerState

Write-Host "`n- INFO, current server power state is '$power_state'`n"

Write-Host
Write-Host "Supported power control values are:`n`n"
$get_content = $result.Content | ConvertFrom-json
$get_action = $get_content.Actions
$create_hash_table = @{}
$get_action.psobject.properties | Foreach { $create_hash_table[$_.Name] = $_.Value }
$create_hash_table["#ComputerSystem.Reset"] | Convertto-Json
return

}

# POST command to set server power state

if ($power_request_value)
{

$JsonBody = @{ "ResetType" = $power_request_value
    } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
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

if ($result1.StatusCode -eq 204)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned, power control operation success for value '{1}'",$result1.StatusCode, $power_request_value)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}

}



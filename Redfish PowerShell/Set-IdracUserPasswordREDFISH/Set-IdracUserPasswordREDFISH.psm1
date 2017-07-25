<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 1.0

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
   Cmdlet used to change iDRAC user password
.DESCRIPTION
   Cmdlet used to change iDRAC user password using Redfish API. Once the iDRAC user password has changed, cmdlet will execute GET command to validate the new password was set.
   Supported parameters: 
   - idrac_ip "pass in iDRAC IP address"
   - idrac_username "pass in iDRAC username"
   - idrac_password "pass in iDRAC username current password"
   - idrac_user_id "pass in the user account ID"
   - idrac_new_password "pass in the new password you want to set to"
.EXAMPLE
   Set-IdracUserPasswordREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -idrac_user_id 2 -idrac_new_password test 
   This example shows changing root password. I pass in the current password of "calvin", pass in "2" for the user account ID and pass in the new password i want to change to which is "test".
#>

function Set-IdracUserPasswordREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$True)]
    [int]$idrac_user_id,
    [Parameter(Mandatory=$True)]
    [string]$idrac_new_password

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


$JsonBody = @{'Password'= $idrac_new_password} | ConvertTo-Json -Compress


$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json'

if ($result1.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully for PATCH command to change iDRAC user password",$result1.StatusCode)
    Start-Sleep 5
    
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$user = $idrac_username
$pass= $idrac_new_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)

Write-Host "`n- WARNING, executing GET command with new user password to validate password was changed"

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Accounts/$idrac_user_id"

try {
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
}
catch {
Write-Host "`n- FAIL, new password verification failed for iDRAC user"
return
}
 

if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully for GET command, iDRAC user password changed`n",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned, password not changed",$result.StatusCode)
    return
}

}

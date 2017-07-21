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
   Cmdlet used to reset iDRAC to default settings using Redfish API
.DESCRIPTION
   Cmdlet used to reset iDRAC to default settins using Redfish API. Once the POST command has completed, iDRAC will reset to defaults and restart the iDRAC. iDRAC should be back up within 1 minute.

   PARAMETERS 
   - idrac_ip "pass in iDRAC IP address"
   - idrac_username "pass in iDRAC username"
   - idrac_password "pass in iDRAC username password"
   
.EXAMPLE
   Set-IdracDefaultSettingsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin
   This example shows reset the iDRAC to default settings
#>

function Set-IdracDefaultSettingsREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password
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

$JsonBody = @{'ResetType'= 'All'} | ConvertTo-Json

$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults"
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'

if ($result1.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to reset iDRAC to default settings",$result1.StatusCode)
    Start-Sleep 15
    
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    Exit
}

Write-Host -Foreground Yellow "`n- WARNING, iDRAC will now reset to default settings and restart the iDRAC. iDRAC should be back up within 1 minute.`n" 

}

<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 4.0

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
   - get_reset_possible_values "pass in 'y' to get reset iDRAC possible values"
   - reset_value "pass in string reset value for reset iDRAC. if needed, execute -get_reset_possible_values to get supported string values

.EXAMPLE
   Set-IdracDefaultSettingsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -reset_idrac_possible_values y
   This example shows getting possible values for reset iDRAC   
.EXAMPLE
   Set-IdracDefaultSettingsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -reset_value ResetAllWithRootDefaults
   This example shows reset iDRAC to default settings, root user password set to calvin 
#>

function Set-IdracDefaultSettingsREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$reset_idrac_possible_values,
    [Parameter(Mandatory=$False)]
    [string]$reset_value
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



[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)

if ($reset_idrac_possible_values)
{
Write-Host "`n- Possible values for iDRAC reset -`n`n- All                       'Reset all iDRAC configuration, reset user to shipping values (root/calvin or server toetag)'`n- ResetAllWithRootDefaults  'Reset all iDRAC configuration, root user password set to calvin'`n- Default                   'Reset all iDRAC configuration to default but preserve user/network settings'`n"
return
}

if ($reset_value)
{
$user_choice = Read-Host "`n- WARNING, reset iDRAC using '$reset_value' option, are you sure you want to perform this operation? Type 'y' to execute or 'n' to exit: " 
if ($user_choice.ToLower() -eq 'n')
{
return
}

Write-Host "`n- WARNING, reset iDRAC to default settings using '$reset_value' option"
$JsonBody = @{'ResetType'= $reset_value} | ConvertTo-Json -Compress

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/DellManager.ResetToDefaults"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 

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

Write-Host -Foreground Yellow "`n- WARNING, iDRAC will now reset to default settings and restart the iDRAC. iDRAC should be back up within a few minutes.`n" 
}
}

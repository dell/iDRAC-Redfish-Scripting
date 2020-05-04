<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 1.0

Copyright (c) 2020, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>




<#
.Synopsis
   Cmdlet used to get server slot information for all devices in the server. 
.DESCRIPTION
   Cmdlet using Redfish API with OEM extension to get server slot information for all devices and will be echo output to the screen. if large amount of data is returned, its recommended to redirect output to a file.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
.EXAMPLE
   .\Get-IdracServerSlotInformationREDFISH -idrac_ip 192.168.0.120 -username root -password calvin 
   This example will get server slot information, echo to the screen.
.EXAMPLE
   .\Get-IdracServerSlotInformationREDFISH -idrac_ip 192.168.0.120 -username root -password calvin > R640_slot_info.txt
   This example will get server slot information and redirect output to a log file.
#>






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

$next_link_value = 0

Write-Host -ForegroundColor Yellow "`n- WARNING, getting server slot information for iDRAC $idrac_ip`n"
Start-Sleep 5

while ($true)
{

$skip_uri ="?"+"$"+"skip="+$next_link_value

$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellSlotCollection$skip_uri"

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
    Write-Host -ForegroundColor Yellow "`n- WARNING, cmdlet execution complete. Note: If needed, execute cmdlet again and redirect output to a file."
    return
    }
    else
    {
    Write-Host
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
$get_content=$result.Content | ConvertFrom-Json
$get_content.Members
$next_link_value = $next_link_value+50

}







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
   Cmdlet used to get either server current power state or change the server power state
.DESCRIPTION
   Cmdlet used to get either server current power state or change the server power state. If you are changing the server power state, make sure you pass in the exact string value since the values
   are case sensitive.
   
   Supported parameters:
   - idrac_ip, pass in the iDRAC IP
   - idrac_username, pass in the iDRAC user name
   - idrac_password, pass in the iDRAC user name password
   - power_request_value, pass in the value you want to change the server power state to
   - get_power_state_only, get the current server power state
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_ password calvin -get_power_state_only y
   # Example to get current server power state
.EXAMPLE
   Set-PowerControlREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -power_request_value On
   # Example to power ON the server
#>

function Set-PowerControlREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$power_request_value,
    [Parameter(Mandatory=$False)]
    [string]$get_power_state_only

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

# Get current server power state

if ($get_power_state_only -eq "y")
{

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 

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

$get_content=$result.Content
$power_state=[regex]::Match($get_content, "PowerState.+?,").Captures[0].value
$power_state=$power_state -replace (",","")
$power_state=$power_state -split (":")

if ($power_state -eq '"On"')
{
Write-Host
Write-Host "- WARNING, Server current power state is ON"
}
else
{
Write-Host
Write-Host "- WARNING, Server current power state is OFF"
}
Write-Host
Write-Host "Supported power control values are:`n`n- On`n- ForceOff`n- GracefulRestart`n- GracefulShutdown"

return
}

if ($get_power_state_only -eq "n")
{
return
}


# POST command to set server power state

$JsonBody = @{ "ResetType" = $power_request_value
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'

if ($result1.StatusCode -eq 204)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned, power control operation success for: {1}",$result1.StatusCode, $power_request_value)
    Start-Sleep 3
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

return

}

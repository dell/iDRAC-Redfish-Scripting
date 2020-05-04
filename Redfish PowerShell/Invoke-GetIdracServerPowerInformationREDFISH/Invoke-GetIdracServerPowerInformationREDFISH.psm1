<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0

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
   Cmdlet using Redfish API to get iDRAC power information for the server. 
.DESCRIPTION
   Cmdlet using Redfish API to get iDRAC power information for the server. Cmdlet will support getting either all iDRAC server power information or selective information based off argument value passed in.

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - get_all_power_info: Pass in a value of "y"
   - get_specific_power_info: Pass in "1" for Power Control, "2" for Power Supply, "3" for Power Redundancy and "4" for Power Voltage
   
.EXAMPLE
   Invoke-GetIdracServerPowerInformationREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_all_power_info y 
   This example will pull all iDRAC power information which includes Power Control, Power Supplies, Power Redundancy and Power Voltages
   Invoke-GetIdracServerPowerInformationREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_specific_power_info 2 
   This example will return only iDRAC Power Supply information.
#>

function Invoke-GetIdracServerPowerInformationREDFISH {


# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_all_power_info,
    [Parameter(Mandatory=$False)]
    [string]$get_specific_power_info
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


# Function to set up iDRAC credentials 

function setup_idrac_creds
{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}


# Get PSU information

function get_all_power_info
{

$uri = "https://$idrac_ip/redfish/v1/Chassis/System.Embedded.1/Power"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

if ($get_result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
$content = $get_result.Content | ConvertFrom-Json

$power_control = $content.PowerControl
$power_supplies = $content.PowerSupplies
$power_redundancy = $content.Redundancy
$power_voltage = $content.Voltages 
[String]::Format("`n--- Power Control Details ---`n")
$power_control
[String]::Format("`n--- Power Supply Details ---`n")
$power_supplies
[String]::Format("`n--- Power Redundancy Details ---`n")
$power_redundancy
[String]::Format("`n--- Power Voltage Details ---`n")
$power_voltage

}

}


function get_specific_power_info

{

$uri = "https://$idrac_ip/redfish/v1/Chassis/System.Embedded.1/Power"
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }

if ($get_result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
$content = $get_result.Content | ConvertFrom-Json

$power_control = $content.PowerControl
$power_supplies = $content.PowerSupplies
$power_redundancy = $content.Redundancy
$power_voltage = $content.Voltages 

if ($get_specific_power_info -eq "1")
{
[String]::Format("`n--- Power Control Details ---`n")
$power_control
}
elseif ($get_specific_power_info -eq "2")
{
[String]::Format("`n--- Power Supply Details ---`n")
$power_supplies
}
elseif ($get_specific_power_info -eq "3")
{
[String]::Format("`n--- Power Redundancy Details ---`n")
$power_redundancy
}
elseif ($get_specific_power_info -eq "4")
{
[String]::Format("`n--- Power Voltage Details ---`n")
$power_voltage
}
else
{
[String]::Format("`n- FAIL, invalid value passed in for argument get_specific_power_info")
}

}

}


# Run cmdlet

get_powershell_version 
setup_idrac_creds


if ($get_all_power_info.ToLower() -eq "y")
{
get_all_power_info
}
elseif ($get_specific_power_info)
{
get_specific_power_info
}


}








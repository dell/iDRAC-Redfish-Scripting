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
   Cmdlet using Redfish API with OEM extension to export all server hardware information to a file locally using default browser session.
.DESCRIPTION
   Cmdlet using Redfish API with OEM extension to export all server hardware information to a file locally. You will be prompted to download the exported HW inventory using your default browser session. If you select yes, it will automatically launch a browser session and download the file. You may be prompted to enter iDRAC credentials if this is the first time you are using browser to access the iDRAC.

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   
.EXAMPLE
   Invoke-ExportHwInventoryLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin
   # This example will export the complete server hardware information to a local file using your default browser session. 
#>

function Invoke-ExportHwInventoryLocalREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

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

# Function to set up iDRAC credentials 

function setup_idrac_creds
{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


# Get Support Assist current license agreement information

function export_HW_inventory_local
{
Write-Host "`n- WARNING, exporting server hardware inventory locally for iDRAC $idrac_ip"
$JsonBody = @{"ShareType"="Local"} | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportHWInventory"

try
{
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
}
catch
{
Write-Host
$RespErr
break
} 

if ($post_result.StatusCode -eq 202)
{
Write-Host "- PASS, POST command passed to export server HW inventory, status code 202 returned"
}
else
{
[String]::Format("- FAIL, POST command failed to export server HW inventory, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
return
}


$export_HW_inventory_file_uri = $post_result.Headers.Location
Write-Host "- WARNING, GET URI for exported HW inventory file: '$export_HW_inventory_file_uri'"

$uri = "https://$idrac_ip$export_HW_inventory_file_uri"

$user_answer = Read-Host -Prompt "`n- Would you like to use default browser to download exported HW inventory file now? Type 'y' for yes or 'n' for no"
    if ($user_answer.ToLower() -eq "y")
    {
    Write-Host "`n- User selected to download exported HW inventory file now, check your default browser session."
    Start-Sleep 5
    start $uri
    Write-Host
    return
    }
    elseif ($user_answer.ToLower() -eq "n")
    {
    Write-Host "`n- WARNING, user selected to not download the exported HW inventory file now. HW inventory file can still be accessed by executing GET on URI '$uri'"
    Write-Host
    return
    }
    else
    {
    Write-Host "- FAIL, invalid option passed in for downloading exported HW inventory file"
    return
    }
}

# Run cmdlet

get_powershell_version 
setup_idrac_creds

# Check to validate iDRAC version detected supports this feature

$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService"
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
$get_actions = $get_result.Content | ConvertFrom-Json
$hw_inventory_action_name = "#DellLCService.ExportHWInventory"
$validate_supported_idrac = $get_actions.Actions.$hw_inventory_action_name
    try
    {
    $test = $validate_supported_idrac.GetType()
    }
    catch
    {
    Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
    break
    }
}
else
{
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
return
}

export_HW_inventory_local

}







<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0
Copyright (c) 2019, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>




<#
.Synopsis
   Cmdlet using Redfish DMTF to either get virtual media information, attach or eject virtual media located on HTTP/HTTPS share. 
.DESCRIPTION
   Cmdlet using Redfish DMTF to either get virtual media information, attach or eject virtual media located on HTTP/HTTPS share. 
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_virtual_media_info: Pass in "y" to get current virtual media information.
   - virtual_media_action: Type of action you want to perform. Pass in "1" if you want perform Insert, pass in "2" if you want to perform Eject.
   - virtual_media_device: Type of virtual media device you want to use. Pass in "1" for CD or "2" for removable disk. 
   - uri_path: For insert virtual media, pass in the HTTP or HTTPS URI path of the remote image. Note: If attaching removable disk, only supported file type is .img'
.EXAMPLE
   .\Invoke-InsertEjectVirtualMediaREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_virtual_media_info y
   This example will return virtual media information for virtual CD and virtual removable disk.
.EXAMPLE
   .\Invoke-InsertEjectVirtualMediaREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -virtual_media_action 1 -virtual_media_device 1 -uri_path http://192.168.0.130/updates_http/esxi.iso
   This example will attach ISO on HTTP share as a virtual CD.
.EXAMPLE
   .\Invoke-InsertEjectVirtualMediaREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -virtual_media_action 2 -virtual_media_device 2
   This example will detach virtual removable disk.
#>

function Invoke-InsertEjectVirtualMediaREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_virtual_media_info,
    [Parameter(Mandatory=$False)]
    [string]$virtual_media_action,
    [Parameter(Mandatory=$False)]
    [string]$virtual_media_device,
    [Parameter(Mandatory=$False)]
    [string]$uri_path
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


# Setting up iDRAC credentials for functions  

function setup_idrac_creds

{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}

# function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

# Function to test if iDRAC version supports this cmdlet

function test_iDRAC_version 

{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD"
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
}


# Function to GET virtual media information 

function get_virtual_media_info

{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia"
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
[String]::Format("`n- GET command passed for URI {0}, status code {1} returned`n",$u, $result.StatusCode)
$result = $result.Content | ConvertFrom-Json
    foreach ($i in $result.Members)
    {
    $u = $i.'@odata.id'
    Write-Host "- Detailed information for URI: $u"   
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri "https://$idrac_ip$u" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri "https://$idrac_ip$u" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
    Write-Host
    $result1.Content | ConvertFrom-Json
    }

}

# Function to perform virtual media action insert

function virtual_media_insert

{
if ($virtual_media_device -eq 1)
{
$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia"
$get_uri = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD"
}
elseif ($virtual_media_device -eq 2)
{
$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.InsertMedia"
$get_uri = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk"
}
else
{
Write-Host "`n- FAIL, invalid value passed in for parameter 'virtual_media_device'"
return
}
$JsonBody = @{'Image'=$uri_path;'Inserted'=$true;'WriteProtected'=$true} | ConvertTo-Json -Compress
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $u1 -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host  
    $RespErr
    break
    } 

if ($result1.StatusCode -eq 204)
{
[String]::Format("`n- PASS, POST command passed for Virtual Media Insert, status code {0} returned", $result1.StatusCode)
}   
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri "https://$idrac_ip$get_uri" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri "https://$idrac_ip$get_uri" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
    break
    $result1.Content | ConvertFrom-Json
    

    Write-Host
    $final_results = $result1.Content | ConvertFrom-Json
if ($final_results.Inserted -eq $true)
{
Write-Host "- PASS, GET command passed and verified virtual media device is attached(insert)`n"
}
else
{
Write-Host "- FAIL, verification failed to verify virtual media device is attached"
return
}
    
return
}


# Function to perform virtual media action eject

function virtual_media_eject

{
if ($virtual_media_device -eq 1)
{
$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia"
$get_uri = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD"
}
elseif ($virtual_media_device -eq 2)
{
$u1 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk/Actions/VirtualMedia.EjectMedia"
$get_uri = "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/RemovableDisk"
}
else
{
Write-Host "`n- FAIL, invalid value passed in for parameter 'virtual_media_device'"
return
}
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $u1 -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host  
    $RespErr
    break
    } 
if ($result1.StatusCode -eq 204)
{
[String]::Format("`n- PASS, POST command passed for Virtual Media Eject, status code {0} returned", $result1.StatusCode)
} 
   try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri "https://$idrac_ip$get_uri" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri "https://$idrac_ip$get_uri" -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    }
    Write-Host
    Start-Sleep 5
    
    Write-Host
    $final_results = $result1.Content | ConvertFrom-Json
if ($final_results.Inserted -eq $false)
{
Write-Host "- PASS, GET command passed and verified virtual media device is detached(eject)`n"
}
else
{
Write-Host "- FAIL, verification failed to verify virtual media device is detached"
return
}
    
return
}


# Run code

get_powershell_version
setup_idrac_creds
test_iDRAC_version

if ($get_virtual_media_info -ne "")
{
get_virtual_media_info
}
elseif ($virtual_media_action -eq 1)
{
virtual_media_insert
}
elseif ($virtual_media_action -eq 2)
{
virtual_media_eject
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}

}

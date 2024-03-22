<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 6.0

Copyright (c) 2021, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
   iDRAC cmdlet using Redfish with OEM extension to either export or import SSL certificate locally. 
.DESCRIPTION
   iDRAC cmdlet using Redfish with OEM extension to either export or import SSL certificate locally.   

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - export_ssl_cert: Export SSL, pass in the type of cert you want to export. To get supported values, execute argument -get_supported_ssl_cert_types. NOTE: This value is case sensitive, make sure to pass in exact string syntax. 
   - import_ssl_cert: Import SSL, pass in the type of cert you want to import. To get supported values, execute argument -get_supported_ssl_cert_types. NOTE: This value is case sensitive, make sure to pass in exact string syntax. NOTE: If using iDRAC 6.00.00 or newer, once you import the cert, you're no longer required to reboot the iDRAC to apply it. 
   - get_supported_ssl_cert_types: Get supported ssl cert types which will be used for either export or import operations. 
   - cert_filename: Pass in SSL cert filename. For export, you'll be passing in an unique filename which the SSL cert contents will get copied to. For import, passed in the signed SSL cert filename. 
   - passphrase: Pass in passphrase string if the cert you are importing is passpharse protected.
   - delete_ssl_cert: Delete SSL cert pass in value CustomCertificate, CSC or ClientTrustCertificate. iDRAC does not support delete server or CA certs. 
   - restore_factory_defaults: Restore the webserver certificate to factory defaults

.EXAMPLE
   Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_supported_ssl_cert_types 
   This example will get supported SSL certs for export or import operations. 
.EXAMPLE
   Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -get_supported_ssl_cert_types 
   # This example will first prompt for iDRAC username/password using Get-Credential, then get supported SSL certs for export or import operations. 
.EXAMPLE
   Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -get_supported_ssl_cert_types  -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   # This example will get supported SSL certs for export or import operations using iDRAC X-auth token session. 
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH>Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -export_ssl_cert Server -cert_filename C:\Python39\R640_server_cert.ca
   This example will export iDRAC web server certificate and copy contents to the filename you specified. 
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH>Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -import_ssl_cert CustomCertificate -cert_filename C:\Python39\R640_server_cert.pem -passphrase Test1234#
   This example will import custom certificate with passphrase.
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH>Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -delete_ssl_cert CSC
   This example will delete CSC cert.
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH>Invoke-ExportImportSslCertificateREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -restore_factory_defaults
   This example will restore webserver certs to factory defaults. 
#>

function Invoke-ExportImportSslCertificateREDFISH {

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
    [string]$export_ssl_cert,
    [Parameter(Mandatory=$False)]
    [string]$import_ssl_cert,
    [Parameter(Mandatory=$False)]
    [switch]$get_supported_ssl_cert_types,
    [Parameter(Mandatory=$False)]
    [string]$cert_filename,
    [Parameter(Mandatory=$False)]
    [string]$passphrase,
    [ValidateSet("CustomCertificate", "CSC", "ClientTrustCertificate")]
    [Parameter(Mandatory=$False)]
    [string]$delete_ssl_cert,
    [Parameter(Mandatory=$False)]
    [switch]$restore_factory_defaults
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

# Function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

# Function to convert P12 cert to encoded base64 string

Function ConvertTo-PaddedBase64 {
    Param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [ValidateScript({Test-Path $_})]
        $File
    )
    $base64Str = [Convert]::ToBase64String([IO.File]::ReadAllBytes($File))
    $paddedStr = do {
        $base64Str[0..63] -join ''
        $base64Str = $base64Str[64..$($base64Str.length)]
    } until ($base64Str.Length -eq 0)
    $paddedStr | Out-String
}


# Function to export or import SSL cert

function export_import_ssl_cert
{
if ($export_ssl_cert)
{
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ExportSSLCertificate"
$JsonBody = @{"SSLCertType"= $export_ssl_cert} | ConvertTo-Json -Compress
$action_name = "Export"
[string]::Format("`n- INFO, performing {0} SSL cert operation for SSL cert type {1}", $action_name, $export_ssl_cert)
}
if ($import_ssl_cert)
{
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService/Actions/DelliDRACCardService.ImportSSLCertificate"
$fileExtension = [System.IO.Path]::GetExtension($cert_filename)
    if ($fileExtension -eq ".p12")
    {
    $CertFile = Get-Item $cert_filename
    [string]$get_file_content = ConvertTo-PaddedBase64 $CertFile.FullName
    }
    else 
    {
        try
        {
        $get_file_content = Get-Content $cert_filename -ErrorAction Stop | Out-String
        }
        catch
        {
        Write-Host "`n- FAIL, unable to locate cert filename '$cert_filename' for import operation"
        return
        }
    }

$JsonBody = @{"CertificateType"= $import_ssl_cert; "SSLCertificateFile" = $get_file_content}
    if ($passphrase)
    {
    $JsonBody["Passphrase"] = $passphrase
    }
$JsonBody = $JsonBody | ConvertTo-Json -Compress
$action_name = "Import"
[string]::Format("`n- INFO, performing {0} SSL cert operation for SSL cert type {1}", $action_name, $import_ssl_cert)
}

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
[String]::Format("- PASS, {0} SSL cert operation passed", $action_name)
}
else
{
[String]::Format("- FAIL, POST command failed for {2} SSL cert, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result, $action_name)
break
}


$post_result = $post_result.Content | ConvertFrom-Json
if ($export_ssl_cert)
{
[string]::format("`n- Exported SSL cert contents -`n")
$get_cert_content = $post_result.CertificateFile
$get_cert_content
try
{
#$get_cert_content | Out-File -FilePath $cert_filename -NoClobber -NoNewline
Set-Content -Path $cert_filename -Value $get_cert_content
}
catch
{
Write-Host "- FAIL, unable to copy cert contents to file ""$cert_filename"", already exists."
Write-Host
return
}
Write-Host "`n- INFO, SSL cert contents copied to ""$cert_filename"""
Write-Host
}


}

# Function to delete SSL cert

function delete_ssl_cert
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.DeleteSSLCertificate"
$JsonBody = @{"CertificateType"= $delete_ssl_cert} | ConvertTo-Json -Compress
$action_name = "Delete"
[string]::Format("`n- INFO, performing {0} SSL cert operation for SSL cert type {1}", $action_name, $delete_ssl_cert)


if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
[String]::Format("- PASS, {0} SSL cert operation passed", $action_name)
}
else
{
[String]::Format("- FAIL, POST command failed for {2} SSL cert, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result, $action_name)
break
}

}

function restore_factory_defaults
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DelliDRACCardService/Actions/DelliDRACCardService.SSLResetCfg"
$JsonBody = @{} | ConvertTo-Json -Compress
Write-Host "`n- INFO, restoring webserver certificate to factory defaults"
$action_name = "SSLResetCfg"


if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $post_result = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $post_result = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
[String]::Format("- PASS, {0} operation passed, webservices are restarting which may end the current web session(s)", $action_name)
}
else
{
[String]::Format("- FAIL, POST command failed for {2} action, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result, $action_name)
break
}

}


# Function to get supported SSL cert types for export or import operation

function get_supported_ssl_cert_types
{
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}
$get_result=$get_result.Content | ConvertFrom-Json
$action_name = "#DelliDRACCardService.ExportSSLCertificate"
$possible_values = "SSLCertType@Redfish.AllowableValues"
Write-Host "`n- Possible cert type values for export operation -`n"
$get_result.Actions.$action_name.$possible_values
Write-Host
$action_name = "#DelliDRACCardService.ImportSSLCertificate"
$possible_values = "CertificateType@Redfish.AllowableValues"
Write-Host "`n- Possible cert type values for import operation -`n"
$get_result.Actions.$action_name.$possible_values
Write-Host
}




# Run cmdlet

get_powershell_version 
setup_idrac_creds

# Check to validate iDRAC version detected supports this feature

$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DelliDRACCardService"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
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
    $get_result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    else
    {
    Ignore-SSLCertificates
    $get_result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    }
    catch
    {
    $RespErr
    return
    }
}
if ($get_result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
$get_actions = $get_result.Content | ConvertFrom-Json
$action_name="#DelliDRACCardService.ExportSSLCertificate"
    try
    {
    $test = $get_actions.Actions.$action_name.GetType()
    }
    catch
    {
    Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in.`n"
    return
    }
}
else
{
$status_code = $result.StatusCode
Write-Host "`n- FAIL, status code $status_code returned for GET request to validate iDRAC connection.`n"
return
}

if ($get_supported_ssl_cert_types)
{
get_supported_ssl_cert_types
}

elseif ($export_ssl_cert -or $import_ssl_cert -and $cert_filename)
{
export_import_ssl_cert
}

elseif ($delete_ssl_cert)
{
delete_ssl_cert
}

elseif ($restore_factory_defaults)
{
restore_factory_defaults
}

else
{
Write-Host "`n- FAIL, either incorrect parameter(s) used or missing required parameter(s)"
}


}















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
   iDRAC cmdlet using Redfish API to generate new iDRAC CSR.
.DESCRIPTION
   iDRAC cmdlet using Redfish API to generate new iDRAC CSR.

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - city: Generate iDRAC CSR, pass in city string value. Note: This argument is required to generate CSR.
   - state: Generate iDRAC CSR, pass in state string value. Note: This argument is required to generate CSR.
   - country: Generate iDRAC CSR, pass in common name string value. Note: This argument is required to generate CSR.
   - commonname: Generate iDRAC CSR, pass in common name string value. Note: This argument is required to generate CSR.
   - org: Generate iDRAC CSR, pass in organization string value. Note: This argument is required to generate CSR.
   - orgunit: Generate iDRAC CSR, pass in organization unit string value. Note: This argument is required to generate CSR.
   - email: Generate iDRAC CSR, pass in email string value. Note: This argument is optional to generate CSR.
   - subject_alt_name: Generate iDRAC CSR, pass in subject alt name value. Note: This argument is optional to generate CSR, if passing in multiple values use a comma separator.
   - export: Save the newly generated CSR to any location, pass in complete directory path and unique CSR filename. Note if this argument is not passed in, CSR content will be copied to a file named 'idrac_generated_csr.txt' in the directory you are running the cmdlet from.
   
.EXAMPLE
   Invoke-GenerateCsrREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_certs
   # This example will get current iDRAC certs.
.EXAMPLE
   Invoke-GenerateCsrREDFISH -idrac_ip 192.168.0.120 -get_certs 
   # This example will first prompt for iDRAC username/password using Get-Credential, then get current iDRAC certs. 
.EXAMPLE
   Invoke-GenerateCsrREDFISH -idrac_ip 192.168.0.120 -get_certs -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   # This example using iDRAC X-auth token session will get current iDRAC certs. 
.EXAMPLE
   Invoke-GenerateCsrREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -city Austin -state Texas -country US -commonname Test -org Test group -orgunit lab -email tester@email.com
   # This example will generate new iDRAC CSR.  
.EXAMPLE
   Invoke-GenerateCsrREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -city Austin -state Texas -country US -commonname Test -org Test group -orgunit lab -export 'C:\Users\Administrator\R650_iDRAC.csr'
   # This example will generate new iDRAC CSR and save the CSR content to 'C:\Users\Administrator\test.csr' location 
#>

function Invoke-GenerateCsrREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$False)]
    [string]$idrac_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [Parameter(Mandatory=$True)]
    [string]$city,
    [Parameter(Mandatory=$True)]
    [string]$state,
    [Parameter(Mandatory=$True)]
    [string]$country,
    [Parameter(Mandatory=$True)]
    [string]$commonname,
    [Parameter(Mandatory=$True)]
    [string]$org,
    [Parameter(Mandatory=$True)]
    [string]$orgunit,
    [Parameter(Mandatory=$False)]
    [string]$email,
    [Parameter(Mandatory=$False)]
    [string]$subject_alt_name,
    [Parameter(Mandatory=$False)]
    [string]$export
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

# Function to get current session Powershell version 

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

# Generate iDRAC CSR

function generate_CSR
{
Write-Host "`n- INFO, generating CSR for iDRAC $idrac_ip"
$JsonBody = @{"CertificateCollection"=@{"@odata.id"="/redfish/v1/Managers/iDRAC.Embedded.1/NetworkProtocol/HTTPS/Certificates"};"City"=$city;"CommonName" = $commonname;"Country"=$country;"Organization"=$org;"OrganizationalUnit"=$orgunit;"State"=$state}
if ($email)
{
$JsonBody["Email"] = $email
}

if ($subject_alt_name)
{
# NOTE: Code is commented out due to bug in iDRAC code. To set multiple subject alt names you have to pass in one string value using comma separator for the multiple values. 
#    if ($subject_alt_name.Contains(","))
#    {
#    $JsonBody["AlternativeNames"] = [array]($subject_alt_name.Split(","))
#    }
#    else
#    {
    $JsonBody["AlternativeNames"] = [array]($subject_alt_name)
#    }
}

$JsonBody = $JsonBody | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR"

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

if ($post_result.StatusCode -eq 200)
{
Write-Host "- PASS, POST command passed to generate CSR, status code 202 returned"
}
else
{
[String]::Format("- FAIL, POST command failed to generate CSR, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
return
}

$get_result = $post_result.Content | ConvertFrom-Json
Write-Host "- INFO, CSR generated file`n"
$get_result.CSRString 

if ($export)
{
$filename = $export
}
else
{
$filename = "idrac_generated_csr.txt"
}
try
{
Set-Content -Path $filename -Value $get_result.CSRString 
}
catch
{
Write-Host "- FAIL, unable to write CSR contents to a file"
return
}   
Write-Host "`n- INFO, CSR content also copied to file '$filename'"

}

# Run cmdlet

get_powershell_version 
setup_idrac_creds

# Check to validate iDRAC version detected supports this feature

$uri = "https://$idrac_ip/redfish/v1/CertificateService"
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

if ($result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
$get_actions = $result.Content | ConvertFrom-Json
$action_name = "#CertificateService.GenerateCSR"
$validate_supported_idrac = $get_actions.Actions.$action_name
    try
    {
    $test = $validate_supported_idrac.GetType()
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

if ($city -and $state -and $country -and $commonname -and $org -and $orgunit)
{
generate_csr
}
else
{
Write-Host "- WARNING, either missing or incorrect arguments detected"
}


}











<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 8.0

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
   iDRAC cmdlet using Redfish API with OEM extension to either get iDRAC, Lifecycle Controller(LC) or System attributes or set one or multiple iDRAC, LC or System attributes.
.DESCRIPTION
   iDRAC cmdlet using Redfish API with OEM extension to either get iDRAC, Lifecycle Controller(LC) or System attributes or set one or multiple iDRAC, LC or System attributes. 
   Parameters:
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in idrac username
   - idrac_password: Pass in idrac username password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - attribute_group: Supported values: lc, idrac  or system. Pass in "lc" to get Lifecycle controller attributes.
   - attribute_names: Pass in attribute name(s) you want to set. Make sure to type the attribute name exactly due to case senstive. Example: VNCServer.1.Enable will work but vncserver.1.enable will fail. When configuring multiple attributes, make sure to use a pipe (|) separator between each attribute name and surround the complete value with double quotes. 
   - attribute_values: Pass in attribute value(s) for the attribute(s) you want to set. Make sure the values align with the attribute names. See examples for more details. 
   - view_attribute_list_only: Get attributes and current values. You must also pass in attribute_group argument for the group type of attributes.  
   - get_specific_attribute: Pass in attribute name to only return details about this attribute. You must also pass in attribute_group argument. 
.EXAMPLE
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -attribute_group lc -view_attribute_list_only  
    This example will return LC attributes and their current values only.
.EXAMPLE
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -attribute_group lc -view_attribute_list_only 
    This example will first prompt for iDRAC username/password using Get-Credentials, then return LC attributes and their current values only.
.EXAMPLE
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -attribute_group lc -view_attribute_list_only -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
    This example will return LC attributes and their current values only using iDRAC X-auth token session. 
.EXAMPLE
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -attribute_group idrac -get_specific_attribute EmailAlert.1.Enable
    This example will return attribute details for only iDRAC attribute EmailAlert.1.Enable.
.EXAMPLE
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -attribute_group idrac -attribute_names "EmailAlert.2.Enable|IPv4.1.Address|EmailAlert.1.Enable" -attribute_values "Enabled|192.168.0.130|Enabled" 
    This example shows setting multiple iDRAC attributes. 
   #>

function Set-IdracLcSystemAttributesREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$False)]
    [string]$idrac_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [ValidateSet("idrac", "system", "lc")]
    [Parameter(Mandatory=$True)]
    [string]$attribute_group,
    [Parameter(Mandatory=$False)]
    [string]$attribute_names,
    [Parameter(Mandatory=$False)]
    [string]$attribute_values,
    [Parameter(Mandatory=$False)]
    [string]$get_specific_attribute,
    [Parameter(Mandatory=$False)]
    [switch]$view_attribute_list_only

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

$global:get_powershell_version = $null

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

# Setting up iDRAC credentials 

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

function get_attributes
{

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

if ($result.StatusCode -eq 200)
{
    #[String]::Format("- PASS, GET command passed, statuscode {0} returned successfully to get ""{1}"" attributes",$result.StatusCode, $attribute_group.ToUpper())
}
else
{
    [String]::Format("- FAIL, GET command failed to get attributes statuscode {0} returned",$result.StatusCode)
}

Write-Host

$get_all_attributes = $result.Content | ConvertFrom-Json | Select Attributes

if ($get_specific_attribute)
{
$current_value = $get_all_attributes.Attributes.$get_specific_attribute
if ($current_value -eq $null)
{
[String]::Format("- WARNING, unable to locate attribute $get_specific_attribute, confirm you are passing in correct string name")
return
}
else
{
Write-Host "- Attribute Name: $get_specific_attribute, Current Value: $current_value"
return
}

}

$get_all_attributes.Attributes


}

function set_attributes
{


$attribute_names_array = $attribute_names.Split("|")
$attribute_values_old = $attribute_values.Split("|")
$attribute_values_array = @()

foreach ($item in $attribute_values_old)
{
    try
    {
    $item = [int]$item
    $attribute_values_array += $item
    }
    catch
    {
    $attribute_values_array += $item
    }
}


$JsonBody = @{"Attributes"=@{}} 

function Zip($a1, $a2) {
    while ($a1) {
        $x, $a1 = $a1
        $y, $a2 = $a2
        $JsonBody["Attributes"][$x] = $y
    }
}



Zip $attribute_names_array $attribute_values_array

Write-Host "`n- INFO, cmdlet will set $attribute_group attribute(s):"
$JsonBody["Attributes"]
$JsonBody = $JsonBody | ConvertTo-Json -Compress


if ($attribute_names_array.Contains("IPv4.1.Address"))
{
$attribute_name_index = $attribute_names_array.IndexOf("IPv4.1.Address")
$new_static_ip = $attribute_values_array[$attribute_name_index]
}
elseif ($attribute_names_array.Contains("ipv4.1.address"))
{
$new_static_ip = $attribute_values_array[$attribute_name_index]
$attribute_name_index = $attribute_names_array.IndexOf("ipv4.1.address")
}
else
{
$attribute_name_index = "no"
}


# PATCH command to set attribute pending value

 if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
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
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}



if ($result1.StatusCode -eq 200)
{
    Start-Sleep 5
    [String]::Format("`n- PASS, statuscode {0} returned to successfully set ""{1}"" attribute(s)",$result1.StatusCode, $attribute_group.ToUpper())
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

if ($attribute_name_index -eq "no")
{
}
else
{
Write-Host "`n- INFO, static IP address change detected, will use new IP address to get current attribute values"
if ($attribute_group -eq "idrac")
{
$uri = "https://$new_static_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
}
elseif ($attribute_group -eq "lc")
{
$uri = "https://$new_static_ip/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes"
}
elseif ($attribute_group -eq "system")
{
$uri = "https://$new_static_ip/redfish/v1/Managers/System.Embedded.1/Attributes"
} 

}


Write-Host "`n- INFO, getting current $attribute_group attribute value(s) that were just changed`n"
Start-Sleep 15

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

$attribute_names_array = $attribute_names.Split("|")
$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes
foreach ($item in $attribute_names_array)
{
$current_value = $get_all_attributes.Attributes.$item
Write-Host "- Attribute Name: $item, Current Value: $current_value"
}


}


############
# Run code #
############

get_powershell_version 
setup_idrac_creds

# Code to check for supported iDRAC version installed

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
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
	    }
	    else
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API"
        $result
	    return
	    }



if ($attribute_group.ToLower() -eq "idrac")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
}
elseif ($attribute_group.ToLower() -eq "lc")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes"
}
elseif ($attribute_group.ToLower() -eq "system")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/System.Embedded.1/Attributes"
} 


if ($view_attribute_list_only -and $attribute_group -or $get_specific_attribute)
{
get_attributes
}
elseif ($attribute_group -and $attribute_names -and $attribute_values)
{
set_attributes
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}


}



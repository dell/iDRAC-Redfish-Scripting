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
   Cmdlet used to set one or multiple iDRAC, LC or System attributes. Or get current value of iDRAC, LC or System attributes using REDFISH API.
   IMPORTANT: Make sure you are using latest Powershell version 5 or newer to execute this cmdlet. Execute "Get-Host" to check the version.
.DESCRIPTION
   Cmdlet used to either set one or multiple iDRAC, LC or System attributes or get current value of iDRAC, LC or System attributes. 
   When setting attributes, you will be using "multiple_idrac_lc_system_attributes.txt" file. In this file, 
   make sure you use the exact format as the example is in the file (attribute name:attribute value|attribute name:attribute value).
   Also make sure you pass in exact name of the attribute and value since these are case sensitive. 
   Example: For attribute VNCServer.1.Enable, you must pass in "Enabled". Passing in "enabled" will fail.

   Parameters:
   - idrac_ip: pass in iDRAC IP
   - idrac_username: pass in idrac username
   - idrac_password: pass in idrac username password
   - attribute_group: supported values are: lc, idrac  or system.
     Pass in "lc" to get Lifecycle controller attributes. Pass in "idrac" to get iDRAC attributes. Pass in "system" to get System attributes.
   - file_path: pass in the directory path where "multiple_idrac_lc_system_attributes.txt" file is located.
   - view_attribute_list_only: pass in "y" to get attributes and current values
.EXAMPLE
    This example shows getting only Lifecycle Controller attributes and current values
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -attribute_group lc -view_attribute_list_only y 
.EXAMPLE
    This example shows setting all LC attributes listed in text file "multiple_idrac_lc_system_attributes.txt".
    Set-IdracLcSystemAttributesREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -attribute_group lc -file_path C:\Python27
   #>

   function Set-IdracLcSystemAttributesREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$attribute_group,
    [Parameter(Mandatory=$False)]
    [string]$file_path,
    [Parameter(Mandatory=$False)]
    [string]$view_attribute_list_only

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

# Setting up iDRAC credentials 

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


# Check for supported iDRAC version installed

$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    catch
    {
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



# GET command to get all attributes and current values

if ($attribute_group -eq "idrac")
{
$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
}
elseif ($attribute_group -eq "lc")
{
$u = "https://$idrac_ip/redfish/v1/Managers/LifecycleController.Embedded.1/Attributes"
}
elseif ($attribute_group -eq "system")
{
$u = "https://$idrac_ip/redfish/v1/Managers/System.Embedded.1/Attributes"
} 


$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
Write-Host

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes

# Check to see if return attributes only for cmdlet

if ($view_attribute_list_only -eq "y")
{
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, GET command passed, statuscode {0} returned successfully to get ""{1}"" attributes:",$result.StatusCode, $attribute_group.ToUpper())
    $get_all_attributes.Attributes
try 
{
    Remove-Item("attributes.txt") -ErrorAction Stop
    Write-Host "- WARNING, attributes.txt file detected, file deleted and will create new file with attributes and current values"
}
catch [System.Management.Automation.ActionPreferenceStopException] {
    Write-Host "- WARNING, attributes.txt file not detected, delete file not executed" 
}

Write-Host -ForegroundColor Yellow "`n- WARNING, Attributes also copied to ""attributes.txt"" file"
$final_all_attributes=$get_all_attributes.Attributes | ConvertTo-Json -Compress
foreach ($i in $final_all_attributes)
{
Add-Content attributes.txt $i
}
    return
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$write_to_file=Add-Content "$file_path\multiple_idrac_lc_system_attributes.txt"
}

if ($view_attribute_list_only -eq "n")
{
return
}


# Create hashtable for attribute names and values from text file


$input_key_values=Get-Content "$file_path\multiple_idrac_lc_system_attributes.txt"
$dict = @{}
$input_key_values.Split('|') |ForEach-Object {
    # Split each pair into key and value
    $key,$value = $_.Split(':')
    # Populate $Dictionary
    if ($value -match "^[\d\.]+$")
    {
    $value=[int]$value
    }
    $dict[$key] = $value
}


$dict_final=@{"Attributes"=""}
$dict_final.("Attributes")=$dict 
$JsonBody = $dict_final | ConvertTo-Json -Compress

# Create hashtable for setting attribute new values which will be used to compare against new values at the end of the script

$pending_dict=@{}

foreach ($i in $dict.GetEnumerator())
{
    $attribute_name = $i.Name
    $get_attribute_name=$get_all_attributes.Attributes | Select $attribute_name
    $get_attribute_value=$attribute_name
    #$attribute_value=$get_attribute_name.$get_attribute_value
    #$pending_value = $i.Value
    #Write-Host -ForegroundColor Yellow "- WARNING, attribute $attribute_name current value is: $attribute_value, setting pending value to: $pending_value"
    [String]::Format("- WARNING, attribute {0} current value is: {1}, setting new value to: {2}",$attribute_name,$get_attribute_name.$get_attribute_value,$i.Value)
    $pending_dict.Add($attribute_name,$i.Value)
}
Write-Host

#$u1 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios/Settings"

# PATCH command to set attribute pending value

$result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}
#$raw_content=$result1.RawContent | ConvertTo-Json -Compress


if ($result1.StatusCode -eq 200)
{
    #$code=$result1.StatusCode
    #Write-Host -ForegroundColor Green "- PASS, statuscode $code returned to successfully set attributes pending value"
    [String]::Format("- PASS, statuscode {0} returned to successfully set ""{1}"" attributes",$result1.StatusCode, $attribute_group.ToUpper())
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}


# GET command to verify new attribute values are set correctly 

$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"} 
Write-Host
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get ""{1}"" attributes",$result.StatusCode,$attribute_group.ToUpper())
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
}

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes
Write-Host
foreach ($i in $pending_dict.GetEnumerator())
{
$attribute_name = $i.Name
$get_attribute= $get_all_attributes.Attributes | Select $attribute_name
$get_attribute_value=$attribute_name
if ( $get_attribute.$get_attribute_value -eq $i.Value )
{
[String]::Format("- PASS, attribute {0} current value is successfully set to: {1}",$attribute_name,$get_attribute.$get_attribute_value)
}
else
{
[String]::Format("- FAIL, attribute {0} current value not successfully set to: {1}, current value is: {2}",$attribute_name,$i.Value,$get_attribute.$get_attribute_value)
}
}
}

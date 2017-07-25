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
   Cmdlet used to set multiple BIOS attributes or get current value of BIOS attributes using REDFISH API.
   IMPORTANT: Make sure you are using latest Powershell version 5 or newer to execute this cmdlet. Execute "Get-Host" to check the version.
.DESCRIPTION
   Cmdlet used to either set multiple BIOS attributes or get current value of BIOS attributes. 
   When setting multiple BIOS attributes, you will be using "multiple_bios_attributes.txt file". In this file, make sure you use the exact format as the example is in the file (attribute name:attribute value|attribute name:attribute value).
   Also make sure you pass in exact name of the attribute and value since these are case sensitive. 
   Example: For attribute MemTest, you must pass in "MemTest". Passing in "memtest" will fail.
   - idrac_ip, REQUIRED, pass in idrac IP
   - idrac_username, REQUIRED, pass in idrac user name
   - idrac_password, REQUIRED, pass in idrac password
   - file_path, OPTIONAL, pass in the absolute or full directory path where file "multiple_bios_attributes.txt" is located
   - view_attribute_list_only, OPTIONAL, this will return all attributes along with their current values
.EXAMPLE
    This example shows getting only BIOS attributes and current value
   .\redfish_set_one_bios_attribute -idrac_ip 192.168.0.120 -idrac_sername root -idrac_password calvin -view_attribute_list_only y 
.EXAMPLE
    This example shows setting all BIOS attributes listed in text file "bios_multiple_attributes.txt" which is located in "C:\Users\Administrator\Documents\WindowsPowerShell\Modules\Set-MultipleBIOSAttributesREDFISH" directory
   .\redfish_set_one_bios_attribute -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -file_path C:\Users\Administrator\Documents\WindowsPowerShell\Modules\Set-MultipleBIOSAttributesREDFISH
#>

function Set-MultipleBIOSAttributesREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
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


$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"

# GET command to get all BIOS attributes and current values

$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 
Write-Host

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes

# Check to see if return attributes only 

if ($view_attribute_list_only -eq "y")
{
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get attributes",$result.StatusCode)
    Write-Host
    $get_all_attributes.Attributes
    return
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
}

if ($view_attribute_list_only -eq "n")
{
return
}

# Create hashtable for attribute names and values from text file

#$input_key_values=Get-Content multiple_bios_attributes.txt
$input_key_values=Get-Content "$file_path\multiple_bios_attributes.txt"
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

# Create hashtable for attribute pending values which will be used to compare against new values at the end of the script

$pending_dict=@{}

foreach ($i in $dict.GetEnumerator())
{
    $attribute_name = $i.Name
    $get_attribute_name=$get_all_attributes.Attributes | Select $attribute_name
    $get_attribute_value=$attribute_name
    [String]::Format("- WARNING, attribute {0} current value is: {1}, setting pending value to: {2}",$attribute_name,$get_attribute_name.$get_attribute_value,$i.Value)
    $pending_dict.Add($attribute_name,$i.Value)
}
Write-Host

$u1 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios/Settings"

# PATCH command to set attribute pending value

$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json'

if ($result1.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned to successfully set attributes pending value",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}


$JsonBody = @{ "TargetSettingsURI" ="/redfish/v1/Systems/System.Embedded.1/Bios/Settings"
    } | ConvertTo-Json -Compress


$u2 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"

# POST command to create BIOS config job

$result1 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'
$raw_content=$result1.RawContent | ConvertTo-Json -Compress
$jobID_search=[regex]::Match($raw_content, "JID_.+?r").captures.groups[0].value
$job_id=$jobID_search.Replace("\r","")
Start-Sleep 3
if ($result1.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned to successfully create job: {1}",$result1.StatusCode,$job_id)
    Start-Sleep 5
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}


$u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to check job status of scheduled before rebooting the server

$result = Invoke-WebRequest -Uri $u3 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.JobState -eq "Scheduled")
{
[String]::Format("- PASS, {0} job ID marked as scheduled",$job_id)
}
else 
{
Write-Host
[String]::Format("- FAIL, {0} job ID not marked as scheduled",$job_id)
[String]::Format("- Extended error details: {0}",$overall_job_output)
Exit
}


$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power OFF the server

$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'


if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power OFF the server",$result1.StatusCode)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power ON the server

$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

Write-Host
Write-Host "- WARNING, cmdlet will now poll job ID every 15 seconds until marked completed"
Write-Host

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)

while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"

# GET command to loop query the job status until marked completed or failed

$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobState -eq "Failed")
{
Write-Host
[String]::Format("- FAIL, job marked as failed, detailed error info: {0}",$overall_job_output)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}
else
{
[String]::Format("- WARNING, current job status is: {0}",$overall_job_output.Message)
Start-Sleep 15
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds 
Write-Host "  Job completed in $final_completion_time"


$u6 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"

# GET command to verify new attribute values are set correctly 

$result = Invoke-WebRequest -Uri $u6 -Credential $credential -Method Get -UseBasicParsing 
Write-Host
if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get attributes",$result.StatusCode)
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
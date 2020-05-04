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
   Cmdlet using Redfish API with OEM extension to either get storage controllers, get controller encryption mode settings or set the storage controller key(enable encryption).
.DESCRIPTION
   Cmdlet Redfish API with OEM extension to either get storage controllers, get controller encryption mode settings or set the storage controller key(enable encryption) for LKM(Local Key Management).
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_storage_controllers: Pass in "y" to get current storage controller FQDDs for the server. Pass in "yy" to get detailed information for each storage controller
   - get_controller_encryption_mode_settings: Pass in the controller FQDD to get current controller encryption mode settings. Example, pass in "RAID.Integrated.1-1".
   - set_controller_key: Set the controller key, pass in the controller FQDD (Example, pass in "RAID.Slot.6-1"). You must also use parameters key_passphrase and key_id for setting controller key.
   - key_passphrase: Pass in unique key passpharse for setting controller key. Minimum length is 8 characters, must have at least 1 upper and 1 lowercase, 1 number and 1 special character Example "Test123##". Refer to Dell PERC documentation for more information.
   - key_id: Pass in unique key ID name for setting the controller key. Example H730key.
.EXAMPLE
   .\Invoke-StorageSetControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_controller_encryption_mode_settings RAID.Mezzanine.1-1
   This example will return current encryption mode information for storage controller.
.EXAMPLE
   .\Invoke-StorageSetControllerKeyREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -set_controller_key RAID.Mezzanine.1-1 -key_passphrase Pass123## -key_id test_key
   This example will set storage controller key for RAID.Mezzanine.1-1 controller.
#>

function Invoke-StorageSetControllerKeyREDFISH {

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_storage_controllers,
    [Parameter(Mandatory=$False)]
    [string]$get_controller_encryption_mode_settings,
    [Parameter(Mandatory=$False)]
    [string]$set_controller_key,
    [Parameter(Mandatory=$False)]
    [string]$key_passphrase,
    [Parameter(Mandatory=$False)]
    [string]$key_id
    )

################################
# Function to ignore SSL certs #
################################

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

#######################################
# Function to Setup iDRAC credentials #  
#######################################

function setup_idrac_creds
{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}

######################################
# Function to get Powershell version #
######################################

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


#############################################
#Function to get storage controller details #
#############################################

function get_storage_controller_details
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$result.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$get_result = $result.Content | ConvertFrom-Json
$number_of_controller_entries = $get_result.Members.Count
$count = 0
Write-Host
while ($count -ne $number_of_controller_entries)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
if ($result.StatusCode -ne 200)
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
$get_content = $get_content.Members[$count]
$get_content = [string]$get_content
$get_content = $get_content.Replace("@{@odata.id=","")
$get_content = $get_content.Replace('}',"")
$uri = "https://$idrac_ip"+$get_content
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
$get_content = $result.Content | ConvertFrom-Json
[String]::Format("- Detailed information for controller {0} -`n", $get_content.Id)
$result.Content | ConvertFrom-Json
Write-Host
$count+=1

}
Write-Host
return
}


#############################################################
#Function to get storage controller encryption mode details #
#############################################################

function get_controller_encryption_mode_settings
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_controller_encryption_mode_settings"
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
if ($result.StatusCode -eq 200)
{
    #
}
else
{
    [String]::Format("`n- FAIL, GET command failed to get storage controller encryption details, statuscode {0} returned",$result.StatusCode)
    return
}

$get_content = $result.RawContent
$regex = [regex] 'SecurityStatus.+?,'
$security_status = $regex.Matches($get_content).Value.Replace(",","")
$regex = [regex] 'EncryptionMode.+?,'
$encryption_mode = $regex.Matches($get_content).Value.Replace(",","")
$regex = [regex] 'EncryptionCapability.+?,'
$encryption_capability = $regex.Matches($get_content).Value.Replace(",","")
Write-Host "`n- Encryption information for storage controller $get_controller_encryption_mode_settings -`n"
$security_status
$encryption_mode
$encryption_capability
Write-Host
return
}


############################################
# Function to get storage controller FQDDs #
############################################

function get_storage_controllers
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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

if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$result.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_content = $result.Content

Write-Host
$regex = [regex] '/Storage/.+?"'
$allmatches = $regex.Matches($get_content)
$get_all_matches = $allmatches.Value.Replace('/Storage/',"")
$controllers = $get_all_matches.Replace('"',"")
Write-Host "- Server controllers detected -`n"
$controllers
Write-Host
return
}

############################################
# Function to set storage controller key #
############################################

function set_storage_controller_key
{

$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.SetControllerKey"
$JsonBody = @{"TargetFQDD"=$set_controller_key;"Key"=$key_passphrase;"Keyid"=$key_id} | ConvertTo-Json -Compress

try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 
    if ($result1.StatusCode -eq 202 -or $result1.StatusCode -eq 200)
    {
    $job_id = $result1.Headers.Location.Split("/")[-1]

    [String]::Format("`n- PASS, statuscode {0} returned successfully to set controller {1} key, {2} job ID created",$result1.StatusCode,$set_controller_key,$job_id)
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned to set controller key",$result1.StatusCode)
    return
    }


$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
if ($result.StatusCode -eq 200)
{
    #[String]::Format("`n- PASS, statuscode {0} returned to successfully query job ID {1}",$result.StatusCode,$job_id)
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
 
$overall_job_output = $result.Content | ConvertFrom-Json

if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
{
$job_type = "realtime_config"
Write-Host "`n- WARNING, set controller key real time job created, no server reboot needed to apply the changes"
}
if ($overall_job_output.JobType -eq "RAIDConfiguration")
{
$job_type = "staged_config"
Write-Host "`n- WARNING, set controller key staged job created, server reboot needed to apply the changes"
}

if ($job_type -eq "realtime_config")
{
    while ($overall_job_output.JobState -ne "Completed")
    {
    $uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id" 
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

    $overall_job_output=$result.Content | ConvertFrom-Json
        if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
        {
        Write-Host
        [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
        return
        }
        else
        {
        [String]::Format("- WARNING, job not marked completed, current status is: {0} Precent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
        Start-Sleep 10
        }
    }
Write-Host
Start-Sleep 10
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
check_controller_key_set
return
}

if ($job_type -eq "staged_config")
{
    while ($overall_job_output.Message -ne "Task successfully scheduled.")
    {
    $uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
 
    $overall_job_output=$result.Content | ConvertFrom-Json
    if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
    {
    Write-Host
    [String]::Format("- FAIL, job not marked as scheduled, detailed error info: {0}",$overall_job_output)
    return
    }
    else
    {
    [String]::Format("- WARNING, job not marked scheduled, current message is: {0}",$overall_job_output.Message)
    Start-Sleep 1
    }
    }
}
Write-Host "`n- PASS, $job_id successfully scheduled, rebooting server"



while ($overall_job_output.JobState -ne "Completed")
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
    {
    Write-Host
    [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
    return
    return
    }
    else
    {
    [String]::Format("- WARNING, job not marked completed, current status is: {0} Precent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
    Start-Sleep 30
    }
}
Start-Sleep 10
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
check_controller_key_set
return
}

########################################
# Function to check controller key set #
########################################

function check_controller_key_set
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$set_controller_key"
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
if ($result.StatusCode -eq 200)
{
    #
}
else
{
    [String]::Format("`n- FAIL, GET command failed to get storage controller encryption details, statuscode {0} returned",$result.StatusCode)
    return
}

$get_result = $result.RawContent
$regex = [regex] 'SecurityStatus.+?,'
$security_status = $regex.Matches($get_result).Value.Replace(",","").Split(":")[-1]
if ($security_status -eq '"SecurityKeyAssigned"')
{
Write-Host "`n- PASS, validated controller key is successfully set for controller $set_controller_key`n"
}
else
{
Write-Host "`n- FAIL, controller key not set for controller $set_controller_key, $security_status"
return
}
}


############
# Run code #
############

get_powershell_version 
setup_idrac_creds

# Code to check for supported iDRAC version installed

$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/"
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


if ($get_storage_controllers -eq "y" -or $get_storage_controllers -eq "Y")
{
get_storage_controllers
}
elseif ($get_storage_controllers -eq "yy" -or $get_storage_controllers -eq "YY")
{
get_storage_controller_details
}
elseif ($get_controller_encryption_mode_settings -ne "")
{
get_controller_encryption_mode_settings
}
elseif ($set_controller_key -and $key_passphrase -and $key_id)
{
set_storage_controller_key
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}

}


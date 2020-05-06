<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 4.0

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
   Cmdlet using Redfish with OEM extension to either get Support Assist (SA) license agreement info, accept end user license agreement (EULA), register SA or perform SA collection locally. NOTE: Before you perform SA local collection, the EULA must be accepted. 
.DESCRIPTION
   Cmdlet using Redfish with OEM extension to either get Support Assist (SA) license agreement info, accept end user license agreement (EULA), register SA or perform SA collection locally. NOTE: Before you perform SA local collection, the EULA must be accepted.  

   Supported parameters to pass in for cmdlet:
   
   - idrac_ip: Pass in iDRAC IP
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - get_SA_licence_agreement_info: Pass in "y" to get Support Assist license and registered current status.
   - accept_SA_license_agreement: Pass in "y" to accept Support Assist end user license agreement (EULA)
   - register_SA: Pass in "y" to register Support Assist Collection iDRAC feature. NOTE: You must also pass in city, company name, country, email, first name, last name, phone number, street, state and zip arguments to register. NOTE: iDRAC Service Module (iSM) must be installed and service running on the operating system before you register SA.
   - city: Pass in city name to register Support Assist. If passing in a value with whitespace, make sure to surround the value with double quotes. 
   - companyname: Pass in company name to register Support Assist. If passing in a value with whitespace, make sure to surround the value with double quotes.
   - country: Pass in country to register Support Assist. If passing in a value with whitespace, make sure to surround the value with double quotes.
   - email: Pass in email to register Support Assist
   - firstname: Pass in first name to register Support Assist
   - lastname: Pass in last name to register Support Assist
   - phonenumber: Pass in phone number to register Support Assist
   - street: Pass in street name to register Support Assist. If passing in a value with whitespace, make sure to surround the value with double quotes.
   - state: Pass in state to register Support Assist
   - zip: Pass in zip code to register Support Assist
   - execute_SA_collection: Perform Support Assist collection locally, Pass in a value for the type of data you want to collect for Support Assist collection. Supported values are: "0" for DebugLogs, "1" for HWData, "2" for OSAppData or "3" for TTYLogs. Note: You can pass in one value or multiple values to collect. If you pass in multiple values, use comma separator for the values and surround it with double quotes (Example: "0,3")

.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_SA_license_agreement_info y
   # This example will get iDRAC Support Assist license and register status
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -accept_SA_license_agreement y
   # This example will accept Support Assist license agreement
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -register_SA y -city Austin -companyname Dell -country US -email test@dell.com -firstname User -lastname Tester -phonenumber 512-111-5555 -street "511 street name" -state Texas -zip 78758
   # This example will register Support Assist feature for iDRAC
.EXAMPLE
   Invoke-SupportAssistCollectionLocalREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -execute_SA_collection "1,3"
   # This example will execute Support Assist collection locally capturing hardware data and storage logs. Once the job is marked completed, cmdlet will prompt user to download the Support Assist collection zip file.
#>

function Invoke-SupportAssistCollectionLocalREDFISH {

# Required, optional parameters needed to be passed in when cmdlet is executed

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_SA_license_agreement_info,
    [Parameter(Mandatory=$False)]
    [string]$accept_SA_license_agreement,
    [Parameter(Mandatory=$False)]
    [string]$register_SA,
    [Parameter(Mandatory=$False)]
    [string]$city,
    [Parameter(Mandatory=$False)]
    [string]$companyname,
    [Parameter(Mandatory=$False)]
    [string]$country,
    [Parameter(Mandatory=$False)]
    [string]$email,
    [Parameter(Mandatory=$False)]
    [string]$firstname,
    [Parameter(Mandatory=$False)]
    [string]$lastname,
    [Parameter(Mandatory=$False)]
    [string]$phonenumber,
    [Parameter(Mandatory=$False)]
    [string]$street,
    [Parameter(Mandatory=$False)]
    [string]$state,
    [Parameter(Mandatory=$False)]
    [string]$zip,
    [Parameter(Mandatory=$False)]
    [string]$execute_SA_collection
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

# Function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


# Function Get Support Assist current license agreement information

function get_support_assist_license_agreement
{
Write-Host "`n- Current Support Assist End User License Agreement Information -`n"
$JsonBody = @{} | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistGetEULAStatus"

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

if ($post_result.StatusCode -eq 200)
{
}
else
{
[String]::Format("- FAIL, POST command failed to GET SA license info, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
break
}


$post_result = $post_result.Content | ConvertFrom-Json
$post_result_final = $post_result
$register_status = $post_result_final.IsRegistered
$get_key = "@Message.ExtendedInfo"

if ($post_result_final.$get_key.Message[0].Contains("License") -or $post_result_final.$get_key.Message[0].Contains("license"))
{
$license_message = $post_result_final.$get_key.Message[0]
Write-Host "IsRegistered  : $register_status"
Write-Host "LicenseStatus : $license_message"
}
else
{
$license_message = $post_result_final.$get_key.Message[1]
Write-Host "IsRegistered  : $register_status"
Write-Host "LicenseStatus : $license_message"
}
}

# Function accept support assist license agreement

function accept_support_assist_license_agreement
{

$JsonBody = @{} | ConvertTo-Json -Compress
$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistAcceptEULA"

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


if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
Write-Host "`n- PASS, POST command passed to accept Support Assist license agreement (EULA)`n"
}
else
{
[String]::Format("- FAIL, POST command failed to accept SA license, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
break
}

}

# Function to register Support Assist feature

function register_support_assist_feature
{

# Check if iSM is installed and running in the OS

$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
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
    Write-Host
    $RespErr
    break
    }

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes
$get_iSM_running_status = $get_all_attributes.Attributes | Select "ServiceModule.1.ServiceModuleState"
$get_OS_BMC_state = $get_all_attributes.Attributes | Select "OS-BMC.1.AdminState"
$attribute_name = "ServiceModule.1.ServiceModuleState"
if ($get_iSM_running_status.$attribute_name -eq "Not Running")
{
Write-Host "`n- WARNING, iDRAC Service Module(iSM) is either not installed or service is not running in the Operating System"
break
}

# iDRAC attribute OS-BMC admin state must be enabled to register iSM

$attribute_name = "OS-BMC.1.AdminState"
if ($get_OS_BMC_state.$attribute_name -eq "Disabled")
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Attributes"
$JsonBody = @{"Attributes"=@{"OS-BMC.1.AdminState" = "Enabled"}}
$JsonBody = $JsonBody | ConvertTo-Json -Compress
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Patch -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Patch -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    break
    } 
    }

# Create body payload for POST command

$JsonBody = @{}

if ($companyname)
{
$JsonBody["CompanyName"] = $companyname
}
if ($country)
{
$JsonBody["Country"] = $country
}
if ($email)
{
$JsonBody["PrimaryEmail"] = $email
}
if ($firstname)
{
$JsonBody["PrimaryFirstName"] = $firstname
}
if ($lastname)
{
$JsonBody["PrimaryLastName"] = $lastname
}
if ($phonenumber)
{
$JsonBody["PrimaryPhoneNumber"] = $phonenumber
}
if ($street)
{
$JsonBody["Street1"] = $street
}
if ($city)
{
$JsonBody["City"] = $city
}
if ($state)
{
$JsonBody["State"] = $state
}
if ($zip)
{
$JsonBody["Zip"] = $zip
}

Write-Host "`n- Keys and Values being passed in for POST action 'SupportAssistRegister' -`n"
$JsonBody

$JsonBody = $JsonBody | ConvertTo-Json -Compress

$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistRegister"

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


if ($post_result.StatusCode -eq 200 -or $post_result.StatusCode -eq 202)
{
Write-Host "`n- PASS, POST command passed to register Support Assist"
break
}
else
{
[String]::Format("- FAIL, POST command failed to register Support Assist, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode, $post_result)
return
}

}


# Function to execute Support Assist collection

$Global:job_id = $null

function execute_support_assist_collection
{

# Create body payload for POST command


if ($execute_SA_collection.Contains(","))
{
$string_split = $execute_SA_collection.Split(",")
$JsonBody = @{"ShareType"="Local";"DataSelectorArrayIn"=''}
$data_selector_array = @()
[System.Collections.ArrayList]$data_selector_array = $data_selector_array
    foreach ($item in $string_split)
    {
        if ($item -eq 0)
        {
        $data_selector_array+="DebugLogs"
        }
        if ($item -eq 1)
        {
        $data_selector_array+="HWData"
        }
        if ($item -eq 2)
        {
        $data_selector_array+="OSAppData"
        }
        if ($item -eq 3)
        {
        $data_selector_array+="TTYLogs"
        }
    }
$JsonBody["DataSelectorArrayIn"] = $data_selector_array
Write-Host "`n- Keys and Values being passed in for POST action 'SupportAssistCollection' -`n"
$JsonBody
$JsonBody = $JsonBody | ConvertTo-Json -Compress
}
else
{
$JsonBody = @{"ShareType"="Local";"DataSelectorArrayIn"=[System.Collections.ArrayList]@()}
    if ($execute_SA_collection -eq 0)
    {
    $JsonBody["DataSelectorArrayIn"]+="DebugLogs"
    }
    if ($execute_SA_collection -eq 1)
    {
    $JsonBody["DataSelectorArrayIn"]+="HWData"
    }
    if ($execute_SA_collection -eq 2)
    {
    $JsonBody["DataSelectorArrayIn"]+="OSAppData"
    }
    if ($execute_SA_collection -eq 3)
    {
    $JsonBody["DataSelectorArrayIn"]+="TTYLogs"
    }

Write-Host "`n- Keys and Values being passed in for POST action 'SupportAssistCollection' -`n"
$JsonBody
$JsonBody = $JsonBody | ConvertTo-Json -Compress
}


$uri = "https://$idrac_ip/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.SupportAssistCollection"

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

if ($post_result.StatusCode -eq 202 -or $post_result.StatusCode -eq 200)
{
    $job_id_search=$post_result.Headers['Location']
    $Global:job_id=$job_id_search.Split("/")[-1]
    [String]::Format("`n- PASS, statuscode {0} returned successfully for POST command to create update job ID '{1}'",$post_result.StatusCode, $Global:job_id)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned. Detail error message: {1}",$post_result.StatusCode,$post_result)
    return
}

}



function loop_job_status
{

$get_time_old=Get-Date -DisplayHint Time
$start_time = Get-Date

$end_time = $start_time.AddMinutes(50)
$force_count=0
Write-Host "- WARNING, script will now loop polling the job status every 30 seconds until marked completed`n"
while ($true)
{
$loop_time = Get-Date
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$Global:job_id"

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
    Write-Host
    $RespErr
    break
    }
    try
    {
    $SA_report_file_location = $result.Headers.Location
    }
    catch
    {
    Write-Host "- FAIL, unable to locate file location in headers output"
    break
}
$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.Message.Contains("Fail") -or $overall_job_output.Message.Contains("Failed") -or $overall_job_output.Message.Contains("fail") -or $overall_job_output.Message.Contains("failed") -or $overall_job_output.Message.Contains("already"))
{
Write-Host
[String]::Format("- FAIL, job id $Global:job_id marked as failed, error message: {0}",$overall_job_output.Message)
break
}
elseif ($overall_job_output.Message.Contains("partially") -or $overall_job_output.Message.Contains("part"))
{
Write-Host
[String]::Format("- WARNING, job id $Global:job_id completed with issues, check iDRAC Lifecyle Logs for more details. Final job message: {0}",$overall_job_output.Message)
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$Global:job_id' successfully marked as completed"
Write-Host "`nSupport Assist collection job execution time:"
$final_completion_time
Write-Host "`n- URI Support Assist collection file location: $SA_report_file_location`n"
$user_answer = Read-Host -Prompt "`n- Would you like to use default browser to download SA collection file now? Type 'y' for yes or 'n' for no"
    if ($user_answer.ToLower() -eq "y")
    {
    start https://$idrac_ip/redfish/v1/Dell/sacollect.zip
    Write-Host "`n- User selected to download the SA collection file now, check your default browser session"
    break
    }
    elseif ($user_answer.ToLower() -eq "n")
    {
    Write-Host "`n- User selected to not download the SA collection file. SA collection file can still be accessed by executing a GET on URI 'https://<idrac_ip>/redfish/v1/Dell/sacollect.zip'"
    break
    }
    else
    {
    return
    }
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 50 minutes has been reached before marking the job completed"
break
}
elseif ($overall_job_output.Message -eq "The SupportAssist Collection Operation is completed successfully." -or $overall_job_output.Message -eq  "Job completed successfully." -or $overall_job_output.Message.Contains("complete"))
{
$get_current_time=Get-Date -DisplayHint Time
$final_time=$get_current_time-$get_time_old
$final_completion_time=$final_time | select Minutes,Seconds
Write-Host "`n- PASS, job ID '$Global:job_id' successfully marked as completed"
Write-Host "`nSupport Assist collection job execution time:"
$final_completion_time
Write-Host "`n- URI Support Assist collection file location: $SA_report_file_location`n"
$user_answer = Read-Host -Prompt "`n- Would you like to use default browser to download SA collection file now? Type 'y' for yes or 'n' for no"

    if ($user_answer.ToLower() -eq "y")
    {
    start https://$idrac_ip/redfish/v1/Dell/sacollect.zip
    Write-Host "`n- User selected to download the SA collection file now, check your default browser session"
    break
    }
    elseif ($user_answer.ToLower() -eq "n")
    {
    Write-Host "`n- User selected to not download the SA collection file. SA collection file can still be accessed by executing a GET on URI 'https://<idrac_ip>/redfish/v1/Dell/sacollect.zip'"
    break
    }
    else
    {
    break
    }
}
else
{
Write-Host "- Job ID '$Global:job_id' not marked completed, checking job status again"
Start-Sleep 30
}

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
    Write-Host
    $RespErr
    return
    }
if ($get_result.StatusCode -eq 200 -or $result.StatusCode -eq 202)
{
$get_actions = $get_result.Content | ConvertFrom-Json
$support_assist_collection_action_name = "#DellLCService.SupportAssistCollection"
$validate_supported_idrac = $get_actions.Actions.$support_assist_collection_action_name
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
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API or incorrect iDRAC user credentials passed in`n"
return
}


if ($get_SA_license_agreement_info.ToLower() -eq "y")
{
get_support_assist_license_agreement
}

elseif ($accept_SA_license_agreement.ToLower() -eq "y")
{
accept_support_assist_license_agreement
}

elseif ($register_SA.ToLower() -eq "y")
{
register_support_assist_feature
}

elseif ($execute_SA_collection)
{
execute_support_assist_collection
loop_job_status
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s)"
}




}







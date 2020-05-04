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
  Cmdlet used to perform a repository update from a supported network share
.DESCRIPTION
   Cmdlet used to perform a repository update from a supported network share. Recommended to use HTTP share "downloads.dell.com" repository for updates or you can create and use a custom repository using Dell Repository Manager (DRM) utility.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC password
   - get_firmware_versions_only: Pass in "y" to get current firmware versions of devices in the server.
   - get_repo_update_list: Pass in "y" to get device firmware versions that can be updated from the repository you are using.
   - install_from_repository: Pass in "y" to perform installation from repository. You must also pass in other required parameters needed to perform this operation. See -examples for examples of executing install from repository.
   - network_share_IPAddress: Pass in IP address of the network share which contains the repository. Domain name string is also valid to pass in.
   - ShareName: Pass in the network share name of the repository.
   - ShareType: Pass in share type of the network share. Supported network shares are: NFS, CIFS, HTTP and HTTPS
   - Username: Name of your username that has access to CIFS share. REQUIRED only for CIFS
   - Password: Name of your user password that has access to CIFS share. REQUIRED only for CIFS
   - IgnoreCertWarning: Supported values are Off and On. This argument is only supported if using HTTPS for share type'
   - ApplyUpdate: Pass in True if you want to apply the updates. Pass in False will not apply updates. NOTE: This argument is optional. If you don't pass in the argument, default value is True.
   - RebootNeeded: Pass in True to reboot the server immediately to apply updates which need a server reboot. False means the updates will get staged but not get applied until next manual server reboot. NOTE: This argument is optional. If you don't pass in this argument, default value is False
   - catalogFile: Name of the catalog file on the repository. If the catalog file name is Catalog.xml on the network share, you don't need to pass in this argument
 

.EXAMPLE
   Invoke-InstallFromRepositoryOemREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_firmware_versions_only y, this example will get current firmware versions for the devices in the server.
.EXAMPLE
   Invoke-InstallFromRepositoryOemREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_repo_update_list y, this example will check the Catalog.xml file on the repository and compare against current FW versions in the server. If there is a FW version difference detected, it will report it in the output. It's recommended to check the Catalog.xml for version differences before applying updates.
.EXAMPLE
   Invoke-InstallFromRepositoryOemREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -install_from_repository y -ShareType HTTP -network_share_IPAddress 143.166.147.76 -ApplyUpdate True -RebootNeeded True, this example will perform repository update using HTTP share which contains the repository. This will immediately apply the updates and reboot the server if needed to apply updates. NOTE: This example is using Dell's HTTP repository which is recommended to be used. If you don't use this repository, you will need to use Dell Repository Manager (DRM) utility to create a custom repository.
.EXAMPLE
   Invoke-InstallFromRepositoryOemREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -install_from_repository y -ShareType NFS -network_share_IPAddress 192.168.0.130 -ShareName /nfs -ApplyUpdate True -RebootNeeded True, this example will perform repository update using NFS share which contains custom repository. This will imediately apply the udpates and reboot the server if needed to apply updates.
#>

function Invoke-InstallFromRepositoryOemREDFISH {


param(
    [Parameter(Mandatory=$True)]
    $idrac_ip,
    [Parameter(Mandatory=$True)]
    $idrac_username,
    [Parameter(Mandatory=$True)]
    $idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_firmware_versions_only,
    [Parameter(Mandatory=$False)]
    [string]$get_repo_update_list,
    [Parameter(Mandatory=$False)]
    [string]$install_from_repository,
    [Parameter(Mandatory=$False)]
    [string]$network_share_IPAddress,
    [Parameter(Mandatory=$False)]
    [string]$ShareName,
    [Parameter(Mandatory=$False)]
    [string]$ShareType,
    [Parameter(Mandatory=$False)]
    [string]$Username,
    [Parameter(Mandatory=$False)]
    [string]$Password,
    [Parameter(Mandatory=$False)]
    [string]$IgnoreCertWarning,
    [Parameter(Mandatory=$False)]
    [string]$ApplyUpdate,
    [Parameter(Mandatory=$False)]
    [string]$RebootNeeded,
    [Parameter(Mandatory=$False)]
    [string]$catalogFile
    )



# Function to igonre SSL certs

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

# function to get Powershell version

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}


# Function to get firmware versions only

function get_firmware_versions
{
Write-Host
Write-Host "--- Getting Firmware Inventory For iDRAC $idrac_ip ---"
Write-Host

$expand_query ='?$expand=*($levels=1)'
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$expand_query"
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
$get_fw_inventory = $get_result.Content | ConvertFrom-Json
$get_fw_inventory.Members

return
}


# Function to get repo update list

function get_repo_update_list
{
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.GetRepoBasedUpdateList"
$JsonBody = @{} | ConvertTo-Json -Compress
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
$post_result_search=$post_result.Content
$post_result_search = $post_result_search.Split("<")
$post_result_search = $post_result_search.Replace(">\n","")
$post_result_search
}




# Function install from repository

function install_from_repository
{
$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"
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
$get_job_id_uris = $get_result.Content | ConvertFrom-Json
$current_job_ids = @()
foreach ($item in $get_job_id_uris.Members)
{
$convert_to_string = [string]$item
$get_job_id = $convert_to_string.Split("/")[-1].Replace("}","")
$current_job_ids += $get_job_id
}


$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellSoftwareInstallationService/Actions/DellSoftwareInstallationService.InstallFromRepository"
$JsonBody= @{}

if ( $network_share_IPAddress ) 
{
$JsonBody["IPAddress"] = $network_share_IPAddress
}
if ( $ShareType ) 
{
$JsonBody["ShareType"] = $ShareType
}
if ( $ShareName ) 
{
$JsonBody["ShareName"] = $ShareName
}
if ( $Username ) 
{
$JsonBody["UserName"] = $Username
}
if ( $Password ) 
{
$JsonBody["Password"] = $Password
}
if ( $IgnoreCertWarning ) 
{
$JsonBody["IgnoreCertWarning"] = $IgnoreCertWarning
}
if ( $ApplyUpdate ) 
{
$JsonBody["ApplyUpdate"] = $ApplyUpdate
}
if ( $RebootNeeded ) 
{
    if ( $RebootNeeded -eq "True")
    {
    $JsonBody["RebootNeeded"] = $true
    $reboot_needed_flag = "True"
    }
    if ( $RebootNeeded -eq "False")
    {
    $JsonBody["RebootNeeded"] = $false
    $reboot_needed_flag = "False"
    }
}

if ( $CatalogFile ) 
{
$JsonBody["CatalogFile"] = $CatalogFile
}

Write-Host "`n- WARNING, arguments and values passed in for Action 'DellSoftwareInstallationService.InstallFromRepository'"
foreach ($item in $JsonBody)
{
$item    
}

$JsonBody = $JsonBody| ConvertTo-Json -Compress
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
        Write-Host "`n- PASS, POST command passed for OEM Action 'InstallFromRepository', status code 202 returned"
        }
try
{
$repo_job_id = $post_result.Headers["Location"].Split("/")[-1]
}
catch
{
Write-Host "`n- FAIL, unable to locate job ID URI in POST headers output"
return
}
Write-Host "- PASS, repository job ID '$repo_job_id' successfully created, cmdlet will loop checking the job status until marked completed"

$start_time=Get-Date -DisplayHint Time
Start-Sleep 5
$message_count = 1

while ($true)
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$repo_job_id"
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
if ($overall_job_output.JobState -eq "Completed")
{
break
}
elseif ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
    {
    Write-Host
    [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
    return
    }
elseif ($overall_job_output.Message -eq "Package successfully downloaded." -and $message_count -eq 1)
{
Write-Host "`n- WARNING, repository package successfully downloaded. If firmware version difference detected for any device, update job ID will get created`n"
$message_count += 1
}
else
    {
    $get_current_time=Get-Date -DisplayHint Time
    $get_time_query=$get_current_time - $start_time
    $current_job_execution_time = [String]::Format("{0}:{1}:{2}",$get_time_query.Hours,$get_time_query.Minutes,$get_time_query.Seconds)
    [String]::Format("- WARNING, repository job ID {0} not marked completed, current status: {1}",$repo_job_id,$overall_job_output.Message)
    Start-Sleep 10
    }
}

Start-Sleep 3
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$repo_job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$repo_job_id"
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


$uri = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"
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
$get_job_id_uris_new = $result.Content | ConvertFrom-Json
$latest_job_ids = @()
foreach ($item in $get_job_id_uris_new.Members)
{
$convert_to_string = [string]$item
$get_job_id_new = $convert_to_string.Split("/")[-1].Replace("}","")
$latest_job_ids += $get_job_id_new

}
[System.Collections.ArrayList]$latest_job_ids = $latest_job_ids
$latest_job_ids.Remove($repo_job_id)
$new_update_job_ids = @()


foreach ($item in $latest_job_ids)
{
    if  ($current_job_ids -notcontains $item)
    {
    $new_update_job_ids += $item
    }
}
if ($new_update_job_ids.Count -eq 0)
{
Write-Host "- WARNING, no update job id(s) created. All server components firmware version match the firmware version packages on the repository"
return
}

if ($reboot_needed_flag -eq "False")
{
Write-Host "`n- WARNING, 'RebootNeeded' argument set to False, no reboot executed. Update job id(s) are scheduled and will execute on next server manual reboot`n"
return
}
 
Write-Host "- WARNING, update job(s) created due to firmware version difference detected. Cmdlet will now loop through each update job ID until all are marked completed"
Write-Host "- WARNING, if iDRAC firmware version change detected, this update job will execute last`n"

foreach ($item in $new_update_job_ids)
{   
while ($true)
{
$RID_search = [string]$item
if ($RID_search.Contains("RID"))
{
break
}

$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$item"
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
    Write-Host "`n- WARNING, script will exit due to job failure detected. Check the overall job queue for status on any other update jobs which were also executed."
    return
    }
elseif ($overall_job_output.JobState -eq "Completed")
{
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$item)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$item"
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
break
}

else
    {
    [String]::Format("- WARNING, update job ID {0} not marked completed, current status: {1}",$item,$overall_job_output.Message)
    Start-Sleep 10
    }
}
}



Write-Host "`n- Execution of 'InstallFromRepositoryOemREDFISH' cmdlet complete -`n"
}




# Run cmdlet

get_powershell_version 
setup_idrac_creds


# Code to check for supported iDRAC version installed

$query_parameter = "?`$expand=*(`$levels=1)" 
$uri = "https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory$query_parameter"
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
}
else
{
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API`n"
$get_result
return
}




if ($get_firmware_versions_only -eq "y" -or $get_firmware_versions_only -eq "Y")
{
get_firmware_versions
}

elseif ($get_repo_update_list -eq "y" -or $get_repo_update_list -eq "Y")
{
get_repo_update_list
}

elseif ($install_from_repository -eq "y" -or $install_from_repository -eq "Y")
{
install_from_repository
}

else
{
Write-Host "- FAIL, either incorrect parameter(s) used or missing required parameters(s)"
}


}


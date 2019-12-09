<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0
Copyright (c) 2018, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>




<#
.Synopsis
   Cmdlet used to either get storage controllers, get external enclosusres, get enclosure asset tag or set enclosure asset tag
.DESCRIPTION
   Cmdlet used to either get storage controllers, get external enclosusres, get enclosure asset tag or set enclosure asset tag using iDRAC Redfish API.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_storage_controllers: Pass in "y" to get current storage controller FQDDs for the server. Pass in "yy" to get detailed information for each storage controller
   - get_external_enclosures: Pass in the controller FQDD to get external enclosures. Example, pass in "RAID.Integrated.1-1".
   - get_enclosure_details: Pass in external enclosure FQDD to get detailed information. Example, pass in "Enclosure.External.1-0:RAID.Slot.5-1"
   - get_enclosure_asset_tag: Pass in external enclosure FQDD to get current asset tag. Example, pass in "Enclosure.External.1-0:RAID.Slot.5-1"
   - set_enclosure_asset_tag: Pass in external enclosure FQDD you want to set the asset tag for. Example, pass in "Enclosure.External.1-0:RAID.Slot.5-1. You must also pass in asset_tag and job_type parameters when setting asset tag"
   - asset_tag: Pass in new value to set asset tag.
   - job_type: Pass in "r" to perform a realtime config job, no host reboot needed to apply config changes. Pass in "s" to perform a staged config job which will reboot the server to apply changes.
.EXAMPLE
   .\Invoke-DeleteVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_storage_controllers y
   This example will return storage controller FQDDs for the server.
.EXAMPLE
   .\Invoke-DeleteVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -delete_virtual_disk Disk.Virtual.0:RAID.Slot.6-1
   This example will delete virtual disk Disk.Virtual.0:RAID.Slot.6-1.
#>

function Invoke-SetExternalEnclosureAssetTagREDFISH {

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
    [string]$get_external_enclosures,
    [Parameter(Mandatory=$False)]
    [string]$get_enclosure_details,
    [Parameter(Mandatory=$False)]
    [string]$get_enclosure_asset_tag,
    [Parameter(Mandatory=$False)]
    [string]$set_enclosure_asset_tag,
    [Parameter(Mandatory=$False)]
    [string]$asset_tag,
    [Parameter(Mandatory=$False)]
    [string]$job_type
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


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


if ($get_external_enclosures -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Chassis"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}

$count=0
$z=$result.Content | ConvertFrom-Json
$zz=$z.Members
Write-Host "`n- External enclosures detected for storage controller $get_external_enclosures -`n"
    foreach ($item in $zz)
    {
    $i=[string]$item
        if ($i.Contains($get_external_enclosures) -and $i.Contains("External"))
        {
        $i=$i.Split("/")[-1]
        $i.Replace("}","")
        $count++
        }
    }

    if ($count -eq 0)
    {
    Write-Host "- WARNING, no external enclosures detected for storage controller $get_external_enclosures"
    }

return

}

if ($get_enclosure_asset_tag -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Chassis/$get_enclosure_asset_tag"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$z=$result.Content | ConvertFrom-Json
$asset_tag=$z.AssetTag
if ($asset_tag -eq "")
{
Write-Host "`n- WARNING, current asset tag for external enclosure $get_enclosure_asset_tag is blank"
}
else
{
Write-Host "`n- WARNING, current asset tag for external enclosure $get_enclosure_asset_tag is: '$asset_tag'"
}

return
}

if ($get_enclosure_details -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Chassis/$get_enclosure_details"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
Write-Host "`n- Detailed information for external enclosure $get_enclosure_details -"
$z=$result.Content | ConvertFrom-Json
$z

return
}


if ($get_storage_controllers -eq "yy")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$result.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$z=$result.Content | ConvertFrom-Json
$number_of_controller_entries=$z.Members.Count
$count=0
while ($count -ne $number_of_controller_entries)
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
if ($result.StatusCode -ne 200)
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$z=$result.Content | ConvertFrom-Json
$z=$z.Members[$count]
$z=[string]$z
$z=$z.Replace("@{@odata.id=","")
$z=$z.Replace('}',"")
$u="https://$idrac_ip"+$z
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$r.Content | ConvertFrom-Json
Write-Host
$count+=1

}
return
}


if ($get_storage_controllers -eq "y")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
try
{
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host "`n- WARNING, current iDRAC version installed doesn't support this feature using Redfish"
return
}

if ($r.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$r.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$a=$r.Content

Write-Host
$regex = [regex] '/Storage/.+?"'
$allmatches = $regex.Matches($a)
$z=$allmatches.Value.Replace('/Storage/',"")
$controllers=$z.Replace('"',"")
Write-Host "- Storage controllers detected -`n"
$controllers
Write-Host
return
}


if ($set_enclosure_asset_tag -ne "" -and $asset_tag -ne "" -and $job_type -ne "")
{
$u1 = "https://$idrac_ip/redfish/v1/Chassis/$set_enclosure_asset_tag/Settings"

$JsonBody = @{ "AssetTag" = $asset_tag
    } | ConvertTo-Json -Compress

try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}

if ($result1.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to set pending asset tag value to '{1}' for external enclosure '{2}'",$result1.StatusCode,$asset_tag,$set_enclosure_asset_tag)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned, unable to set asset tag pending value",$result1.StatusCode)
    Write-Host "- Detailed error message results: $result1"
    return
}
}
else
{
Write-Host "`n- FAIL, when setting asset tag, make sure to pass in parameters: set_enclosure_asset_tag, asset_tag and job_type"
return
}



if ($job_type -eq "r")
{
$JsonBody = @{ "@Redfish.SettingsApplyTime" = @{"ApplyTime"="Immediate"}} | ConvertTo-Json -Compress
try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$job_id=$result1.Headers['Location'].Split("/")[-1]
if ($result1.StatusCode -eq 202)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to create real time config job ID '{1}'",$result1.StatusCode,$job_id)
    Start-Sleep 5
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned, unable to create config job ID",$result1.StatusCode)
    return
}
while ($overall_job_output.JobState -ne "Completed")
{

$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
try
{
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
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
[String]::Format("- WARNING, job not marked completed, current status is: {0} Percent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
Start-Sleep 3
}
}

[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Start-Sleep 60
Write-Host "`n- Detailed final job status results:"
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
try
{
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}

$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output

$u = "https://$idrac_ip/redfish/v1/Chassis/$set_enclosure_asset_tag"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$z=$result.Content | ConvertFrom-Json
$asset_tag_new=$z.AssetTag

if ($asset_tag_new -eq $asset_tag)
{
Write-Host "- PASS, asset tag for '$set_enclosure_asset_tag' successfully set to '$asset_tag_new'"
}
else
{
Write-Host "- FAIL, asset tag for '$set_enclosure_asset_tag' not set to '$asset_tag', current asset tag value is '$asset_tag_new'"
return
}

return
}



if ($job_type -eq "s")
{
$u1 = "https://$idrac_ip/redfish/v1/Chassis/$set_enclosure_asset_tag/Settings"

$JsonBody = @{ "@Redfish.SettingsApplyTime" = @{"ApplyTime"="OnReset"}} | ConvertTo-Json -Compress
try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$job_id=$result1.Headers['Location'].Split("/")[-1]
if ($result1.StatusCode -eq 202)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to create staged config job ID '{1}'",$result1.StatusCode,$job_id)
    Start-Sleep 60
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned, unable to create config job ID",$result1.StatusCode)
    return
}

while ($overall_job_output.Message -ne "Task successfully scheduled.")
{

$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}

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
Write-Host "- PASS, $job_id successfully scheduled, rebooting server"

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$z=$result.Content | ConvertFrom-Json
$host_power_state = $z.PowerState

if ($host_power_state -eq "On")
{
$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" 
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}


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
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}


if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}
else
{
$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -Headers @{"Accept"="application/json"}


if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    Write-Host
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}


while ($overall_job_output.JobState -ne "Completed")
{
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
try
{
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
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
[String]::Format("- WARNING, job not marked completed, current status is: {0} Percent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
Start-Sleep 10
}
}

[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Start-Sleep 20
Write-Host "`n- Detailed final job status results:"
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"


try
{
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
 
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output

$u = "https://$idrac_ip/redfish/v1/Chassis/$set_enclosure_asset_tag"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
$z=$result.Content | ConvertFrom-Json
$asset_tag_new=$z.AssetTag

if ($asset_tag_new -eq $asset_tag)
{
Write-Host "- PASS, asset tag for '$set_enclosure_asset_tag' successfully set to '$asset_tag_new'"
}
else
{
Write-Host "- FAIL, asset tag for '$set_enclosure_asset_tag' not set to '$asset_tag', current asset tag value is '$asset_tag_new'"
return
}

}


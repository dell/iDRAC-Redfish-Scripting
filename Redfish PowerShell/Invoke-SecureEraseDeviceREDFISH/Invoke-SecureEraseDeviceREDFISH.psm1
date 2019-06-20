<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 4.0
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
   Cmdlet used to either get controllers, get supported secure erase devices or execute secure erase devices
.DESCRIPTION
   Cmdlet used to either get storage controllers, get secure erase devices or secure erase devices using iDRAC Redfish API NOTE: If erasing SED / ISE drives, make sure these drives are not part of a RAID volume. RAID volume must be deleted first before you can erase the drives.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_storage_controllers: Pass in "y" to get current storage controller FQDDs for the server. Pass in "yy" to get detailed information for each storage controller
   - get_secure_erase_devices: Pass in the controller FQDD to return supported secure erase devices if detected. Example, pass in "RAID.Integrated.1-1"
   - secure_erase_device: Pass in supported secure erase device FQDD to erase. Supported devices are ISE / SED drives or PCIe SSD drives / HHHL cards.
.EXAMPLE
   .\Invoke-SecureEraseDeviceREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_storage_controllers y
   This example will return storage controller FQDDs for the server.
.EXAMPLE
   .\Invoke-SecureEraseDeviceREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -secure_erase_device Disk.Bay.21:Enclosure.Internal.0-1:PCIeExtender.Slot.1
   This example will secure erase PCIe SSD drive Disk.Bay.21:Enclosure.Internal.0-1:PCIeExtender.Slot.1
#>

function Invoke-SecureEraseDeviceREDFISH {

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
    [string]$get_secure_erase_devices,
    [Parameter(Mandatory=$False)]
    [string]$secure_erase_device
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
#[Net.ServicePointManager]::SecurityProtocol = "TLS12, TLS11, TLS"
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)


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
Write-Host
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
$z=$r.Content | ConvertFrom-Json
[String]::Format("- Detailed information for controller {0} -`n", $z.Id)
$r.Content | ConvertFrom-Json
Write-Host
$count+=1

}
return
}


if ($get_storage_controllers -eq "y")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
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
Write-Host "- Server controllers detected -`n"
$controllers
return
}


if ($get_secure_erase_devices -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_secure_erase_devices"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$z=$result.Content | ConvertFrom-Json
$count = 0
Write-Host "`n- Devices detected for controller '$get_secure_erase_devices' -`n"
foreach ($item in $z.Drives)
{
$count++
$zz=[string]$item
$zz=$zz.Split("/")[-1]
$drive=$zz.Replace("}","")
$drive
}
if ( $count -eq 0)
{
Write-Host "- WARNING, no devices detected for controller $get_secure_erase_devices`n"
}
return
}


if ($secure_erase_device -ne "")
{
$u1 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Drives/$secure_erase_device/Actions/Drive.SecureErase"

try
{
$result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Post -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}
if ($result1.StatusCode -eq 202)
{
    $q=$result1.RawContent | ConvertTo-Json -Compress
    $j=[regex]::Match($q, "JID_.+?r").captures.groups[0].value
    $job_id=$j.Replace("\r","")
    [String]::Format("`n- PASS, statuscode {0} returned to successfully erase '{1}' device, {2} job ID created",$result1.StatusCode, $secure_erase_device, $job_id)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}
}


$u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
try
{
$result = Invoke-WebRequest -Uri $u3 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
}
catch
{
Write-Host
$RespErr
return
}

$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
{
$job_type = "realtime_config"
Write-Host "- WARNING, secure erase job will run in real time operation, no server reboot needed to apply the changes"
}
if ($overall_job_output.JobType -eq "RAIDConfiguration")
{
$job_type = "staged_config"
Write-Host "- WARNING, secure erase job will run in staged operation, server reboot needed to apply the changes"
}



if ($job_type -eq "realtime_config")
{
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
[String]::Format("- WARNING, job not marked completed, current status is: {0} Precent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
Start-Sleep 3
}
}
Write-Host
Start-Sleep 10
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
return
}






if ($job_type -eq "staged_config")
{
while ($overall_job_output.Message -ne "Task successfully scheduled.")
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
if ($overall_job_output.JobState -eq "Failed")
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
[String]::Format("- WARNING, job not marked completed, current status is: {0} Precent complete is: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
Start-Sleep 10
}
}
Start-Sleep 10
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
return

}


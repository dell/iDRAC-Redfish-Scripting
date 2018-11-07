<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 1.0
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
   Cmdlet used to either get storage controllers, get virtual disks or delete virtual disk
.DESCRIPTION
   Cmdlet used to either get storage controllers, get virtual disks or delete virtual disk using iDRAC Redfish API.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_storage_controllers: Pass in "y" to get current storage controller FQDDs for the server. Pass in "yy" to get detailed information for each storage controller
   - get_virtual_disks: Pass in the controller FQDD to get current virtual disks. Example, pass in "RAID.Integrated.1-1" to get current virtual disks for integrated storage controller
   - get_virtual_disks_details: Pass in the controller FQDD to get detailed VD information. Example, pass in "RAID.Slot.6-1" to get detailed virtual disk information
   - delete_virtual_disk: Pass in the virtual disk FQDD to delete. Example, pass in "Disk.Virtual.0:RAID.Slot.6-1" to delete virtual disk for controller RAID.Slot.6-1
.EXAMPLE
   .\Invoke-DeleteVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_storage_controllers y
   This example will return storage controller FQDDs for the server.
.EXAMPLE
   .\Invoke-DeleteVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -delete_virtual_disk Disk.Virtual.0:RAID.Slot.6-1
   This example will delete virtual disk Disk.Virtual.0:RAID.Slot.6-1.
#>

function Invoke-DeleteVirtualDiskREDFISH {

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
    [string]$get_virtual_disks,
    [Parameter(Mandatory=$False)]
    [string]$get_virtual_disk_details,
    [Parameter(Mandatory=$False)]
    [string]$delete_virtual_disk

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

function check_supported_idrac_version
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
    }
    catch
    {
    }
	    if ($result.StatusCode -ne 200)
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API"
	    return
	    }
	    else
	    {
	    }
return
}

Ignore-SSLCertificates


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)

check_supported_idrac_version

if ($get_virtual_disks -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_virtual_disks/Volumes"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get virtual disks for {1} controller`n",$result.StatusCode,$get_virtual_disks)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$a=$result.Content
try
{
$regex = [regex] '/Volumes/.+?"'
$allmatches = $regex.Matches($a)
$z=$allmatches.Value.Replace('/Volumes/',"")
$virtual_disks=$z.Replace('"',"")
[String]::Format("- WARNING, virtual disks detected for controller {0}:`n",$get_virtual_disks)
foreach ($i in $virtual_disks)
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$i"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
$z=$result.Content | ConvertFrom-Json
if ($z.VolumeType -ne "RawDevice")
{
[String]::Format("{0}, Volume Type: {1}",$z.Id, $z.VolumeType)
}
}
}
catch
{
Write-Host "- WARNING, no virtual disks detected for controller $get_virtual_disks"
}
Write-Host
return

}

if ($get_virtual_disk_details -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$get_virtual_disk_details"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}

if ($result.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get virtual disk '{1}' details",$result.StatusCode,$get_virtual_disk_details)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
$result.Content | ConvertFrom-Json

return

}


if ($get_storage_controllers -eq "yy")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
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
$z=$result.Content | ConvertFrom-Json
$number_of_controller_entries=$z.Members.Count
$count=0
Write-Host
while ($count -ne $number_of_controller_entries)
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}
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
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
$z=$r.Content | ConvertFrom-Json
[String]::Format("- Detailed information for controller {0} -`n", $z.Id)
$r.Content | ConvertFrom-Json
Write-Host
$count+=1

}
Write-Host
return
}


if ($get_storage_controllers -eq "y")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
try
{
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
}
catch
{
Write-Host
$RespErr
return
}
if ($r.StatusCode -eq 200)
{
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get storage controller(s)",$r.StatusCode)
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    Exit
}

$a=$r.Content

Write-Host
$regex = [regex] '/Storage/.+?"'
$allmatches = $regex.Matches($a)
$z=$allmatches.Value.Replace('/Storage/',"")
$controllers=$z.Replace('"',"")
Write-Host "- Server controllers detected -`n"
$controllers
Write-Host
return
}

if ($delete_virtual_disk -ne "")
{
$u1 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$delete_virtual_disk"
    try
    {
    $result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Delete -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }

    if ($result1.StatusCode -eq 202)
    {
    $q=$result1.RawContent | ConvertTo-Json
    $j=[regex]::Match($q, "JID_.+?r").captures.groups[0].value
    $job_id=$j.Replace("\r","")
    [String]::Format("`n- PASS, statuscode {0} returned to successfully delete virtual disk {1}, {2} job ID created",$result1.StatusCode,$delete_virtual_disk,$job_id)
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
    }


    $u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
    $result = Invoke-WebRequest -Uri $u3 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
    if ($result.StatusCode -eq 200)
    {
    [String]::Format("`n- PASS, statuscode {0} returned to successfully query job ID {1}",$result.StatusCode,$job_id)
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
    }

}
    $overall_job_output=$result.Content | ConvertFrom-Json

    if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
    {
    $job_type = "realtime_config"
    Write-Host "- WARNING, delete virtual disk job will run in real time operation, no server reboot needed to apply the changes"
    }
    if ($overall_job_output.JobType -eq "RAIDConfiguration")
    {
    Write-Host "- WARNING, delete virtual disk job will run in staged operation, server reboot needed to apply the changes"
    {
    $job_type = "staged_config"
    }
}

if ($job_type -eq "realtime_config")
{
    while ($overall_job_output.JobState -ne "Completed")
    {
    $u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
    $result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'

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
        Start-Sleep 1
        }
    }
Write-Host
Start-Sleep 10
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output

$controller_id=$delete_virtual_disk.Split(":")[1]
$u="https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$delete_virtual_disk"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
    Write-Host "- FAIL, $delete_virtual_disk still reported for controller $controller_id"
    return
    }
    catch
    {
    Write-Host "- PASS, $delete_virtual_disk no longer exists for controller $controller_id"
    return
    }
}

if ($job_type -eq "staged_config")
{
    while ($overall_job_output.Message -ne "Task successfully scheduled.")
    {
    $u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
    $result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'

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

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
$z=$result.Content | ConvertFrom-Json
$host_power_state = $z.PowerState

if ($host_power_state -eq "On")
{
$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
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
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'


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
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
$result1 = Invoke-WebRequest -Uri $u4 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'


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
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
 
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
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'

$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output

$controller_id=$delete_virtual_disk.Split(":")[1]

$u="https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$delete_virtual_disk"
try
{
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing
Write-Host "- FAIL, $delete_virtual_disk still reported for controller $controller_id"
return
}
catch
{
Write-Host "- PASS, $delete_virtual_disk no longer exists for controller $controller_id"
return
}

return
}


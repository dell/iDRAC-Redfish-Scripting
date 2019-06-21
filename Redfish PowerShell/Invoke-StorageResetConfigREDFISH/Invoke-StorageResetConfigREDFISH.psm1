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
   Cmdlet used to either get storage controllers, get virtual disks, get physical disks or reset the storage controller using Redfish API OEM extension.
.DESCRIPTION
   Cmdlet used to either get storage controllers, get virtual disks, get physical disks or reset the storage controller using Redfish API OEM extension.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_storage_controllers: Pass in "y" to get current storage controller FQDDs for the server. Pass in "yy" to get detailed information for each storage controller
   - get_virtual_disks: Pass in the controller FQDD to get current virtual disks. Example, pass in "RAID.Integrated.1-1" to get current virtual disks for integrated storage controller
   - get_virtual_disks_details: Pass in the virtual disk FQDD to get detailed VD information. Example, pass in "Disk.Virtual.0:RAID.Slot.6-1" to get detailed virtual disk information
   - reset_storage_controller: Pass in the controller FQDD. Example, pass in "RAID.Slot.6-1".
   
.EXAMPLE
    .\Invoke-StorageResetConfigREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_storage_controllers y
   This example will return storage controller FQDDs for the server.
.EXAMPLE
   .\Invoke-StorageResetConfigREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -reset_storage_controller RAID.Mezzanine.1-1
   This example will reset the storage controller RAID.Mezzanine.1-1
#>

function Invoke-StorageResetConfigREDFISH {

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
    [string]$reset_storage_controller
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

#################################
# Function to get virtual disks #
#################################

function get_virtual_disks
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_virtual_disks/Volumes"
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
return
}

########################################
# Function to get virtual disk details #
########################################

function get_virtual_disk_details
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$get_virtual_disk_details"
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

#############################################
#Function to get storage controller details #
#############################################

function get_storage_controller_details
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
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
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
$z=$r.Content | ConvertFrom-Json
[String]::Format("- Detailed information for controller {0} -`n", $z.Id)
$r.Content | ConvertFrom-Json
Write-Host
$count+=1

}
Write-Host
return
}

############################################
# Function to get storage controller FQDDs #
############################################

function get_storage_controllers
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
try
{
$r = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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
Write-Host
return
}

############################################
# Function to reset the storage controller #
############################################

function storage_controller_reset
{

$u1 = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ResetConfig"
$JsonBody = @{"TargetFQDD"=$reset_storage_controller} | ConvertTo-Json -Compress

    try
    {
    $result1 = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
    if ($result1.StatusCode -eq 202 -or $result1.StatusCode -eq 200)
    {
    $job_id=$result1.Headers.Location.Split("/")[-1]

    [String]::Format("`n- PASS, statuscode {0} returned to successfully reset storage controller {1}, {2} job ID created",$result1.StatusCode,$reset_storage_controller,$job_id)
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned to create virtual disk",$result1.StatusCode)
    return
    }


$u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u3 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}
if ($result.StatusCode -eq 200)
{
    #[String]::Format("`n- PASS, statuscode {0} returned to successfully query job ID {1}",$result.StatusCode,$job_id)
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}
 
$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
{
$job_type = "realtime_config"
Write-Host "`n- WARNING, reset storage controller real time job created, no server reboot needed to apply the changes"
}
if ($overall_job_output.JobType -eq "RAIDConfiguration")
{
$job_type = "staged_config"
Write-Host "`n- WARNING, reset storage controller staged job created, server reboot needed to apply the changes"
}

if ($job_type -eq "realtime_config")
{
    while ($overall_job_output.JobState -ne "Completed")
    {
    $u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id" 
    $result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json' -Headers @{"Accept"="application/json"}

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

##################################
# Function to check no VDs exist #
##################################

function check_no_vds
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$reset_storage_controller/Volumes"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"}

$result_output=$result.Content | ConvertFrom-Json
#$z
$member_count_key="Members@odata.count"
if ($result_output.$member_count_key -eq 0)
{
Write-Host "- PASS, validated no VDs exist for storage controller $reset_storage_controller"
}
else
{
Write-Host "- FAIL, VDs still exist for storage controller $reset_storage_controller. Execute script to debug and check virtual disks reported for your storage controller"
}
return
}


############
# Run code #
############

Ignore-SSLCertificates
setup_idrac_creds

# Code to check for supported iDRAC version installed

$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/"
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


if ($get_storage_controllers -eq "y" -or $get_storage_controllers -eq "Y")
{
get_storage_controllers
}
elseif ($get_storage_controllers -eq "yy" -or $get_storage_controllers -eq "YY")
{
get_storage_controller_details
}
elseif ($get_virtual_disks -ne "")
{
get_virtual_disks
}
elseif ($get_virtual_disk_details -ne "")
{
get_virtual_disk_details
}
elseif ($reset_storage_controller -ne "")
{
storage_controller_reset
check_no_vds
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}

}


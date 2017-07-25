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
   Cmdlet used to either enable / disable boot device source state or get current boot order and their current boot source state
.DESCRIPTION
   Cmdlet used to either enable / disable boot device source state for one boot device or get current boot order and their current boot source state.
   NOTE: Change boot order supported for BIOS (IPL) and UEFI boot sequences. Change boot source state supported for BIOS (IPL) and UEFI devices. 
   HDD devices not supported for changing boot order or boot source state.
   - idrac_ip: REQUIRED, pass in the iDRAC IP address
   - idrac_username: REQUIRED, pass in the iDRAC user name
   - idrac_password: REQUIRED, pass in the iDRC user name password
   - view_boot_order_boot_source_state: OPTIONAL, pass in "y" to view only the boot order and current boot source state.

   IMPORTANT NOTE: You must execute and view the current boot order/boot source state at least once to create "boot_devices.txt" file. 
   This file is needed to edit and make user changes to set the new boot order / boot source state. To change boot source state to Enabled, pass in "true" value for Enabled key. If
   you want to disable boot source state, pass in a value of "false" for Enabled Key. 
   To change the boot order, change the index numbers for the devices listed. Also make sure you do not change the format of the file as JSON format is needed for the script.

    Example of "boot_devices.txt" file, current boot order and boot devices:

    {
    "Attributes":  {
                       "UefiBootSeq":  [
                                           {
                                               "Enabled":  false,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#Optical.iDRACVirtual.1-1#375d3ecb49f87dd46ca6c60e34f6155d",
                                               "Index":  2,
                                               "Name":  "Optical.iDRACVirtual.1-1"
                                           },
                                           {
                                               "Enabled":  true,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#RAID.Mezzanine.1-1#6f9a42098226e9297f899d1039d4558e",
                                               "Index":  0,
                                               "Name":  "RAID.Mezzanine.1-1"
                                           },
                                           {
                                               "Enabled":  false,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#Floppy.iDRACVirtual.1-1#f64c2e3f049b92a8e71f61cf51fea794",
                                               "Index":  1,
                                               "Name":  "Floppy.iDRACVirtual.1-1"
                                           }
                                       ]
                   }
}


  Example of "boot_devces.txt" file after making changes. I set boot source state for virtual floppy to true and set virtual floppy as 1st device, PERC as 2nd device and virtual optical
  as 3rd device.

  {
    "Attributes":  {
                       "UefiBootSeq":  [
                                           {
                                               "Enabled":  false,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#Optical.iDRACVirtual.1-1#375d3ecb49f87dd46ca6c60e34f6155d",
                                               "Index":  2,
                                               "Name":  "Optical.iDRACVirtual.1-1"
                                           },
                                           {
                                               "Enabled":  true,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#RAID.Mezzanine.1-1#6f9a42098226e9297f899d1039d4558e",
                                               "Index":  1,
                                               "Name":  "RAID.Mezzanine.1-1"
                                           },
                                           {
                                               "Enabled":  true,
                                               "Id":  "BIOS.Setup.1-1#UefiBootSeq#Floppy.iDRACVirtual.1-1#f64c2e3f049b92a8e71f61cf51fea794",
                                               "Index":  0,
                                               "Name":  "Floppy.iDRACVirtual.1-1"
                                           }
                                       ]
                   }
}




.EXAMPLE
   Set-BiosBootOrderBootSourceStateREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -view_boot_order_boot_source_state_only y 
   This example will return only the current boot order along with current boot source state and write this output to "boot_devices.txt" file which this file is needed to make user changes.
.EXAMPLE
   Set-BootSourceStateREDFISH -idrac_ip 192.168.0.120 -username root -password calvin
   This example will make changes to the boot order and boot source state based off the changes you made in boot_devices.txt file.
#>

function Set-BiosBootOrderBootSourceStateREDFISH {


param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$view_boot_order_boot_source_state_only
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

if ($view_boot_order_boot_source_state_only -eq "n")
{
return
}


$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 
Write-Host

if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully get current boot mode",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_all_attributes=$result.Content | ConvertFrom-Json | Select Attributes
$get_boot_mode_attribute= $get_all_attributes.Attributes | Select BootMode
$current_boot_mode=$get_boot_mode_attribute.BootMode

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/BootSources"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 

if ($result.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to get boot order devices and boot source state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_output=$result.Content

# This code is needed to strip the string output to parse the data and only return the current boot order and boot source state in pretty format

$j=[regex]::Match($get_output, "Attributes.+").captures.groups[0].value
$jj=$j.Replace(",""Description"":""Boot Sources Current Settings"",""Id"":""BootSources"",""Name"":""Boot Sources Configuration Current Settings""}","")
$jj=$jj.Replace("Attributes","")
$jj=$jj.Replace("{"," ")
$jj=$jj.Replace("}"," `n")
if ($current_boot_mode -eq "Uefi")
{
$jj=$jj.Replace(": ""UefiBootSeq"":[","")
}
else
{
$jj=$jj.Replace(": ""BootSeq"":[","")
$jj=$jj.Replace("""HddSeq"":","")
}
$jj=$jj.Replace(""" ","")
$jj=$jj.Replace(" ","")
$jj=$jj.Replace("]","")
$jj=$jj.Replace("[","")


Write-Host "`n`n- Current boot source state and boot order for BIOS boot mode ""$current_boot_mode"" listed below:"
Write-Host
foreach ($i in $jj)
{
$i.Split(",")
}

if ($view_boot_order_boot_source_state_only -eq "y")
{
try {
    Remove-Item("boot_devices.txt") -ErrorAction Stop
    Write-Host "- WARNING, boot_devices.txt file detected, file deleted and will create new file with latest boot order/boot source state content"
    }
catch [System.Management.Automation.ActionPreferenceStopException] {
    Write-Host "- WARNING, boot_devices.txt file not detected" 
}
$get_content_convert=$result.Content | ConvertFrom-Json
$write_json_to_file=@{"Attributes"=$get_content_convert.Attributes} | ConvertTo-Json -Compress -Depth 3

$write_json_to_file | Out-String | Add-Content boot_devices.txt
Write-Host -Foreground Yellow "`n- WARNING, current boot source state and boot order copied to ""boot_devices.txt"" file. This file is needed to either change boot order/boot source state or both."
return
}

$JsonBody_patch_command=Get-Content boot_devices.txt
$JsonBody_patch_command=[string]$JsonBody_patch_command

$u1 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/BootSources/Settings"
$result_test = Invoke-WebRequest -Uri $u1 -Credential $credential -Method Patch -Body $JsonBody_patch_command -ContentType 'application/json'

if ($result_test.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to set pending value(s)",$result_test.StatusCode)
    
    
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result_test.StatusCode)
    return
}


$JsonBody = @{ "TargetSettingsURI" ="/redfish/v1/Systems/System.Embedded.1/Bios/Settings"
    } | ConvertTo-Json -Compress


$u2 = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs"
$result1 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json'
$raw_output=$result1.RawContent | ConvertTo-Json -Compress
$job_search=[regex]::Match($raw_output, "JID_.+?r").captures.groups[0].value
$job_id=$job_search.Replace("\r","")
Start-Sleep 3
if ($result1.StatusCode -eq 200)
{
    [String]::Format("- PASS, statuscode {0} returned to successfully create job: {1}",$result1.StatusCode,$job_id)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}


$u3 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
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
return
}


$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json -Compress


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
    } | ConvertTo-Json -Compress


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
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


$t=Get-Date -DisplayHint Time
$start_time = Get-Date
$end_time = $start_time.AddMinutes(30)

while ($overall_job_output.JobState -ne "Completed")
{
$loop_time = Get-Date
$u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
$result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
$overall_job_output=$result.Content | ConvertFrom-Json
if ($overall_job_output.JobState -eq "Failed")
{
Write-Host
[String]::Format("- FAIL, job not marked as scheduled, detailed error info: {0}",$overall_job_output)
return
}
elseif ($loop_time -gt $end_time)
{
Write-Host "- FAIL, timeout of 30 minutes has been reached before marking the job completed"
return
}
else
{
[String]::Format("- WARNING, job not marked completed, current message is: {0}",$overall_job_output.Message)
Start-Sleep 15
}
}
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
$tt=Get-Date -DisplayHint Time
$ttt=$tt-$t
$final_completion_time=$ttt | select Minutes,Seconds 
Write-Host "  Job completed in $final_completion_time"



$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/BootSources"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 
if ($result.StatusCode -eq 200)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned successfully to get boot order devices and boot source state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

# Code to get parse new string GET output for boot order and boot source state, convert to pretty format

$get_string_output=$result.Content
$j=[regex]::Match($get_string_output, "Attributes.+").captures.groups[0].value
$jj=$j.Replace(",""Description"":""Boot Sources Current Settings"",""Id"":""BootSources"",""Name"":""Boot Sources Configuration Current Settings""}","")
$jj=$jj.Replace("Attributes","")
$jj=$jj.Replace("{"," ")
$jj=$jj.Replace("}"," `n")
if ($current_boot_mode -eq "Uefi")
{
$jj=$jj.Replace(": ""UefiBootSeq"":[","")
}
else
{
$jj=$jj.Replace(": ""BootSeq"":[","")
$jj=$jj.Replace("""HddSeq"":","")
}
$jj=$jj.Replace(""" ","")
$jj=$jj.Replace(" ","")
$jj=$jj.Replace("]","")

Write-Host "`n`n- New boot source state and boot order for BIOS boot mode ""$current_boot_mode"" listed below:"
Write-Host
foreach ($i in $jj){
$i.Split(",")
}

}
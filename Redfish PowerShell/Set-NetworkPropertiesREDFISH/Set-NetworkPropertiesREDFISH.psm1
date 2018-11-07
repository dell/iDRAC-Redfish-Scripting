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
   Cmdlet used to either get network device IDs, get network port IDs, get network port properties or set network properties
.DESCRIPTION
   Cmdlet used to either get network device IDs, get network port IDs, get network port properties or set netork properties using iDRAC Redfish API.
   - idrac_ip: REQUIRED, pass in iDRAC IP address
   - idrac_username: REQUIRED, pass in iDRAC username
   - idrac_password: REQUIRED, pass in iDRAC username password
   - get_network_device_IDs: OPTIONAL, pass in "y" to get network device and port IDs for your system.
   - get_detail_network_device_ID_info: OPTIONAL, pass in network device ID string to get detailed information. Example, pass in "NIC.Integrated.1"
   - get_detail_network_port_ID_info:  OPTIONAL, pass in network port ID string to get detailed information. Example, pass in "NIC.Integrated.1-1-1"
   - get_network_port_properties: OPTIONAL, pass in network port ID to get properties. Example, pass in "NIC.Integrated.1-1-1"
   - generate_set_properties_ini_file: OPTIONAL, pass in "y" to generate ini file to set network attributes. If setting network properties, you must generate this ini file first which you will modify for setting attributes
   - set_network_properties: OPTIONAL, pass in network port ID to set network properties in the ini file (make sure the ini file is located in the same directory you are executing the cmdlet from). "job_type" parameter is also required when setting network attributes
   - job_type: OPTIONAL, pass in "n" for creating a config job which will run now. Pass in "s" which will schedule the config job but not reboot the server. Config changes will be applied on next system manual reboot
.EXAMPLE
   .\Set-NetworkPropertiesREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_network_port_properties NIC.Integrated.1-1-1
   This example will return network properties for port NIC.Integrated.1-1-1
.EXAMPLE
   .\Set-Network_PropertiesREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -set_network_properties NIC.Integrated.1-1-1 -job_type n
   This example will set network properties from the ini file for NIC.Integrated.1-1-1 and create a config job for now to reboot the system and apply changes
.EXAMPLE
   Examples of modified hashtable in the ini file for setting network properties. For either iSCSIBoot or FibreChannel nested hastables, you can leave it blank or remove it from the hashtable:
   {"FibreChannel":{},"iSCSIBoot":{"InitiatorIPAddress":"192.168.0.120","InitiatorNetmask":"255.255.255.0"}}
   {"FibreChannel":{"WWNN":"20:00:00:24:FF:12:FC:11"},"iSCSIBoot":{}}
#>

function Set-NetworkPropertiesREDFISH {

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_network_device_IDs,
    [Parameter(Mandatory=$False)]
    [string]$get_detail_network_device_ID_info,
    [Parameter(Mandatory=$False)]
    [string]$get_detail_network_port_ID_info,
    [Parameter(Mandatory=$False)]
    [string]$get_network_port_properties,
    [Parameter(Mandatory=$False)]
    [string]$generate_set_properties_ini_file,
    [Parameter(Mandatory=$False)]
    [string]$set_network_properties,
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

function check_supported_idrac_version
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr
    }
    catch
    {
    }
	    if ($result.StatusCode -ne 200)
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API" -ForegroundColor Yellow
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

if ($generate_set_properties_ini_file -eq "y")
{
    if (Test-Path .\set_nic_properties.ini -PathType Leaf)
    {
    Remove-Item "set_nic_properties.ini"
    }
$payload=@{"iSCSIBoot"=@{};"FibreChannel"=@{}} | ConvertTo-Json -Compress

$payload | out-string | add-content "set_nic_properties.ini"
Write-Host "`n- WARNING, 'set_nic_properties.ini' file successfully created in this directory you are executing the cmdlet from" -ForegroundColor Yellow
return
}



if ($get_network_device_IDs -eq "y")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get network device IDs `n",$result.StatusCode)
    }
    else
    {
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
    }

$z=$result.Content | ConvertFrom-Json
$z=$z.Members
$device_ids=@()
Write-Host "- Network Device IDs Detected for iDRAC $idrac_ip -`n" -ForegroundColor Yellow
    foreach ($i in $z)
    {
    $i=[string]$i
    $i=$i.Split("/")[-1].Replace("}","")
    $i
    $device_ids+=$i
    }
        foreach ($i in $device_ids)
        {
        $u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$i/NetworkDeviceFunctions"
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
        $z=$result.Content | ConvertFrom-Json
        $z=$z.Members
        $port_ids=@()
        Write-Host "`n- Network port IDs Detected for network ID $i -`n" -ForegroundColor Yellow
            foreach ($ii in $z)
            {
            $ii=[string]$ii
            $ii=$ii.Split("/")[-1].Replace("}","")
            $ii
            $port_ids+=$ii
            }
        }
Return
}


if ($get_detail_network_device_ID_info -ne "")
{
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$get_detail_network_device_ID_info"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get detail info for network device ID '{1}'`n",$result.StatusCode,$get_detail_network_device_ID_info)
    }
    else
    {
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
    }
    Write-Host "- Detailed information for network device ID '$get_detail_network_device_ID_info'" -ForegroundColor Yellow
    $z=$result.Content | ConvertFrom-Json
    $z
Return    
}

if ($get_detail_network_port_ID_info -ne "")
{
$s=$get_detail_network_port_ID_info.Split("-")
$device_id=$s[0]
$port_id=$s[0]+"-"+$s[1]
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$device_id/NetworkPorts/$port_id"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get detail info for port device ID '{1}'`n",$result.StatusCode,$get_detail_network_port_ID_info)
    }
    else
    {
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
    }
    Write-Host "- Detailed information for network device ID '$get_detail_network_port_ID_info'" -ForegroundColor Yellow
    $z=$result.Content | ConvertFrom-Json
    $z
Return    
}

if ($get_network_port_properties -ne "")
{
$s=$get_network_port_properties.Split("-")
$device_id=$s[0]
$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$device_id/NetworkDeviceFunctions/$get_network_port_properties"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get properties for port device ID '{1}'`n",$result.StatusCode,$get_network_port_properties)
    }
    else
    {
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
    }
    $z=$result.Content | ConvertFrom-Json
    Write-Host "- iSCSIBoot properties for '$get_network_port_properties'" -ForegroundColor Yellow
        if ($z.iSCSIBoot.Length -eq 0)
        {
        Write-Host "`n- WARNING, no iSCSIBoot properties detected for $get_network_port_properties'`n"
        }
        else
        {
        $z.iSCSIBoot
        }
    Write-Host "- FibreChannel properties for '$get_network_port_properties'`n" -ForegroundColor Yellow
        if ($z.FibreChannel.Length -eq 0)
        {
        Write-Host "`n- WARNING, no FibreChannel properties supported for $get_network_port_properties'" 
        }
        else
        {
        $z.FibreChannel
        }
Return    
}

if ($set_network_properties -ne "")
{

try {
    $JsonBody = Get-Content set_nic_properties.ini -ErrorAction Stop
    }
catch [System.Management.Automation.ActionPreferenceStopException] {
    Write-Host "`n- WARNING, 'set_nic_properties.ini' file not detected. Make sure this file is located in the same directory you are running the cmdlet from"  -ForegroundColor Yellow
    return
}

$JsonBody_patch_command=Get-Content set_nic_properties.ini
$JsonBody=[string]$JsonBody_patch_command

    if ($JsonBody.Contains('"FibreChannel":{}'))
    {
    $JsonBody=$JsonBody.Replace('"FibreChannel":{},',"")
    }
    if ($JsonBody.Contains('"iSCSIBoot":{}'))
    {
    $JsonBody=$JsonBody.Replace(',"iSCSIBoot":{}',"")
    }

$properties = $JsonBody | ConvertFrom-Json
$set_properties = @{}
$properties.psobject.properties | Foreach { $set_properties[$_.Name] = $_.Value }
Write-Host "`n- WARNING, new property change(s) for: '$set_network_properties'" -ForegroundColor Yellow
$set_properties
$s=$set_network_properties.Split("-")
$device_id=$s[0]

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$device_id/NetworkDeviceFunctions/$set_network_properties/Settings"
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }

    if ($result.StatusCode -eq 200)
    {
    $status_code = $result.StatusCode
    
    Write-Host "`n- PASS, statuscode $status_code returned successfully for PATCH command to set property pending value(s) for port device ID '$set_network_properties'" -ForegroundColor Green
    }
    else
    {
    Write-Host "`n- FAIL, status code $status_code returned for PATCH command" -ForegroundColor Red
    return
    }
  
}

if ($job_type -eq "n")
{
$s=$set_network_properties.Split("-")
$device_id=$s[0]

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$device_id/NetworkDeviceFunctions/$set_network_properties/Settings"
$JsonBody = @{"@Redfish.SettingsApplyTime"=@{"ApplyTime"="OnReset"}} | ConvertTo-Json -Compress
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
        if ($result.StatusCode -eq 202)
        {
        $status_code = $result.StatusCode
       
        Write-Host "`n- PASS, statuscode $status_code returned successfully for PATCH command to create reboot now config job for port device ID '$set_network_properties'`n" -ForegroundColor Green
        }
        else
        {
        
        Write-Host "`n- FAIL, status code $status_code returned for PATCH command" -ForegroundColor Red
        return
        }
$q=$result.RawContent | ConvertTo-Json
$j=[regex]::Match($q, "JID_.+?r").captures.groups[0].value
$job_id=$j.Replace("\r","")
Write-Host "- WARNING, job ID created for reboot now config job is: '$job_id'"
    
    while ($overall_job_output.JobState -ne "Scheduled")
    {
    $u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
    $result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
    $overall_job_output=$result.Content | ConvertFrom-Json
        if ($overall_job_output.JobState -eq "Failed") 
        {
        Write-Host
        [String]::Format("- FAIL, final job status is: {0}",$overall_job_output.JobState)
        return
        }
        
    [String]::Format("- WARNING, job ID {0} not marked as scheduled, current job message: {1}",$job_id, $overall_job_output.Message)
    Start-Sleep 1
    }
    Write-Host "`n- PASS, reboot now job ID '$job_id' successfully marked as scheduled, rebooting the server`n"
    
$JsonBody = @{ "ResetType" = "ForceOff"} | ConvertTo-Json

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

$JsonBody = @{ "ResetType" = "On"} | ConvertTo-Json

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
Write-Host "- WARNING, cmdlet will now poll job ID every 15 seconds until job ID '$job_id' marked completed"
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
    [String]::Format("- WARNING, job not marked completed, current message: {0}, percent complete: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
    Start-Sleep 15
    }
    }
$tt=Get-Date -DisplayHint Time
$ttt=$tt-$t
$final_completion_time=$ttt | select Minutes,Seconds
Write-Host "`n- PASS, '$job_id' job ID marked completed! Job completed in $final_completion_time`n" -ForegroundColor Green 

return

}

if ($job_type -eq "s")
{
$s=$set_network_properties.Split("-")
$device_id=$s[0]

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/$device_id/NetworkDeviceFunctions/$set_network_properties/Settings"
$JsonBody = @{"@Redfish.SettingsApplyTime"=@{"ApplyTime"="OnReset"}} | ConvertTo-Json -Compress
    try
    {
    $result = Invoke-WebRequest -Uri $u -Credential $credential -Method Patch -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
        if ($result.StatusCode -eq 202)
        {
        $status_code = $result.StatusCode
        Write-Host "`n- PASS, statuscode $status_code returned successfully for PATCH command to create staged config job for port device ID '$set_network_properties'`n" -ForegroundColor Green
        }
        else
        {
        Write-Host "`n- FAIL, status code $status_code returned for PATCH command" -ForegroundColor Red
        return
        }
$q=$result.RawContent | ConvertTo-Json
$j=[regex]::Match($q, "JID_.+?r").captures.groups[0].value
$job_id=$j.Replace("\r","")
Write-Host "- WARNING, job ID created for reboot now config job is: '$job_id'"
    
    while ($overall_job_output.JobState -ne "Scheduled")
    {
    $u5 ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/$job_id"
    $result = Invoke-WebRequest -Uri $u5 -Credential $credential -Method Get -UseBasicParsing -ContentType 'application/json'
    $overall_job_output=$result.Content | ConvertFrom-Json
        if ($overall_job_output.JobState -eq "Failed") 
        {
        Write-Host
        [String]::Format("- FAIL, final job status is: {0}",$overall_job_output.JobState)
        return
        }
        
    [String]::Format("- WARNING, job ID {0} not marked as scheduled, current job message: {1}",$job_id, $overall_job_output.Message)
    Start-Sleep 1
    }
Write-Host "`n- PASS, staged config job ID '$job_id' successfully marked as scheduled, configuration changes will not be applied until next system manual reboot" -ForegroundColor Green
return
}

}

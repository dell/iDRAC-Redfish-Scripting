<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 16
.0
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
   Cmdlet using iDRAC with Redfish API to either get storage controllers, get virtual disks, get physical disks or create virtual disk
.DESCRIPTION
   Cmdlet using iDRAC with Redfish API to either get storage controllers, get virtual disks, get physical disks or create virtual disk.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - x_auth_token: Pass in iDRAC X-Auth token session to execute cmdlet instead of username / password (recommended)
   - get_storage_controllers: Get current storage controller FQDDs for the server.
   - get_storage_controller_details: Get detailed information for all storage controller FQDDs detected. 
   - get_virtual_disks: Pass in the controller FQDD to get current virtual disks. Example, pass in "RAID.Integrated.1-1" to get current virtual disks for integrated storage controller
   - get_virtual_disks_details: Pass in the virtual disk FQDD to get detailed information for a specific VD. Example, pass in "Disk.Virtual.0:RAID.Slot.6-1" to get detailed virtual disk information
   - get_all_virtual_disks_details: Pass in the controller FQDD to get detailed information for all VDs detected behind this controller.
   - get_physical_disks: Pass in the controller FQDD to get physical disks. Example, pass in "RAID.Slot.6-1" to get physical disks. 
   - get_physical_disks_details: Pass in the controller FQDD to get detailed information for physical disks.
   - create_virtual_disk: Pass in the controller FQDD. Example, pass in "RAID.Slot.6-1".
   - raid_level: Pass in the RAID level you want to create. Possible supported values are: 0, 1, 5, 6, 10, 50 and 60. Note: Some RAID levels might not be supported based on your storage controller
   - pdisks: Pass in disk FQDD to create virtual disk, pass in storage disk FQDD, Example: Disk.Bay.2:Enclosure.Internal.0-1:RAID.Mezzanine.1-1. You can pass in multiple drives, just use a comma seperator between each disk FQDD string and surround the complete string value with double quotes
   - size: Pass in the size(CapacityBytes) in bytes for VD creation. This is OPTIONAL, if you don't pass in the size, VD creation will use full disk size to create the VD
   - stripesize: Pass in the stripesize(OptimumIOSizeBytes) in bytes for VD creation. This is OPTIONAL, if you don't pass in stripesize, controller will use the default value
   - name: Pass in the name for VD creation. This is OPTIONAL, if you don\'t pass in name, storage controller will use the default value
   - diskcachepolicy: Pass in disk cache policy setting for VD creation, supported values: Enabled and Disabled. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value.
   - readcachepolicy: Pass in read cache policy setting for VD creation, supported values: Off, ReadAhead and AdaptiveReadAhead. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value.
   - writecachepolicy: Pass in write cache policy setting for VD creation, supported values: ProtectedWriteBack, UnprotectedWriteBack and WriteThrough. This is OPTIONAL, if you don\'t pass in this argument for VD creation, controller will use the default value.
   - secure: Secure virtual disk for VD creation. Note: Make sure your controller already has encryption enabled and using encryption capable drives.

.EXAMPLE
   Invoke-CreateVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_storage_controllers
   This example will return storage controller FQDDs for the server.
.EXAMPLE
    Invoke-CreateVirtualDiskREDFISH.ps1 -idrac_ip 192.168.0.120 -get_storage_controllers
   This example will first prompt for iDRAC username / password using Get-Credential, then return storage controller FQDDs for the server.
.EXAMPLE
    Invoke-CreateVirtualDiskREDFISH.ps1 -idrac_ip 192.168.0.120 -get_storage_controllers -x_auth_token 7bd9bb9a8727ec366a9cef5bc83b2708
   This example will return storage controller FQDDs for the server using iDRAC x-auth token session.
.EXAMPLE
   Invoke-CreateVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_storage_controller_details
   This example will return detailed information for all storage controllers.
.EXAMPLE
   Invoke-CreateVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_virtual_disks RAID.SL.3-1
   This example will return VD(s) detected for only this controller.
.EXAMPLE
   Invoke-CreateVirtualDiskREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -create_virtual_disk RAID.Slot.6-1 -raid_level 1 -pdisks "Disk.Bay.3:Enclosure.Internal.0-1:RAID.Slot.6-1,Disk.Bay.4:Enclosure.Internal.0-1:RAID.Slot.6-1"
   This example will create a RAID 1 for storage controller RAID.slot.6-1 using disk 3 and 4.
.EXAMPLE
   Invoke-CreateVirtualDiskREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -create_virtual_disk RAID.Mezzanine.1-1 -raid_level 0 -pdisks Disk.Bay.9:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 -name powershell_VD -secure -diskcachepolicy Disabled -writecachepolicy WriteThrough -readcachepolicy Off
   This example shows creating secured RAID 0 VD and setting VD disk, read and write cache policies. 
#>

function Invoke-CreateVirtualDiskREDFISH {

param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$False)]
    [string]$idrac_username,
    [Parameter(Mandatory=$False)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$x_auth_token,
    [Parameter(Mandatory=$False)]
    [switch]$get_storage_controllers,
    [Parameter(Mandatory=$False)]
    [switch]$get_storage_controller_details,
    [Parameter(Mandatory=$False)]
    [string]$get_virtual_disks,
    [Parameter(Mandatory=$False)]
    [string]$get_virtual_disk_details,
    [Parameter(Mandatory=$False)]
    [string]$get_all_virtual_disks_details,
    [Parameter(Mandatory=$False)]
    [string]$get_physical_disks,
    [Parameter(Mandatory=$False)]
    [string]$get_physical_disks_details,
    [Parameter(Mandatory=$False)]
    [string]$create_virtual_disk,
    [ValidateSet(0,1,5,6,10,50,60)]
    [Parameter(Mandatory=$False)]
    [string]$raid_level,
    [Parameter(Mandatory=$False)]
    [string]$pdisks,
    [Parameter(Mandatory=$False)]
    [String]$size,
    [Parameter(Mandatory=$False)]
    [string]$stripesize,
    [Parameter(Mandatory=$False)]
    [switch]$secure,
    [Parameter(Mandatory=$False)]
    [string]$diskcachepolicy,
    [Parameter(Mandatory=$False)]
    [string]$readcachepolicy,
    [Parameter(Mandatory=$False)]
    [string]$writecachepolicy,
    [Parameter(Mandatory=$False)]
    [string]$name
    )

# Function to setup iDRAC creds

function setup_idrac_creds
{

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12

if ($x_auth_token)
{
$global:x_auth_token = $x_auth_token
}
elseif ($idrac_username -and $idrac_password)
{
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}
else
{
$get_creds = Get-Credential
$global:credential = New-Object System.Management.Automation.PSCredential($get_creds.UserName, $get_creds.Password)
}
}

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

# Function get Powershell version 

$global:get_powershell_version = $null

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

function check_supported_idrac_version
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}
	    if ($result.StatusCode -ne 200)
	    {
        Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API"
	    return
	    }
        elseif ($result.StatusCode -eq 401)
        {
        Write-Host "`n- WARNING, invalid iDRAC username or password detected, status code 401 returned."
        return
        }
	    else
	    {
	    }
}


get_powershell_version
setup_idrac_creds
check_supported_idrac_version

if ($raid_level)
{
    if ($raid_level -eq 0)
    {
    $raid_level_string = "RAID0"
    }
    if ($raid_level -eq 1)
    {
    $raid_level_string = "RAID1"
    }
    if ($raid_level -eq 5)
    {
    $raid_level_string = "RAID5"
    }
    if ($raid_level -eq 6)
    {
    $raid_level_string = "RAID6"
    }
    if ($raid_level -eq 10)
    {
    $raid_level_string = "RAID10"
    }
    if ($raid_level -eq 50)
    {
    $raid_level_string = "RAID50"
    }
    if ($raid_level -eq 60)
    {
    $raid_level_string = "RAID60"
    }
} 



if ($create_virtual_disk -and $raid_level -and $pdisks)
{

    if ($pdisks.Contains(","))
    {
    $pdisks_pending=$pdisks.Split(",")
    $pdisks_list=@()
   
        foreach ($item in $pdisks_pending)
        {
        $keys_values=@{"@odata.id"="/redfish/v1/Systems/System.Embedded.1/Storage/Drives/$item"}
        $pdisks_list+=$keys_values   
        }
    }
    else
    {
    $pdisks_list=@()
    $keys_values=@{"@odata.id"="/redfish/v1/Systems/System.Embedded.1/Storage/Drives/$pdisks"}
    $pdisks_list+=$keys_values
    }

    $vd_payload=@{"RAIDType"=$raid_level_string;"Links"=@{"Drives"=$pdisks_list}} 
 
    if ($name)
    {
    $vd_payload["Name"] = $name
    }
    if ($size)
    {
    $vd_payload["CapacityBytes"] = [long]$size
    }
    if ($stripesize)
    {
    $vd_payload["OptimumIOSizeBytes"] = [long]$stripesize
    }
    if ($readcachepolicy)
    {
    $vd_payload["ReadCachePolicy"] = $readcachepolicy
    }
    if ($writecachepolicy)
    {
    $vd_payload["WriteCachePolicy"] = $writecachepolicy
    }
    if ($diskcachepolicy)
    {
    $vd_payload["Oem"]=@{"Dell"=@{"DellVolume"=@{"DiskCachePolicy"=$diskcachepolicy}}}
    }
    if ($secure)
    {
    $vd_payload["Encrypted"] = $true
    }
    $vd_payload = $vd_payload | ConvertTo-Json -Compress -Depth 4
}

#############################################################################################################################

if ($get_all_virtual_disks_details)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_controller_virtual_disk_details/Volumes"
if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}


if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_result=$result.Content | ConvertFrom-Json
if ($get_result.Members.count -eq 0)
{
Write-Host "`n- INFO, no virtual disks detected for controller $get_virtual_disks`n"
return
}

foreach ($item in $get_result.Members)
{
$odata_id = "@odata.id"
$uri = "https://$idrac_ip" + $item.$odata_id
[String]::Format("`n- INFO, detailed information for virtual disk {0} -`n",$item.$odata_id)

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}


if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$result.Content | ConvertFrom-Json

}

}

#############################################################################################################################

if ($get_virtual_disks)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_virtual_disks/Volumes"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}


if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_result=$result.Content | ConvertFrom-Json
if ($get_result.Members.count -eq 0)
{
Write-Host "`n- INFO, no virtual disks detected for controller $get_virtual_disks`n"
return
}

[String]::Format("`n- INFO, virtual disks detected for controller {0} -`n",$get_virtual_disks)
foreach ($item in $get_result.Members)
{
$odata_id = "@odata.id"
$item.$odata_id.Split("/")[-1]
}

}

#############################################################################################################################

if ($get_virtual_disk_details)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/$get_virtual_disk_details"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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
$get_result = $result.Content | ConvertFrom-Json
[String]::Format("`n- Detailed DMTF information for virtual disk {0}", $get_virtual_disk_details)
$get_result
$oem_content = $get_result.Oem.Dell.DellVirtualDisk
[String]::Format("- Detailed OEM information for virtual disk {0}`n", $get_virtual_disk_details)
if ($oem_content -eq $null)
{
[String]::Format("- WARNING, unable to detect or report OEM details for virtual disk {0}", $get_virtual_disk_details)
}
else
{
$oem_content
}

return

}

#############################################################################################################################

if ($get_storage_controller_details)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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
$get_content = $result.Content | ConvertFrom-Json
$number_of_controller_entries = $get_content.Members.Count
$count = 0
Write-Host
while ($count -ne $number_of_controller_entries)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}

$get_content = $result.Content | ConvertFrom-Json
[String]::Format("- Detailed DMTF information for controller {0} -`n", $get_content.Id)
$result.Content | ConvertFrom-Json
[String]::Format("- Detailed OEM information for controller {0} -`n", $get_content.Id)
$oem_content = $get_content.Oem.Dell.DellController
if ($oem_content -eq $null)
{
[String]::Format("- WARNING, unable to detect or report OEM details for controller {0}", $get_content.Id)
}
else
{
$oem_content
}
Write-Host
$count+=1

}
Write-Host
return
}

#############################################################################################################################

if ($get_storage_controllers)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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

#############################################################################################################################

if ($get_physical_disks)
{
$query = "?`$select=Drives"
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_physical_disks" + $query

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}
if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, GET request failed, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
Write-Host "`n- Drives detected for controller $get_physical_disks -`n"

foreach ($item in $get_content.Drives)
{
$id = "@odata.id"
$drive_uri = $item.$id
$uri = "https://$idrac_ip$drive_uri"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}
if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, GET request failed, statuscode {0} returned",$result.StatusCode)
    return
}
$disk = $drive_uri.Split("/")[-1]
$get_content = $result.Content | ConvertFrom-Json
$raid_status = $get_content.Oem.Dell.DellPhysicalDisk.RaidStatus
Write-Host "$disk, RaidStatus = $raid_status"

}
}

#############################################################################################################################

if ($get_physical_disks_details)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$get_physical_disks_details"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}
if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, GET request failed, statuscode {0} returned",$result.StatusCode)
    return
}
$get_content = $result.Content | ConvertFrom-Json
foreach ($item in $get_content.Drives)
{
$id = "@odata.id"
$drive_uri = $item.$id
$uri = "https://$idrac_ip$drive_uri"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
}
else
{
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
    return
    }
}
if ($result.StatusCode -eq 200)
{
}
else
{
    [String]::Format("`n- FAIL, GET request failed, statuscode {0} returned",$result.StatusCode)
    return
}
$disk = $drive_uri.Split("/")[-1]
Write-Host "`n- Detailed DMTF drive information for $disk -`n"
$get_content = $result.Content | ConvertFrom-Json
$get_content

Write-Host "`n- Detailed OEM drive information for $disk -`n"
$get_content.Oem.Dell.DellPhysicalDisk

}
}

#############################################################################################################################

if ($create_virtual_disk)
{
$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$create_virtual_disk/Volumes"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}

$get_result = $result.Content | ConvertFrom-Json
$current_vd_count = $get_result.Members.Count

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$create_virtual_disk/Volumes"

if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Body $vd_payload -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -Body $vd_payload -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


else
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $vd_payload -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $vd_payload -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

    if ($result1.StatusCode -eq 202)
    {
    $get_result = $result1.RawContent | ConvertTo-Json -Compress
    $get_jobid = [regex]::Match($get_result, "JID_.+?r").captures.groups[0].value
    $job_id = $get_jobid.Replace("\r","")
    [String]::Format("`n- PASS, statuscode {0} returned to successfully create virtual disk for controller {1}, {2} job ID created",$result1.StatusCode,$create_virtual_disk,$job_id)
    Start-Sleep 10
    }
    else
    {
    [String]::Format("- FAIL, statuscode {0} returned to create virtual disk",$result1.StatusCode)
    return
    }

$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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
 
$overall_job_output=$result.Content | ConvertFrom-Json

if ($overall_job_output.JobType -eq "RealTimeNoRebootConfiguration")
{
$job_type = "realtime_config"
Write-Host "- INFO, create virtual disk job will run in real time operation, no server reboot needed to apply the changes"
}
if ($overall_job_output.JobType -eq "RAIDConfiguration")
{
$job_type = "staged_config"
Write-Host "- INFO, create virtual disk job will run in staged operation, server reboot needed to apply the changes"
}

if ($job_type -eq "realtime_config")
{
while ($overall_job_output.JobState -ne "Completed")
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id" 
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}

    $overall_job_output = $result.Content | ConvertFrom-Json
        if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
        {
        Write-Host
        [String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
        return
        }
        else
        {
        $job_message = $overall_job_output.Message
        [String]::Format("- INFO, job not marked completed, current status: {0}",$job_message.TrimEnd("."))
        Start-Sleep 3
        }
    }
Write-Host
Start-Sleep 10
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}
$overall_job_output = $result.Content | ConvertFrom-Json
$overall_job_output

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Storage/$create_virtual_disk/Volumes"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}

$get_result = $result.Content | ConvertFrom-Json
$new_vd_count = $get_result.Members.Count

if ($new_vd_count -gt $current_vd_count)
{
Write-Host "- PASS, virtual disk successfully created for storage controller $create_virtual_disk"
}
else
{
Write-Host "- FAIL, virtual disk not successfully created for storage controller $create_virtual_disk"
Return
}
Write-Host
return
}

if ($job_type -eq "staged_config")
{
while ($overall_job_output.Message -ne "Task successfully scheduled.")
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
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
$job_message = $overall_job_output.Message
[String]::Format("- INFO, job not marked completed, current status: {0}",$job_message.TrimEnd("."))
Start-Sleep 1
}
}

Write-Host "`n- PASS, $job_id successfully scheduled, rebooting server"



$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}
$get_content = $result.Content | ConvertFrom-Json
$host_power_state = $get_content.PowerState

if ($host_power_state -eq "On")
{
Write-Host "- INFO, server power state ON, performing graceful shutdown"
$JsonBody = @{ "ResetType" = "GracefulShutdown" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


else
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned to request server graceful shutdown",$result1.StatusCode)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

Start-Sleep 10
$count = 1
while ($true)
{
If ($count -eq 5)
{
Write-Host "- FAIL, retry count to validate graceful shutdown has been hit. Manually check server status and reboot to execute the configuration job"
return 
}

$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}
$get_content = $result.Content | ConvertFrom-Json
$host_power_state = $get_content.PowerState

if ($host_power_state -eq "Off")
{
Write-Host "- PASS, verified server is in OFF state"
$host_power_state = ""
break
}
else
{
Write-Host "- INFO, server still in ON state waiting for graceful shutdown to complete, polling power status again"
Start-Sleep 15
$count++
}

}

$JsonBody = @{ "ResetType" = "On" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


else
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

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

if ($host_power_state -eq "Off")
{
Write-Host "- INFO, server power state OFF, performing power ON operation"
$JsonBody = @{ "ResetType" = "On" } | ConvertTo-Json -Compress


$uri = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
if ($x_auth_token)
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -ContentType 'application/json' -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}


else
{
try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -UseBasicParsing -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Body $JsonBody -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -ErrorVariable RespErr
    }
    else
    {
    Ignore-SSLCertificates
    $result1 = Invoke-WebRequest -UseBasicParsing -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
    }
    }
    catch
    {
    Write-Host
    $RespErr
    return
    } 
}

if ($result1.StatusCode -eq 204)
{
    [String]::Format("- PASS, statuscode {0} returned successfully to power ON the server",$result1.StatusCode)
    Start-Sleep 10
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

Start-Sleep 10
}




while ($overall_job_output.JobState -ne "Completed")
{
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}


$overall_job_output = $result.Content | ConvertFrom-Json
if ($overall_job_output.Message -eq "Job failed." -or $overall_job_output.Message -eq "Failed")
{
Write-Host
[String]::Format("- FAIL, job not marked as completed, detailed error info: {0}",$overall_job_output)
return
}
else
{
[String]::Format("- INFO, job not marked completed, current status: {0} Precent complete: {1}",$overall_job_output.Message,$overall_job_output.PercentComplete)
Start-Sleep 10
}
}
Start-Sleep 10
Write-Host
[String]::Format("- PASS, {0} job ID marked as completed!",$job_id)
Write-Host "`n- Detailed final job status results:"
$uri ="https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/$job_id"
if ($x_auth_token)
{
 try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token}
    }
    else
    {
    Ignore-SSLCertificates
    $result = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept"="application/json"; "X-Auth-Token" = $x_auth_token}
    }
    }
    catch
    {
    $RespErr
    return
    }
}

else
{
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
    $RespErr
    return
    }
}

$overall_job_output=$result.Content | ConvertFrom-Json
$overall_job_output
return

}

}

}




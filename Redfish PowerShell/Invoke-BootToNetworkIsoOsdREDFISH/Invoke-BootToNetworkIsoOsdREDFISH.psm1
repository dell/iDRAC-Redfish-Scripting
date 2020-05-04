<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 4.0
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
   Cmdlet using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO. 
.DESCRIPTION
   Cmdlet using Redfish API with OEM extension to either get network ISO attach status, boot to network ISO or detach network ISO. For performing OS installation, it's recommended to unpack and attach driver pack first, then execute cmdlet to perform boot to network ISO.  
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_attach_status: Pass in "y" to get attach status for network ISO.
   - boot_to_network_iso: Pass in "y" to attach and boot to network ISO. You must also use network share arguments along with this argument) 
   - ipaddress: Pass in IP address of the network share.
   - sharetype: Pass in share type of the network share. Supported values are NFS and CIFS.
   - sharename: Pass in network share share name.
   - username: Pass in CIFS username (this argument only required for CIFS share).
   - password: Pass in CIFS username password (this argument only required for CIFS share).
   - imagename: Pass in the operating system(OS) string you want to boot from on your network share.
   - detach: Pass in "y" to detach network ISO
.EXAMPLE
   .\Invoke-BootToNetworkIsoOsdREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_attach_status y
   This example will check network ISO attach status.
.EXAMPLE
   .\Invoke-BootToNetworkIsoOsdREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -boot_to_network_iso y -ipaddress 192.168.0.130 -sharetype NFS -sharename /nfs -imagename WS2012R2.ISO
   This example will attach network ISO and automatically reboot the server, boot to the ISO.
.EXAMPLE
   .\Invoke-BootToNetworkIsoOsdREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -detach y
   This example will detach network ISO.
#>

function Invoke-BootToNetworkIsoOsdREDFISH {




param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$False)]
    [string]$get_attach_status,
    [Parameter(Mandatory=$False)]
    [string]$boot_to_network_iso,
    [Parameter(Mandatory=$False)]
    [string]$ipaddress,
    [Parameter(Mandatory=$False)]
    [string]$sharetype,
    [Parameter(Mandatory=$False)]
    [string]$sharename,
    [Parameter(Mandatory=$False)]
    [string]$username,
    [Parameter(Mandatory=$False)]
    [string]$password,
    [Parameter(Mandatory=$False)]
    [string]$imagename,
    [Parameter(Mandatory=$False)]
    [string]$detach
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


# Setting up iDRAC credentials for functions  

function setup_idrac_creds

{
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::TLS12
$user = $idrac_username
$pass= $idrac_password
$secpasswd = ConvertTo-SecureString $pass -AsPlainText -Force
$global:credential = New-Object System.Management.Automation.PSCredential($user, $secpasswd)
}

# Function to get Powershell version

$global:get_powershell_version = $null

function get_powershell_version 
{
$get_host_info = Get-Host
$major_number = $get_host_info.Version.Major
$global:get_powershell_version = $major_number
}

# Function to get network ISO attach status

function get_attach_status

{
Write-Host "`n- WARNING, getting network ISO attach information for iDRAC $idrac_ip"
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
   try
{
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
if ($result1.StatusCode -eq 200)
{
$get_attach_status=$result1.Content |  ConvertFrom-Json
[String]::Format("`n- PASS, POST command passed to get attach status. Current network ISO attach status is: {0}", $get_attach_status.ISOAttachStatus)
}
Write-Host
}


# Function to boot to network ISO

function boot_to_network_iso

{
Write-Host "`n- WARNING, attaching network ISO for iDRAC $idrac_ip"
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.BootToNetworkISO"
$JsonBody = @{'ImageName'=$imagename;'IPAddress'=$ipaddress;'ShareType'=$sharetype;'ShareName'=$sharename} | ConvertTo-Json -Compress
if ($username -ne "" -and $password -ne "")
{
$JsonBody = @{'ImageName'=$imagename;'IPAddress'=$ipaddress;'ShareType'=$sharetype;'ShareName'=$sharename;'UserName'=$username;'Password'=$password} | ConvertTo-Json -Compress
}

    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
        if ($result1.StatusCode -eq 202)
        {
        Write-Host "- PASS, POST command passed to connect network ISO, cmdlet will now loop checking concrete job status"
        $concrete_job_uri = $result1.Headers.Location
        }
            while ($result2.TaskState -ne "Completed")
            {
            $uri = "https://$idrac_ip$concrete_job_uri"

            try
            {
            if ($global:get_powershell_version -gt 5)
            {
            $result2 = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
            }
            else
            {
            Ignore-SSLCertificates
            $result2 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
            }
            }
            catch
            {
            Write-Host
            $RespErr
            break
            }
            $result2 = $result2.Content | ConvertFrom-Json
            if ($result2.TaskState -eq "Exception")
            {
            [String]::Format("`n- FAIL, concrete job has hit an exception, current job message: '{0}'", $result2.Messages.Message)
            Write-Host "`n- If needed, check iDRAC Lifecycle Logs or Job Queue for more details on the exception.`n"
            return
            }
            else
            {
            $job_status = $result2.TaskState
            Write-Host "- WARNING, polling concrete job, current status: $job_status"
            Start-Sleep 1
            }
            }
Write-Host "- PASS, concrete job marked completed, verifying network ISO attach status"
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
if ($result1.StatusCode -eq 200)
{
$get_attach_status=$result1.Content |  ConvertFrom-Json
}
    if ($get_attach_status.ISOAttachStatus -eq "Attached")
    {
    [String]::Format("- PASS, network ISO verified as attached")
    }
    else
    {
    [String]::Format("`n- FAIL, network ISO not attached, current status is {0}", $get_attach_status.ISOAttachStatus)
    }
Write-Host
}




# Function to detach network ISO

function detach

{
Write-Host "`n- WARNING, detaching network ISO for iDRAC $idrac_ip"
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DetachISOImage"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
if ($result1.StatusCode -eq 200)
{
$get_attach_status=$result1.Content |  ConvertFrom-Json
[String]::Format("`n- PASS, POST command passed to detach network ISO, verifying attach status")
} 
$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    if ($global:get_powershell_version -gt 5)
    {
    $result1 = Invoke-WebRequest -SkipHeaderValidation -SkipCertificateCheck -Uri $uri -Credential $credential -Method Post -ContentType 'application/json' -Headers @{"Accept"="application/json"} -Body $JsonBody -ErrorVariable RespErr
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
    return
    } 
if ($result1.StatusCode -eq 200)
{
$get_attach_status=$result1.Content |  ConvertFrom-Json
}
    if ($get_attach_status.ISOAttachStatus -eq "NotAttached")
    {
    [String]::Format("- PASS, network ISO verified as not attached")
    Start-Sleep 10
    }
    else
    {
    [String]::Format("`n- FAIL, network ISO is not detached, current status is {0}, $get_attach_status.ISOAttachStatus")
    }
Write-Host
}




# Run code

get_powershell_version
setup_idrac_creds

# Code to check for supported iDRAC version installed

$uri = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService"
try
            {
            if ($global:get_powershell_version -gt 5)
            {
            $result2 = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
            }
            else
            {
            Ignore-SSLCertificates
            $result2 = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorAction RespErr -Headers @{"Accept"="application/json"}
            }
            }
            catch
            {
            Write-Host
            $RespErr
            break
            }
if ($get_attach_status -ne "")
{
get_attach_status
}
elseif ($boot_to_network_iso -ne "")
{
boot_to_network_iso
}
elseif ($detach -ne "")
{
detach
}
else
{
Write-Host "- FAIL, either invalid parameter value passed in or missing required parameter"
return
}


}
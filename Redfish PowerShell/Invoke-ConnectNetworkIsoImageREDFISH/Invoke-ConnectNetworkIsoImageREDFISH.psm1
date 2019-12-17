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
   Cmdlet using Redfish API with OEM extension to connect or detach network ISO image. 
.DESCRIPTION
   Cmdlet using Redfish API with OEM extension to connect or detach network ISO image. Connecting the network ISO image will expose the ISO to the server. Note: This action will not automatically reboot the server compared to action BootToNetworkISO.  
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
   - get_attach_status: Pass in "y" to get attach status for network ISO.
   - connect_to_network_iso: Pass in "y" to connect network ISO. You must also use network share arguments along with this argument) 
   - ipaddress: Pass in IP address of the network share.
   - sharetype: Pass in share type of the network share. Supported values are NFS and CIFS.
   - sharename: Pass in network share share name.
   - username: Pass in CIFS username (this argument only required for CIFS share).
   - password: Pass in CIFS username password (this argument only required for CIFS share).
   - imagename: Pass in the operating system(OS) string you want to boot from on your network share.
   - detach: Pass in "y" to detach network ISO
.EXAMPLE
   .\Invoke-ConnectNetworkIsoImageREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -get_attach_status y
   This example will check network ISO attach status.
.EXAMPLE
   .\Invoke-ConnectNetworkIsoImageREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -connect_to_network_iso y -ipaddress 192.168.0.130 -sharetype NFS -sharename /nfs -imagename WS2012R2.ISO
   This example will connect network share ISO image to the server.
.EXAMPLE
   .\Invoke-ConnectNetworkIsoImageREDFISH.ps1 -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -detach y
   This example will detach network ISO.
#>

function Invoke-ConnectNetworkIsoImageREDFISH {


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
    [string]$connect_to_network_iso,
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


# Function to get network ISO attach status

function get_attach_status

{
Write-Host "`n- WARNING, getting network ISO attach information for iDRAC $idrac_ip"
$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    $result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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

[String]::Format("`n- PASS, POST command passed to get attach status. Current network ISO attach status is: {0}", $get_attach_status.ISOAttachStatus)
}
Write-Host
}


# Function to connect to network ISO

function connect_to_network_iso

{
Write-Host "`n- WARNING, attaching network ISO for iDRAC $idrac_ip"
$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.ConnectNetworkISOImage"
$JsonBody = @{'ImageName'=$imagename;'IPAddress'=$ipaddress;'ShareType'=$sharetype;'ShareName'=$sharename} | ConvertTo-Json -Compress
if ($username -ne "" -and $password -ne "")
{
$JsonBody = @{'ImageName'=$imagename;'IPAddress'=$ipaddress;'ShareType'=$sharetype;'ShareName'=$sharename;'UserName'=$username;'Password'=$password} | ConvertTo-Json -Compress
}

    try
    {
    $result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
    }
    catch
    {
    Write-Host
    $RespErr
    return
    }
        if ($result1.StatusCode -eq 202)
        {
        Write-Host "- PASS, POST command passed to connect network ISO, cmdlet will now loop checking concrete job status"
        $concrete_job_uri = $result1.Headers.Location
        }
            while ($result2.TaskState -ne "Completed")
            {
            $u = "https://$idrac_ip$concrete_job_uri"
                try
                {
                $result2 = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing -Headers @{"Accept"="application/json"}
                }
                catch
                {
                [String]::Format("- FAIL, GET command failed for URI {0}, status code {1} returned",$concrete_job_uri, $result2.StatusCode)
                return
                }
            $result2 = $result2.Content | ConvertFrom-Json
            if ($result2.TaskState -eq "Exception")
            {
            [String]::Format("`n- FAIL, concrete job has hit an exception, current job message: '{0}'", $result2.Messages.Message)
            Write-Host "`n- If needed, check Lifecycle Logs or Job Queue for more details on the exception.`n-"
            return
            }
            else
            {
            $job_status = $result2.TaskState
            Write-Host "- WARNING, current concrete job status not marked completed, current status: $job_status"
            Start-Sleep 15
            }
            }
Write-Host "- PASS, concrete job marked completed, verifying network ISO attach status"
$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    $result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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
$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.DisconnectNetworkISOImage"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    $result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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
[String]::Format("`n- PASS, POST command passed to detach network ISO, verifying attach status")
} 
$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService.GetAttachStatus"
$JsonBody = @{} | ConvertTo-Json -Compress
    try
    {
    $result1 = Invoke-WebRequest -Uri $u -Credential $credential -Method Post -Body $JsonBody -ContentType 'application/json' -ErrorVariable RespErr -Headers @{"Accept"="application/json"}
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
    }
    else
    {
    [String]::Format("`n- FAIL, network ISO is not detached, current status is {0}", $get_attach_status.ISOAttachStatus)
    }
Write-Host
}




# Run code

Ignore-SSLCertificates
setup_idrac_creds

# Code to check for supported iDRAC version installed

$u = "https://$idrac_ip/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService"
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
Write-Host "`n- WARNING, iDRAC version detected does not support this feature using Redfish API`n"
$result
return
}

if ($get_attach_status -ne "")
{
get_attach_status
}
elseif ($connect_to_network_iso -ne "")
{
connect_to_network_iso
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


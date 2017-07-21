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
   Cmdlet used to set BIOS to default settings using REDFISH API
   IMPORTANT: Make sure you are using latest Powershell version 5 or newer to execute this cmdlet. Execute "Get-Host" to check the version.
.DESCRIPTION
   Cmdlet used to set BIOS to default settings on the next server reboot. You can execute the cmdlet and reset the BIOS to default settings now or set the flag to 
   reset BIOS to default and on the next reboot, reset to BIOS default will be applied.
   - idrac_ip, REQUIRED, pass in idrac IP
   - idrac_username, REQUIRED, pass in idrac user name
   - idrac_password, REQUIRED, pass in idrac password
   - reboot_now, REQUIRED, pass in "y" for yes, the cmdlet to set the BIOS reset to default flag and reset the server immediately to apply. Pass in "n" for no, this means flag will be set
   to reset the BIOS to default settings but the server will not automatically reboot to apply it. Reset will BIOS will get applied one the next server reboot by the user.
.EXAMPLE
	This example shows reset to BIOS defaults and apply now
    Set-BiosDefaultSetingsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -reboot_now y
.EXAMPLE
	This example shows setting reset to BIOS defaults but will not get applied until next user server reboot
    Set-BiosDefaultSettingsREDFISH -idrac_ip 192.168.0.120 -idrac_username root -idrac_password calvin -reboot_now n
#>

function Set-BiosDefaultSettingsREDFISH {



param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password,
    [Parameter(Mandatory=$True)]
    [string]$reboot_now
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

$u2 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Bios/Actions/Bios.ResetBios/"

$result1 = Invoke-WebRequest -Uri $u2 -Credential $credential -Method Post -ContentType 'application/json'
Start-Sleep 5

if ($result1.StatusCode -eq 200)
{
try
{
$search=[regex]::Match($result1.Content, "BIOSRTDRequested value is modified successfully").captures.groups[0].value
}
catch
{
Write-Host "`n- FAIL, unable to find succcess message string for reset to BIOS defaults POST command"
return
}
    [String]::Format("`n- PASS, statuscode {0} returned to successfully set BIOS reset to defaults flag. BIOS reset to defaults will be applied on next server reboot.",$result1.StatusCode)
}

else
{
    [String]::Format("`n- FAIL, statuscode {0} returned",$result1.StatusCode)
    return
}

if ($reboot_now -eq "n" -or $reboot_now -eq "no")
{
Write-Host -Foreground Yellow "`n- WARNING, user selected to not reboot the server now. Flag is still set to reset BIOS to default settings but won't be applied until next server reboot."
return
}

Write-Host "`n- WARNING, user selected to reboot the server now to apply BIOS reset to defaults."

$u = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/"
$result = Invoke-WebRequest -Uri $u -Credential $credential -Method Get -UseBasicParsing 

if ($result.StatusCode -eq 200)
{
    Write-Host
    [String]::Format("- PASS, statuscode {0} returned successfully to get current power state",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

$get_content=$result.Content
$power_state=[regex]::Match($get_content, "PowerState.+?,").Captures[0].value
$power_state=$power_state -replace (",","")
$power_state=$power_state -split (":")

if ($power_state -eq '"On"')
{
Write-Host "`n- WARNING, Server current power state is ON"
}
else
{
Write-Host "`n- WARNING, Server current power state is OFF"
}

if ($power_state -eq '"On"')
{

$JsonBody = @{ "ResetType" = "ForceOff"
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power OFF the server

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

# POST command to power ON the server

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

}

if ($power_state -eq '"Off"')
{
$JsonBody = @{ "ResetType" = "On"
    } | ConvertTo-Json


$u4 = "https://$idrac_ip/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"

# POST command to power ON the server

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

}

Write-Host -Foreground Yellow "`n- WARNING, system will now POST and reset the BIOS to default settings, automatically reboot one more time to complete the process. Once the server is back in idle state, execute the SET bios attributes cmdlet to view the default BIOS settings"

}
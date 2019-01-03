<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0

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
   Cmdlet used to get iDRAC lifecycle logs
.DESCRIPTION
   Cmdlet used to get iDRAC lifecycle logs using Redfish API. Lifecycle logs will be printed to the screen and also collected in "lifecycle_logs.txt" file.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username
   - idrac_password: Pass in iDRAC username password
.EXAMPLE
   .\Get-IdracLifecycleLogsREDFISH -idrac_ip 192.168.0.120 -username root -password calvin
#>

function Get-IdracLifecycleLogsREDFISH {




param(
    [Parameter(Mandatory=$True)]
    [string]$idrac_ip,
    [Parameter(Mandatory=$True)]
    [string]$idrac_username,
    [Parameter(Mandatory=$True)]
    [string]$idrac_password
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




$u = "https://$idrac_ip/redfish/v1/Managers/iDRAC.Embedded.1/Logs/Lclog"
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
    [String]::Format("`n- PASS, statuscode {0} returned successfully to get lifecycle contoller(LC) logs`n",$result.StatusCode)
}
else
{
    [String]::Format("- FAIL, statuscode {0} returned",$result.StatusCode)
    return
}

# Converting PS Custom Object to hashtable, print lifecycle logs to the screen 

$z=$result.Content | ConvertFrom-Json
$ht2 = @{}
$z.psobject.properties | Foreach { $ht2[$_.Name] = $_.Value }
$ht2.Members
try 
{
    Remove-Item("lifecycle_logs.txt") -ErrorAction Stop
    Write-Host "- WARNING, lifecycle_logs.txt file detected, file deleted and will create new file with attributes and current values"
}
catch [System.Management.Automation.ActionPreferenceStopException] 
{
    Write-Host "- WARNING, lifecycle_logs.txt file not detected, delete file not executed"
}
Write-Host -ForegroundColor Yellow "`n- WARNING, lifecycle logs also copied to ""lifecycle_logs.txt"" file"

# Write lifecyle logs hashtable to "lifecycle_logs.txt" file

$get_date = Get-Date
$time_stamp = [String]::Format("- LC logs collect timestamp: {0}",$get_date)
Add-Content lifecycle_logs.txt $time_stamp
Add-Content lifecycle_logs.txt "`n"
foreach ($i in $ht2.Members)
{
$i=[string]$i
$ii=$i.Split(";")
Add-Content lifecycle_logs.txt $ii
Add-Content lifecycle_logs.txt "`n"
}

}

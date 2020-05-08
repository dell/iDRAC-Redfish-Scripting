<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 2.0

Copyright (c) 2020, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>




<#
.Synopsis
   Cmdlet used to create Powershell directory structure for cmdlets if doesn't exist and download cmdlets from Dell iDRAC gitHub site. 
.DESCRIPTION
   Cmdlet used to create Powershell directory structure for cmdlets if doesn't exist and download cmdlets from Dell iDRAC gitHub site (https://github.com/dell/iDRAC-Redfish-Scripting/tree/master/Redfish%20PowerShell).
   - powershell_version: Pass in value of 'old" if you are using Powershell version 5 or older. if using PowerSehll version 6 or newer, pass in a value of 'new'.
   - os_username: Pass in your OS username to create the directory structure for downloading cmdlets which will allow auto import of cmdlets when launching PowerShell session. 
.EXAMPLE
   .\create_dir_structure_download_iDRAC_Redfish_cmdlets -powershell_version old -os_username administrator 
   This example using Powershell 5 or older will create directory structure if doesn't already exist for OS user administrator. The directory structure will be '"C:\Users\Administrator\Documents\WindowsPowerShell\Modules'
#>



param(
[Parameter(Mandatory=$true)]
[string]$powershell_version,
[Parameter(Mandatory=$true)]
[string]$os_username
)

if ($powershell_version.ToLower() -eq "old")
{
$powershell_version = "WindowsPowerShell"
}
elseif ($powershell_version.ToLower() -eq "new")
{
$powershell_version = "PowerShell"
}
else
{
Write-Host "- FAIL, invalid value passed in for powershell_version"
return
}

Write-Host "`n- WARNING, downloading cmdlets from GitHub, this may take a few minutes to complete. If PowerShell directory structure doesn't exist, script will create it.`n"

[Net.ServicePointManager]::SecurityProtocol = "tls12, tls11, tls"
$web_request_output = Invoke-WebRequest -UseBasicParsing "https://github.com/dell/iDRAC-Redfish-Scripting/tree/master/Redfish%20PowerShell"
Start-Sleep 5
$get_href = $web_request_output.Links | Select href
$cmdlet_names_array = @()
[System.Collections.ArrayList]$cmdlet_names_array = $cmdlet_names_array
foreach ($i in $get_href) 
{
$i=[string]$i
if ($i.Contains("tree"))
{
$i=$i.Split("/")[-1]
$i=$i.Replace("}","")
$cmdlet_names_array.Add($i) | out-null
}
}
$cmdlet_names_array.RemoveAt(0)
$cmdlet_names_array.RemoveAt(0)
$retry_count = 0
foreach ($i in $cmdlet_names_array)
{
if ($retry_count -eq 70)
{
Write-Host "- FAIL, max retry count has been reached. Check dirctory $path to see if all directories have been created for cmdlets"
return 
}
$path = "C:\Users\$os_username\Documents\$powershell_version\Modules\$i"
$raw_dir = $i+"/"+$i+".psm1"
if(!(test-path $path))
{
      New-Item -ItemType Directory -Force -Path $path | out-null
      Start-Sleep 3
      try
      {
      (new-object net.webclient).DownloadString("https://raw.githubusercontent.com/dell/iDRAC-Redfish-Scripting/master/Redfish%20PowerShell/$raw_dir") | Out-File "C:\Users\$os_username\Documents\$powershell_version\Modules\$raw_dir"
      }
      catch
      {
      Write-Host "- FAIL, unable to download cmdlet from GitHub, retry"
      $retry_count++
      continue
      }
}

}

Write-Host "`n- PASS, script complete. Powershell directory location 'C:\Users\$os_username\Documents\$powershell_version\Modules' which contains iDRAC Redfish cmdlets. Relaunch or reload PowerShell session to start using cmdlets.`n" 





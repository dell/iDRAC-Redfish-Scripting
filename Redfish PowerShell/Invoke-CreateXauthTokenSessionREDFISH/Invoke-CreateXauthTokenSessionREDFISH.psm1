<#
_author_ = Texas Roemer <Texas_Roemer@Dell.com>
_version_ = 10.0

Copyright (c) 2021, Dell, Inc.

This software is licensed to you under the GNU General Public License,
version 2 (GPLv2). There is NO WARRANTY for this software, express or
implied, including the implied warranties of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
along with this software; if not, see
http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
#>

<#
.Synopsis
   iDRAC cmdlet using Redfish API to create iDRAC X-auth token session.
.DESCRIPTION
   iDRAC cmdlet using Redfish API to either view, create or delete iDRAC X-auth token session.
   - idrac_ip: Pass in iDRAC IP address
   - idrac_username: Pass in iDRAC username (Optional: Not passing in username/password parameters will prompt you to enter using Get-Credentail)
   - idrac_password: Pass in iDRAC username password (Optional: Not passing in username/password parameters will prompt you to enter using Get-Credentail)
   - x_auth_token: Pass in X-Auth token session with get_session_details argument to test your token key.
   - get_session_details: Get session details for all iDRAC active sessions.
   - create_x_auth_token_session: Create new X-auth token session for the iDRAC.
   - delete_idrac_session: Pass in the complete session URI to delete If needed, use get_session_details argument to get the URI you want to delete.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -get_session_details 
   This example will return all active iDRAC sessions.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -get_session_details  
   This example will first prompt for username/password using Get-Credential, then return all active iDRAC sessions.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -get_session_details -x_auth_token e2b4efa6b8743bad87d553debc03a203
   This example will return all active iDRAC sessions using X-auth token session for authentication.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -create_x_auth_token_session 
   This example will create a new X-auth token session for the iDRAC.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -create_x_auth_token_session 
   This example will first prompt for iDRAC username/password using Get-Credential, then create a new X-auth token session for the iDRAC.
.EXAMPLE
   Invoke-CreateXauthTokenSessionREDFISH -idrac_ip 192.168.0.120 -username root -password calvin -delete_idrac_session /redfish/v1/SessionService/Sessions/22
   This example will delete iDRAC session /redfish/v1/SessionService/Sessions/22.
#>

function Invoke-CreateXauthTokenSessionREDFISH {

    param(
        [Parameter(Mandatory = $True)]
        [string]$idrac_ip,
        [Parameter(Mandatory = $False)]
        [string]$idrac_username,
        [Parameter(Mandatory = $False)]
        [string]$idrac_password,
        [Parameter(Mandatory = $False)]
        [string]$x_auth_token,
        [Parameter(Mandatory = $False)]
        [switch]$get_session_details,
        [Parameter(Mandatory = $False)]
        [switch]$create_x_auth_token_session,
        [Parameter(Mandatory = $False)]
        [string]$delete_idrac_session
    )


    function Ignore-SSLCertificates {
        $Provider = New-Object Microsoft.CSharp.CSharpCodeProvider
        $Compiler = $Provider.CreateCompiler()
        $Params = New-Object System.CodeDom.Compiler.CompilerParameters
        $Params.GenerateExecutable = $false
        $Params.GenerateInMemory = $true
        $Params.IncludeDebugInformation = $false
        $Params.ReferencedAssemblies.Add("System.DLL") > $null
        $TASource = @'
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
        $TAResults = $Provider.CompileAssemblyFromSource($Params, $TASource)
        $TAAssembly = $TAResults.CompiledAssembly
        ## We create an instance of TrustAll and attach it to the ServicePointManager
        $TrustAll = $TAAssembly.CreateInstance("Local.ToolkitExtensions.Net.CertificatePolicy.TrustAll")
        [System.Net.ServicePointManager]::CertificatePolicy = $TrustAll
    }

    $global:get_powershell_version = $null

    function get_powershell_version {
        $get_host_info = Get-Host
        $major_number = $get_host_info.Version.Major
        $global:get_powershell_version = $major_number
    }
    get_powershell_version

    function setup_idrac_creds {

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
    setup_idrac_creds

   

    ###########################
    ### Get session details ###
    ###########################

    if ($get_session_details) {
        $uri = "https://$idrac_ip/redfish/v1/SessionService/Sessions"

        if ($x_auth_token) {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token }
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token }
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }
        else {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" }
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" }
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }


        if ($result.StatusCode -eq 200) {
        }
        else {
            [String]::Format("`n- FAIL, GET request failed to get session details, statuscode {0} returned", $result.StatusCode)
            return
        }

        $get_content = $result.Content | ConvertFrom-Json
        $odata_id = '@odata.id'
        if ($get_content.Members.count -eq 0) {
            Write-Host "`n- INFO, no sessions detected."
            return
        }
        else {
            foreach ($item in $get_content.Members.$odata_id) {
                $uri = "https://$idrac_ip$item"
                if ($x_auth_token) {
                    try {
                        if ($global:get_powershell_version -gt 5) {
                            $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token }
                        }
                        else {
                            Ignore-SSLCertificates
                            $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token }
                        }
                    }
                    catch {
                        Write-Host
                        $RespErr
                        return
                    }
                }
                else {
                    try {
                        if ($global:get_powershell_version -gt 5) {
                            $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" }
                        }
                        else {
                            Ignore-SSLCertificates
                            $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Get -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" }
                        }
                    }
                    catch {
                        Write-Host
                        $RespErr
                        return
                    }
                }


                if ($result.StatusCode -eq 200) {
                    Write-Host "`n- Details for sessions URI $item`n"
                    $result.Content | ConvertFrom-Json
                }
                else {
                    [String]::Format("`n- FAIL, GET request failed to get session details for specific URI, statuscode {0} returned", $result.StatusCode)
                    return
                }

            }
        }
    }

    ###################################
    ### Create X Auth token session ###
    ###################################

    if ($create_x_auth_token_session) {

        $uri = "https://$idrac_ip/redfish/v1/SessionService/Sessions"

        if ($idrac_password) {
            $JsonBody = @{'UserName' = $idrac_username; 'Password' = $idrac_password } | ConvertTo-Json -Compress
        }
        else {
            $JsonBody = @{'UserName' = $credential.GetNetworkCredential().UserName; 'Password' = $credential.GetNetworkCredential().Password } | ConvertTo-Json -Compress
        }

        if ($x_auth_token) {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Body $JsonBody -Method Post -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token } -ContentType 'application/json'
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Body $JsonBody -Method Post -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token } -ContentType 'application/json'
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }
        else {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Body $JsonBody -Method Post -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" } -ContentType 'application/json'
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Body $JsonBody -Method Post -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" } -ContentType 'application/json'
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }

        if ($result.StatusCode -eq 201) {
        }
        else {
            [String]::Format("`n- FAIL, POST request failed to create X-Auth token session, statuscode {0} returned", $result.StatusCode)
            return
        }

        Write-Host "`n- PASS, new iDRAC token session successfully created`n"
        $result.Headers
    }


    ###################################
    ### Delete iDRAC session ###
    ###################################

    if ($delete_idrac_session) {
        $uri = "https://$idrac_ip$delete_idrac_session"

        if ($x_auth_token) {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Delete -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token } -ContentType 'application/json'
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Delete -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json"; "X-Auth-Token" = $x_auth_token } -ContentType 'application/json'
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }
        else {
            try {
                if ($global:get_powershell_version -gt 5) {
                    $result = Invoke-WebRequest -SkipCertificateCheck -SkipHeaderValidation -Uri $uri -Credential $credential -Method Delete -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" } -ContentType 'application/json'
                }
                else {
                    Ignore-SSLCertificates
                    $result = Invoke-WebRequest -Uri $uri -Credential $credential -Method Delete -UseBasicParsing -ErrorVariable RespErr -Headers @{"Accept" = "application/json" } -ContentType 'application/json'
                }
            }
            catch {
                Write-Host
                $RespErr
                return
            }
        }

        if ($result.StatusCode -eq 200 -or $result.StatusCode -eq 204) {
            "`n- PASS, session '$delete_idrac_session' successfully deleted"
        }
        else {
            [String]::Format("`n- FAIL, DELETE failed to delete session, statuscode {0} returned", $result.StatusCode)
            return
        }
    }



   

}

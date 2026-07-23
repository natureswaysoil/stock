param(
    [Parameter(Mandatory = $true)]
    [string]$CredentialPath,

    [Parameter(Mandatory = $true)]
    [string]$Recipient,

    [Parameter(Mandatory = $true)]
    [string]$CsvPath,

    [Parameter(Mandatory = $true)]
    [string]$Subject,

    [Parameter(Mandatory = $true)]
    [string]$Body
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CredentialPath -PathType Leaf)) {
    throw "Encrypted credential not found: $CredentialPath"
}
if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) {
    throw "CSV attachment not found: $CsvPath"
}

$credential = Import-Clixml -LiteralPath $CredentialPath
$message = [System.Net.Mail.MailMessage]::new()
$smtp = [System.Net.Mail.SmtpClient]::new("smtp.gmail.com", 587)
$attachment = $null

try {
    $message.From = $credential.UserName
    [void]$message.To.Add($Recipient)
    $message.Subject = $Subject
    $message.Body = $Body

    $attachment = [System.Net.Mail.Attachment]::new($CsvPath)
    [void]$message.Attachments.Add($attachment)

    $smtp.EnableSsl = $true
    $smtp.Credentials = $credential.GetNetworkCredential()
    $smtp.Send($message)
    Write-Output "Results emailed to $Recipient"
}
finally {
    if ($null -ne $attachment) {
        $attachment.Dispose()
    }
    $message.Dispose()
    $smtp.Dispose()
}

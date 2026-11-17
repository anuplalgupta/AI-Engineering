# Writes ai-lms\deploy\.env with new random passwords and secrets.
# Run once before the first start:   powershell -ExecutionPolicy Bypass -File ai-lms\deploy\setup.ps1
# For a demo on a public server, add:  -PublicDemo
param([switch]$PublicDemo)
$ErrorActionPreference = 'Stop'

$envFile = Join-Path $PSScriptRoot '.env'

function New-RandomHex([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($buffer)
    $rng.Dispose()
    return -join ($buffer | ForEach-Object { $_.ToString('x2') })
}

if (Test-Path $envFile) {
    # A file from an earlier version may lack a newer setting: add it, change nothing else.
    if (-not (Select-String -Path $envFile -Pattern '^APP_DB_PASSWORD=' -Quiet)) {
        $text = [System.IO.File]::ReadAllText($envFile)
        if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += "`n" }
        $text += "APP_DB_PASSWORD=$(New-RandomHex 24)`n"
        [System.IO.File]::WriteAllText($envFile, $text, (New-Object System.Text.UTF8Encoding $false))
        Write-Host "Added the new setting APP_DB_PASSWORD to $envFile; nothing else was changed."
        exit 0
    }
    Write-Host "$envFile already exists, so nothing was changed."
    Write-Host 'It holds the passwords for your existing data. To start again from nothing, see'
    Write-Host '"Wipe everything" in ai-lms\docs\guide.md.'
    exit 1
}

if ($PublicDemo) {
    $accessCode = New-RandomHex 6
    $publicDemoValue = 'true'
    $signupOpen = 'false'
} else {
    $accessCode = ''
    $publicDemoValue = 'false'
    $signupOpen = 'true'
}

$lines = @(
    '# Written by setup.ps1. Keep this file private and never commit it.'
    '# Deleting it does not delete your data, but the data cannot be opened without it.'
    "POSTGRES_PASSWORD=$(New-RandomHex 24)"
    "APP_DB_PASSWORD=$(New-RandomHex 24)"
    "SECRET_KEY=$(New-RandomHex 32)"
    "OBJECTSTORE_ACCESS_KEY=ailms$(New-RandomHex 8)"
    "OBJECTSTORE_SECRET_KEY=$(New-RandomHex 24)"
    ''
    '# Demo mode: entry as the demo accounts without an email code (never for real students).'
    'DEMO_MODE=true'
    "PUBLIC_DEMO=$publicDemoValue"
    "DEMO_ACCESS_CODE=$accessCode"
    "SIGNUP_OPEN=$signupOpen"
)
# Plain UTF-8 without a byte-order mark and with LF line endings, as Docker Compose expects.
[System.IO.File]::WriteAllText($envFile, (($lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding $false))

Write-Host "Wrote $envFile"
if ($PublicDemo) { Write-Host "Public demo access code: $accessCode  (also kept in that file)" }
Write-Host 'Next: docker compose -p ailms -f ai-lms/deploy/compose.yaml up -d'

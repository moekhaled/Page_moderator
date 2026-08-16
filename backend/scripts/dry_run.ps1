$ErrorActionPreference = "Stop"

Write-Host "[1/6] Checking Docker daemon..."
docker info | Out-Null

Write-Host "[2/6] Validating compose config..."
docker compose config | Out-Null

Write-Host "[3/6] Starting stack (postgres, migrator, app, workers)..."
docker compose up -d postgres
Start-Sleep -Seconds 2
docker compose run --rm migrator
docker compose up -d app llm-worker outbound-worker

Write-Host "[4/6] Waiting for health endpoint..."
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
  try {
    $resp = Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
    if ($resp.status -eq "ok") { $ok = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}
if (-not $ok) { throw "Health endpoint did not become ready." }

Write-Host "[5/6] Sending signed webhook smoke event..."
$verifySecret = $env:META_APP_SECRET
if (-not $verifySecret) { throw "META_APP_SECRET must be set in environment before running script." }

$payload = '{"object":"instagram","entry":[{"messaging":[{"sender":{"id":"12345"},"recipient":{"id":"17890000000000000"},"timestamp":1730000000000,"message":{"mid":"mid.dryrun.1","text":"How much is package A?"}}]}]}'

$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($verifySecret)
$hashBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
$hash = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLowerInvariant()
$signature = "sha256=$hash"

$headers = @{ "X-Hub-Signature-256" = $signature; "Content-Type" = "application/json" }
$webhookResp = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/webhook/meta" -Headers $headers -Body $payload
Write-Host ("Webhook response: " + ($webhookResp | ConvertTo-Json -Compress))

Write-Host "[6/6] Showing service status..."
docker compose ps

Write-Host "Dry run completed successfully."

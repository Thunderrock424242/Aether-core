param(
  [Parameter(Mandatory = $true)]
  [string]$Lesson,
  [string]$SessionId = $(if ($env:AETHER_SESSION_ID) { $env:AETHER_SESSION_ID } else { 'dev-player-1' }),
  [string]$BaseUrl = $(if ($env:AETHER_BASE_URL) { $env:AETHER_BASE_URL } else { 'http://127.0.0.1:8765' })
)

$teachUrl = ($BaseUrl.TrimEnd('/')) + '/teach'
$learningUrl = ($BaseUrl.TrimEnd('/')) + "/learning/$SessionId"

$payload = @{
  lesson = $Lesson
  session_id = $SessionId
} | ConvertTo-Json -Compress

Write-Host "Teaching session '$SessionId' via $teachUrl"
$teachResponse = Invoke-RestMethod -Uri $teachUrl -Method Post -ContentType 'application/json' -Body $payload
Write-Host "POST /teach response: $(($teachResponse | ConvertTo-Json -Compress))"
Write-Host 'Current lessons:'
Invoke-RestMethod -Uri $learningUrl -Method Get | ConvertTo-Json

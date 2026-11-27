$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed. Check Docker Desktop: Engine running." }
}

Invoke-Docker info --format '{{.ServerVersion}}'
if (-not (Test-Path -LiteralPath '.env')) { throw 'Local .env is missing.' }
$envValues = @{}
Get-Content -LiteralPath '.env' | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.*)$') { $envValues[$matches[1]] = $matches[2] }
}
foreach ($key in @('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB')) {
    if (-not $envValues[$key]) { throw "Missing setting: $key" }
}
$container = 'delul-db'
$existing = & docker container ls -a --filter "name=^/$container`$" --format '{{.Names}}'
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect containers.' }
if ($existing -eq $container) {
    $image = Invoke-Docker inspect --format '{{.Config.Image}}' $container
    if ($image -ne 'postgres:18-alpine') { throw 'Existing delul-db uses another image; inspect it manually.' }
    Invoke-Docker start $container
} else {
    Invoke-Docker run -d --name $container --env-file .env -p 127.0.0.1:5432:5432 -v delul-pgdata:/var/lib/postgresql postgres:18-alpine
}
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    & docker exec $container pg_isready -U $envValues['POSTGRES_USER'] -d $envValues['POSTGRES_DB'] *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw 'PostgreSQL did not become ready; inspect docker logs delul-db.' }
$exists = Invoke-Docker exec $container psql -U $envValues['POSTGRES_USER'] -d $envValues['POSTGRES_DB'] -tAc "SELECT 1 FROM pg_database WHERE datname='delul_test'"
if (($exists | Out-String).Trim() -ne '1') {
    Invoke-Docker exec $container createdb -U $envValues['POSTGRES_USER'] delul_test
}
Invoke-Docker ps --filter "name=^/$container`$" --format 'table {{.Names}}	{{.Image}}	{{.Status}}	{{.Ports}}'
Invoke-Docker exec $container psql -U $envValues['POSTGRES_USER'] -d $envValues['POSTGRES_DB'] -tAc "SELECT datname FROM pg_database WHERE datname IN ('delul','delul_test') ORDER BY datname"
Write-Host 'PostgreSQL ready: 127.0.0.1:5432. Local password is stored in .env.'

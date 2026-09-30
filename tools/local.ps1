param([ValidateSet('Start','Stop','Status')][string]$Action='Start')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonExe=Join-Path $projectRoot '.venv\Scripts\python.exe'
$manageFile=Join-Path $projectRoot 'manage.py'
$localFolder=Join-Path $projectRoot '.local'
$runtimeFile=Join-Path $localFolder 'runtime.json'

function Get-OwnedProcess($record) {
    $running=Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
    if (-not $running) { return $null }
    # IDs podem ser reutilizados; caminho, comando e data precisam coincidir.
    if ($running.CommandLine -notlike "*$manageFile*" -or $running.CommandLine -notlike "*$($record.command)*" -or $running.CreationDate.ToUniversalTime() -ne ([datetime]$record.created).ToUniversalTime()) {
        throw "Não foi possível confirmar a identidade do processo $($record.pid). Nenhum processo foi encerrado."
    }
    return $running
}

function Get-OwnedTree($records) {
    $all=@(Get-CimInstance Win32_Process)
    $tree=@()
    foreach ($record in $records) {
        $parent=Get-OwnedProcess $record
        if (-not $parent) { continue }
        if ($tree.ProcessId -notcontains $parent.ProcessId) { $tree+=$parent }
        $pending=@($parent.ProcessId)
        while ($pending.Count) {
            $next=@()
            foreach ($ancestor in $pending) {
                foreach ($child in @($all | Where-Object ParentProcessId -eq $ancestor)) {
                    # O console oculto do Windows fecha com o pai; não é um serviço Python.
                    if ($child.ExecutablePath -eq (Join-Path ([Environment]::GetFolderPath('System')) 'conhost.exe')) { continue }
                    if ($child.CommandLine -notlike "*$manageFile*" -or $child.CommandLine -notlike "*$($record.command)*") { throw 'Descendente não confirmado. Nenhum encerramento realizado.' }
                    if ($tree.ProcessId -notcontains $child.ProcessId) { $tree+=$child; $next+=$child.ProcessId }
                }
            }
            $pending=$next
        }
    }
    return $tree
}

if ($Action -eq 'Status' -or $Action -eq 'Stop') {
    if (-not (Test-Path -LiteralPath $runtimeFile)) { Write-Output 'Enlace sem sessão local registrada.'; exit 0 }
    $records=@(Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json)
    # Verificar todo o conjunto antes de realizar qualquer encerramento.
    $confirmed=@(Get-OwnedTree $records)
    if ($Action -eq 'Stop') {
        [array]::Reverse($confirmed)
        foreach ($identity in $confirmed) {
            try { [Diagnostics.Process]::GetProcessById($identity.ProcessId).Kill() } catch [ArgumentException] { }
        }
        Remove-Item -LiteralPath $runtimeFile
        Write-Output 'Servidor e workers do Enlace encerrados. Arquivos e banco preservados.'
    } else {
        $confirmed | Select-Object ProcessId,CreationDate
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie a .venv e instale requirements.txt antes de iniciar.' }
# Confirmar acesso ao inventário de processos antes de lançar um serviço.
Get-CimInstance Win32_Process -Filter "ProcessId = $PID" | Out-Null
if (Test-Path -LiteralPath $runtimeFile) {
    $records=@(Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json)
    $running=@($records | ForEach-Object { Get-OwnedProcess $_ }) | Where-Object { $_ }
    if ($running.Count -gt 0) { throw 'Há uma sessão registrada. Use -Action Status ou -Action Stop antes de iniciar novamente.' }
}
if (Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue) { throw 'A porta 8766 está ocupada. Nenhum processo foi alterado.' }
New-Item -ItemType Directory -Path $localFolder -Force | Out-Null
& $pythonExe $manageFile migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Migrações não concluídas. Serviços não iniciados.' }
$started=@()
try {
    foreach ($service in @(@{name='server';args='runserver 127.0.0.1:8766 --noreload';command='runserver'},@{name='inventory';args='process_inventory';command='process_inventory'},@{name='analysis';args='process_assessments';command='process_assessments'})) {
        $process=Start-Process -FilePath $pythonExe -ArgumentList "`"$manageFile`" $($service.args)" -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localFolder "$($service.name).out.log") -RedirectStandardError (Join-Path $localFolder "$($service.name).err.log") -PassThru
        $identity=Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)"
        if (-not $identity) { throw "O serviço $($service.name) terminou antes da confirmação." }
        $started+=@{pid=$process.Id;created=$identity.CreationDate.ToUniversalTime().ToString('o');command=$service.command}
        $started | ConvertTo-Json | Set-Content -LiteralPath $runtimeFile -Encoding utf8
    }
    $healthy=$false
    for ($attempt=0;$attempt -lt 10;$attempt++) {
        try { $health=Invoke-RestMethod 'http://127.0.0.1:8766/healthz/' -TimeoutSec 2; if ($health.status -eq 'ok') { $healthy=$true; break } } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) { throw 'Servidor não confirmou saúde. Consulte .local/server.err.log.' }
    foreach ($record in $started) { if (-not (Get-OwnedProcess $record)) { throw "Um serviço terminou. Consulte os logs em .local." } }
    $complete=@(Get-OwnedTree $started | ForEach-Object { @{pid=$_.ProcessId;created=$_.CreationDate.ToUniversalTime().ToString('o');command=''} })
    # Cada filho carrega o mesmo comando no argv. Preservar também sua identidade.
    foreach ($record in $complete) {
        $identity=Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
        $record.command=if ($identity.CommandLine -like '*process_inventory*') {'process_inventory'} elseif ($identity.CommandLine -like '*process_assessments*') {'process_assessments'} else {'runserver'}
    }
    $complete | ConvertTo-Json | Set-Content -LiteralPath $runtimeFile -Encoding utf8
    Write-Output 'Enlace ativo em http://127.0.0.1:8766/. Primeiro acesso: /primeiro-acesso/.'
} catch {
    # Mantém o recibo para diagnóstico e parada segura; não mata processos sem verificar.
    throw
}

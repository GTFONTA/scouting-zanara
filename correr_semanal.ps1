# Corrida semanal del scouting. La ejecuta la tarea "Scouting San Isidro" del Programador de tareas.
# Se puede correr a mano:  powershell -ExecutionPolicy Bypass -File correr_semanal.ps1
# Otro municipio (municipios/<slug>/):  powershell -ExecutionPolicy Bypass -File correr_semanal.ps1 -Municipio caba
param([string]$Municipio = "san_isidro")
$ErrorActionPreference = "Continue"
$proyecto = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $proyecto
New-Item -ItemType Directory -Force -Path "$proyecto\runs" | Out-Null
$sufijo = if ($Municipio -eq "san_isidro") { "" } else { "_$Municipio" }
$log = "$proyecto\runs\log$($sufijo)_$(Get-Date -Format 'yyyy-MM-dd_HHmm').txt"
$argumentos = @("-u", "-m", "src.main")
if ($Municipio -ne "san_isidro") { $argumentos += @("--municipio", $Municipio) }
$env:PYTHONIOENCODING = "utf-8"
# Python: la ruta conocida; si se actualizo Python y ya no existe, el lanzador "py" (busca la version instalada).
$python = "C:\Users\ZN - GF\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (Test-Path $python) {
    & $python @argumentos *> $log
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    "Aviso: no se encontro $python; uso el lanzador py" | Out-File $log -Encoding utf8
    & py -3 @argumentos *>> $log
} else {
    "ERROR: no se encontro Python ($python) ni el lanzador py" | Out-File $log -Encoding utf8
    exit 1
}
exit $LASTEXITCODE

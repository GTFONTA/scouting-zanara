# Corridas automáticas mientras la PC está prendida (Gonzalo, 24/11/2026). La ejecuta la tarea
# "Scouting automático" del Programador de tareas: al iniciar sesión, al desbloquear y cada hora.
# src/agenda.py decide si toca una corrida (reglas en config.yaml, agenda:) y, si toca, llama a correr_semanal.ps1.
# Ver qué haría sin correr nada:  py -3 -m src.agenda --ver
$ErrorActionPreference = "Continue"
$proyecto = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $proyecto
$env:PYTHONIOENCODING = "utf-8"
$python = "C:\Users\ZN - GF\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (Test-Path $python) {
    & $python -m src.agenda
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m src.agenda
} else {
    exit 1
}
exit $LASTEXITCODE

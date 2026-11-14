# Fase 4: pasa cada caso de runs\backtest_fase4\casos_excel.csv por la pestaña "Calculadora" del Excel de
# zonificación (docs\Zonificacion_San_Isidro_COU2022_v2.xlsx) y guarda lo que calcula Excel al lado de lo que
# calculó el sistema. Trabaja sobre una copia temporal: el Excel original no se modifica.
# Uso:  powershell -ExecutionPolicy Bypass -File tools\calculadora_excel.ps1
#       y después:  python tools\backtest_fase4.py --comparar-excel
$ErrorActionPreference = "Stop"
$proyecto = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$entrada = Join-Path $proyecto "runs\backtest_fase4\casos_excel.csv"
$salida = Join-Path $proyecto "runs\backtest_fase4\casos_excel_resultado.csv"
$copia = Join-Path $env:TEMP "calculadora_fase4_$(Get-Random).xlsx"
Copy-Item (Join-Path $proyecto "docs\Zonificacion_San_Isidro_COU2022_v2.xlsx") $copia

# celda de la Calculadora -> campo comparado con el sistema
$celdas = [ordered]@{
    "B14" = "m2_fot"; "B16" = "lotes_frente_propio"; "B17" = "lotes_calle_interna"; "B18" = "agrupadas_calle";
    "B19" = "agrupadas_acceso_comun"; "B20" = "multifamiliar_unidades"; "B21" = "ue_unidades";
    "B22" = "unidades_por_derecho"; "B23" = "unidades_con_aprobacion"; "B24" = "usd_por_unidad_derecho";
    "B25" = "usd_por_unidad_aprobacion"
}
$inv = [Globalization.CultureInfo]::InvariantCulture
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $libro = $xl.Workbooks.Open($copia)
    $calc = $libro.Worksheets.Item("Calculadora")
    $filas = foreach ($caso in Import-Csv $entrada) {
        # Formula takes the value in English notation whatever the PC's locale; column 2 = B
        $calc.Cells.Item(4, 2).Value2 = [string]$caso.zona_excel
        $calc.Cells.Item(5, 2).Formula = $caso.superficie_m2
        if ($caso.frente_m) { $calc.Cells.Item(6, 2).Formula = $caso.frente_m }
        else { $calc.Cells.Item(6, 2).ClearContents() | Out-Null }
        $calc.Cells.Item(7, 2).Formula = $caso.precio_usd
        $xl.CalculateFull()
        $fila = [ordered]@{}
        foreach ($p in $caso.PSObject.Properties) { $fila[$p.Name] = $p.Value }
        foreach ($c in $celdas.Keys) {
            $v = $calc.Cells.Item([int]$c.Substring(1), 2).Value2
            $fila["excel_" + $celdas[$c]] = if ($v -is [double]) { $v.ToString($inv) } else { "$v" }
        }
        [pscustomobject]$fila
    }
    $filas | Export-Csv $salida -NoTypeInformation -Encoding UTF8
    $libro.Close($false)
    "$(@($filas).Count) casos -> $salida"
}
finally {
    $xl.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($xl) | Out-Null
    Remove-Item $copia -ErrorAction SilentlyContinue
}

param([string]$Compiler = 'D:/msys2/mingw64/bin/gcc.exe')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
if (-not (Test-Path -LiteralPath $Compiler)) {
    $taskGcc = Get-Command gcc -ErrorAction SilentlyContinue
    if (-not $taskGcc) { throw 'GCC not found. Supply -Compiler with your MinGW-w64 gcc.exe path.' }
    $Compiler = $taskGcc.Source
}
$taskSourcePath = Join-Path $taskRoot 'upstream/sparrow.c'
$taskSourceText = [IO.File]::ReadAllText($taskSourcePath, [Text.Encoding]::UTF8)
function Replace-One([string]$Text, [string]$Pattern, [string]$Replacement) {
    $taskRegex = [regex]::new($Pattern, [Text.RegularExpressions.RegexOptions]::Singleline)
    if ($taskRegex.Matches($Text).Count -ne 1) { throw "Upstream source no longer matches portability patch: $Pattern" }
    return $taskRegex.Replace($Text, [Text.RegularExpressions.MatchEvaluator]{param($m) $Replacement})
}
# Keep the upstream file unchanged. Generate a separate Windows build source.
$taskSourceText = $taskSourceText.Replace('#include <sys/resource.h>', '#include "windows_compat.h"')
$taskSourceText = $taskSourceText.Replace('#include <sys/times.h>', '/* POSIX process timing supplied by windows_compat.h. */')
$taskSourceText = Replace-One $taskSourceText 'void setCpuLimit\(\) \{.*?\r?\n\}\s*void printFormulaProperties' @'
void setCpuLimit() {
    /* Windows checks the requested process CPU budget in the search loop. */
}
void printFormulaProperties
'@
$taskSourceText = Replace-One $taskSourceText 'void setupSignalHandler\(\) \{.*?\r?\n\}' @'
void setupSignalHandler() {
    signal(SIGTERM, handle_interrupt);
    signal(SIGINT, handle_interrupt);
    signal(SIGABRT, handle_interrupt);
}
'@
$taskSearchAnchor = "`t`tfor (flip = 1; flip <=maxFlips; flip++) {"
if (($taskSourceText.Split(@($taskSearchAnchor), [StringSplitOptions]::None)).Count -ne 2) { throw 'Search loop patch anchor mismatch.' }
$taskSourceText = $taskSourceText.Replace($taskSearchAnchor, $taskSearchAnchor + @'

            /* Compatibility check only. No change to variable-selection heuristics. */
            if (cpu_lim >= 0 && (totalFlips & 16383LL) == 0 &&
                sparrow_process_cpu_seconds() >= (double)cpu_lim) {
                maxTries = 0;
                break;
            }
'@)
$taskBuild = Join-Path $taskRoot 'build'
$taskBin = Join-Path $taskRoot 'bin'
New-Item -ItemType Directory -Path $taskBuild,$taskBin -Force | Out-Null
$taskGenerated = Join-Path $taskBuild 'sparrow_windows.c'
[IO.File]::WriteAllText($taskGenerated, $taskSourceText, [Text.UTF8Encoding]::new($false))
$taskExe = Join-Path $taskBin 'sparrow.exe'
# MinGW's linker cannot reliably write to Chinese paths. Compile in an ASCII
# temporary directory, then let PowerShell copy the executable to its location.
$taskCompilerTemp = Join-Path ([IO.Path]::GetTempPath()) ('sparrow-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskCompilerTemp | Out-Null
try {
    Copy-Item -LiteralPath $taskGenerated -Destination (Join-Path $taskCompilerTemp 'sparrow_windows.c')
    Copy-Item -LiteralPath (Join-Path $taskRoot 'platform/windows/windows_compat.h') -Destination $taskCompilerTemp
    Push-Location -LiteralPath $taskCompilerTemp
    try {
        & $Compiler '-std=gnu99' '-fgnu89-inline' '-fno-use-linker-plugin' '-Wall' '-Wextra' '-static' '-O3' '-funroll-loops' '-fexpensive-optimizations' '-DXOR' '-I' '.' 'sparrow_windows.c' '-lm' '-o' 'sparrow.exe'
        if ($LASTEXITCODE -ne 0) { throw "GCC failed with exit code $LASTEXITCODE" }
    } finally { Pop-Location }
    Copy-Item -LiteralPath (Join-Path $taskCompilerTemp 'sparrow.exe') -Destination $taskExe -Force
} finally {
    foreach ($taskTempName in @('sparrow_windows.c','windows_compat.h','sparrow.exe')) {
        $taskTempPath = Join-Path $taskCompilerTemp $taskTempName
        if (Test-Path -LiteralPath $taskTempPath) { Remove-Item -LiteralPath $taskTempPath -Force }
    }
    Remove-Item -LiteralPath $taskCompilerTemp
}
Write-Host "Built: $taskExe"

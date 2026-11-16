param(
    [string]$Instance = (Join-Path $PSScriptRoot 'examples/demo.cnf'),
    [ValidateRange(0,2147483647)][int]$Seed = 1,
    [ValidateRange(1,2147483647)][int]$MaxFlips = 1000000,
    [ValidateRange(1,2147483647)][int]$Runs = 1,
    [ValidateRange(1,86400)][int]$TimeoutSeconds = 60,
    [ValidateRange(0,86400)][int]$CpuSeconds = 0,
    [switch]$Luby,
    [ValidateRange(1,2147483647)][int]$LubyBase = 262144,
    [switch]$NoAssignment,
    [string]$OutputLog
)
$ErrorActionPreference = 'Stop'
$taskExe = Join-Path $PSScriptRoot 'bin/sparrow.exe'
if (-not (Test-Path -LiteralPath $taskExe -PathType Leaf)) { throw 'Run build.ps1 first: bin/sparrow.exe is missing.' }
$taskInput = (Resolve-Path -LiteralPath $Instance).ProviderPath
# Normalize DIMACS and use an ASCII filename: upstream uses narrow-char fopen.
$taskTempFile = Join-Path ([IO.Path]::GetTempPath()) ('sparrow-' + [guid]::NewGuid().ToString('N') + '.cnf')
$taskReader = $null
$taskWriter = $null
$taskProcess = $null
try {
    $taskReader = [IO.StreamReader]::new($taskInput)
    $taskWriter = [IO.StreamWriter]::new($taskTempFile, $false, [Text.Encoding]::ASCII)
    $taskHeaderSeen = $false
    $taskClauseCount = 0
    $taskClauseSize = 0
    $taskClauseVars = [Collections.Generic.HashSet[int]]::new()
    while (($taskLine = $taskReader.ReadLine()) -ne $null) {
        $taskLine = $taskLine.Trim()
        if (-not $taskLine -or $taskLine.StartsWith('c')) { continue }
        if ($taskLine.StartsWith('p')) {
            if ($taskHeaderSeen -or $taskLine -notmatch '^p\s+cnf\s+(\d+)\s+(\d+)$') { throw 'Expected a single DIMACS header: p cnf <variables> <clauses>.' }
            $taskVariables = [int]$Matches[1]
            $taskExpectedClauses = [int]$Matches[2]
            if ($taskVariables -lt 1 -or $taskExpectedClauses -lt 1) { throw 'This launcher requires a nonempty CNF formula.' }
            $taskHeaderSeen = $true
            $taskWriter.WriteLine("p cnf $taskVariables $taskExpectedClauses")
            continue
        }
        if (-not $taskHeaderSeen) { throw 'Missing DIMACS header before the clauses.' }
        foreach ($taskToken in ($taskLine -split '\s+')) {
            $taskLiteral = 0
            if (-not [int]::TryParse($taskToken, [ref]$taskLiteral)) { throw "Invalid DIMACS literal: $taskToken" }
            if ($taskLiteral -eq 0) {
                if ($taskClauseSize -eq 0) { throw 'Empty clauses cannot be searched by this upstream solver.' }
                $taskClauseCount++
                $taskClauseSize = 0
                $taskClauseVars.Clear()
            } else {
                $taskVar = [Math]::Abs([long]$taskLiteral)
                if ($taskVar -gt $taskVariables) { throw "Literal $taskLiteral exceeds the header variable count." }
                if (-not $taskClauseVars.Add([int]$taskVar)) { throw 'Use distinct variables within each clause; remove duplicate literals and tautologies first.' }
                $taskClauseSize++
                if ($taskClauseSize -ge 20000) { throw 'Clause exceeds the upstream clause-size limit.' }
            }
        }
        $taskWriter.WriteLine($taskLine)
    }
    if (-not $taskHeaderSeen -or $taskClauseSize -ne 0 -or $taskClauseCount -ne $taskExpectedClauses) { throw 'DIMACS clause count or final zero terminator does not match the header.' }
    $taskReader.Dispose(); $taskReader = $null
    $taskWriter.Dispose(); $taskWriter = $null
    # Explicit --randomc initializes the upstream clause-selection function.
    $taskArgs = @('--randomc','1','--runs',"$Runs",'--maxflips',"$MaxFlips")
    if (-not $NoAssignment) { $taskArgs += '-a' }
    if ($CpuSeconds -gt 0) { $taskArgs += @('--timeout',"$CpuSeconds") }
    if ($Luby) { $taskArgs += @('--luby','--luby_base',"$LubyBase") }
    $taskArgs += @($taskTempFile,"$Seed")
    $taskInfo = [Diagnostics.ProcessStartInfo]::new()
    $taskInfo.FileName = $taskExe
    $taskInfo.Arguments = (($taskArgs | ForEach-Object { '"' + $_ + '"' }) -join ' ')
    $taskInfo.UseShellExecute = $false
    $taskInfo.CreateNoWindow = $true
    $taskInfo.RedirectStandardOutput = $true
    $taskInfo.RedirectStandardError = $true
    $taskProcess = [Diagnostics.Process]::new()
    $taskProcess.StartInfo = $taskInfo
    $taskWatch = [Diagnostics.Stopwatch]::StartNew()
    [void]$taskProcess.Start()
    $taskStdoutRead = $taskProcess.StandardOutput.ReadToEndAsync()
    $taskStderrRead = $taskProcess.StandardError.ReadToEndAsync()
    $taskTimedOut = -not $taskProcess.WaitForExit($TimeoutSeconds * 1000)
    if ($taskTimedOut) { $taskProcess.Kill(); $taskProcess.WaitForExit() }
    $taskWatch.Stop()
    $taskStdout = $taskStdoutRead.GetAwaiter().GetResult()
    $taskStderr = $taskStderrRead.GetAwaiter().GetResult()
    $taskExit = $taskProcess.ExitCode
    if ($taskStdout) { Write-Output $taskStdout.TrimEnd() }
    if ($taskStderr) { Write-Output $taskStderr.TrimEnd() }
    if ($taskTimedOut) { $taskStatus = 'UNKNOWN (wall-clock timeout)' }
    elseif ($taskExit -eq 10 -and $taskStdout -match '(?m)^s SATISFIABLE') { $taskStatus = 'SATISFIABLE' }
    elseif ($taskExit -eq 0) { $taskStatus = 'UNKNOWN (search budget exhausted; this does not prove UNSAT)' }
    else { throw "Sparrow failed with exit code $taskExit." }
    $taskSummary = "Result: $taskStatus`nInput: $taskInput`nWall time: $($taskWatch.Elapsed.TotalSeconds.ToString('F3', [Globalization.CultureInfo]::InvariantCulture)) s`nNative exit code: $taskExit"
    Write-Output $taskSummary
    if ($OutputLog) {
        $taskLogPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputLog)
        [IO.File]::WriteAllText($taskLogPath, $taskStdout + $taskStderr + "`n" + $taskSummary, [Text.UTF8Encoding]::new($false))
    }
} finally {
    if ($taskReader) { $taskReader.Dispose() }
    if ($taskWriter) { $taskWriter.Dispose() }
    if ($taskProcess) { if (-not $taskProcess.HasExited) { $taskProcess.Kill(); $taskProcess.WaitForExit() }; $taskProcess.Dispose() }
    if (Test-Path -LiteralPath $taskTempFile) { Remove-Item -LiteralPath $taskTempFile -Force }
}

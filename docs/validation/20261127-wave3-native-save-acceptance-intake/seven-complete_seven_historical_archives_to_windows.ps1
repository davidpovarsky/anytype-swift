$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = 'C:\Users\DAVID\Code\anytype-wave3-mac-artifacts-20261127\historical-evidence-seven-20261127-01'
$macAudit = '/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs/seven-historical-archives-preservation2'
$macController = '/Users/m1/sentinelx/uploads/pinkha-wave3-preserve-seven-archives-reference-fixed-20261127.py'
$manifestSHA = 'd6575b864418cd7b8fdde83776a0fdb4138c70ffb252f81f855fa96c7d7e8c86'
$observationSHA = '9405861bd769db68cef51fc02318756560e91bd63629e31fbf8326f623c02abd'
$controllerSHA = 'f953ab341db150651c93ae46f17703459e34455cdf4015d1b5817554e0cca405'
$names = @('01-t2-fixed-originals-private.tar.gz','02-bin-leaf-pass-originals.tar.gz','03-original-runtime-recovery.tar.gz','04-bin-confirmation-aa261-failure.tar.gz','05-bin410b-originals.tar.gz','06-original-t2-mixed-build-and-executions.tar.gz','07-sdk9565-originals.tar.gz')
$ssh = (Get-Command ssh -ErrorAction Stop).Source
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Require($value, [string]$why) { if(-not $value) { throw $why } }
function SHA([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Write-JSON([string]$path, $value) {
    Require (-not (Test-Path -LiteralPath $path)) 'Receipt already exists'
    [System.IO.File]::WriteAllText($path, (($value | ConvertTo-Json -Depth 30) + "`n"), $utf8)
    return [ordered]@{path=$path;sha256=(SHA $path);bytes=(Get-Item -LiteralPath $path).Length}
}
function Copy-SSH-Binary([string]$remoteCommand, [string]$target, [string]$label) {
    Require (-not (Test-Path -LiteralPath $target)) 'Destination already exists'
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $ssh
    $info.Arguments = '-o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 scaleway-mac "' + $remoteCommand + '"'
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    $stream = [System.IO.File]::Open($target, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        Require ($process.Start()) 'Pinned SSH did not start'
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $copyTask = $process.StandardOutput.BaseStream.CopyToAsync($stream)
        if(-not $copyTask.Wait(300000)) { $process.Kill(); throw 'Owned binary transfer exceeded 300 seconds' }
        [void]$copyTask.GetAwaiter().GetResult()
        $stream.Flush($true)
        if(-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Owned SSH did not terminate after transfer' }
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $stderrPath = Join-Path $root ($label + '.stderr.txt')
        [System.IO.File]::WriteAllText($stderrPath, $stderr, $utf8)
        Require ($process.ExitCode -eq 0) ('Pinned SSH source transfer failed: ' + $label)
        return [ordered]@{ownedSSHPID=$process.Id;exitCode=$process.ExitCode;stderr=$stderr;stderrPath=$stderrPath;stderrSHA256=(SHA $stderrPath)}
    } finally {
        $stream.Dispose()
        if($process.Id -and -not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
}

Require ($env:USERNAME -eq 'DAVID') 'Expected existing Windows owner context'
Require (Test-Path -LiteralPath $root -PathType Container) 'Original private backup directory required'
$originalFailurePath = Join-Path $root 'receipt.json'
Require ((SHA $originalFailurePath) -eq '3c15d4ca13052a6b05b9fa639f10625756d4a10c8cdff62166c0e9e48e9b0bd0') 'Exact original transfer failure required'
$failure = Get-Content -LiteralPath $originalFailurePath -Raw | ConvertFrom-Json
Require ($failure.status -eq 'FAIL' -and $failure.files.Count -eq 0) 'Original interruption scope changed'
$actualACL = Get-Acl -LiteralPath $root
Require ($actualACL.AreAccessRulesProtected -and $actualACL.Sddl -eq $failure.privateACL) 'Private destination ACL changed'
$freeBefore = (Get-PSDrive C).Free
Require ($freeBefore -ge ((772912909 - 213543961) + 2GB)) 'Remaining backup plus Windows live floor does not fit'
Require (-not (Test-Path -LiteralPath (Join-Path $root 'receipt-continuation1.json'))) 'Continuation already completed'
[System.IO.File]::WriteAllBytes((Join-Path $root 'windows-preservation-continuation1.ps1'), [System.IO.File]::ReadAllBytes($PSCommandPath))
$result = [ordered]@{schema='pinkha-seven-original-archives-private-windows-backup-v1';status='FAIL';startedAt=[DateTime]::UtcNow.ToString('o');computer=$env:COMPUTERNAME;owner=$env:USERNAME;destination=$root;privateACL=$actualACL.Sddl;allowedSIDs=$failure.allowedSIDs;freeBytesBefore=$freeBefore;macControllerSHA256=$controllerSHA;sourceManifestSHA256=$manifestSHA;sourceObservationSHA256=$observationSHA;sourceFilesRemoved=0;newMacArchiveBytes=0;unpackedFiles=0;files=@();error=$null;controllerObservedSHA256=(SHA $PSCommandPath);originalFailure=[ordered]@{path=$originalFailurePath;sha256=(SHA $originalFailurePath)};firstBinaryTransferRepeated=$false}
try {
    $manifestPath = Join-Path $root 'source-manifest-before.json'
    Require ((SHA $manifestPath) -eq $manifestSHA) 'Original manifest bytes differ'
    $observationPath = Join-Path $root 'source-observation.json'
    Require ((SHA $observationPath) -eq $observationSHA) 'Original observation bytes differ'
    $controllerPath = Join-Path $root 'original-mac-preservation-controller.py'
    Require ((SHA $controllerPath) -eq $controllerSHA) 'Original Mac controller bytes differ'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $observation = Get-Content -LiteralPath $observationPath -Raw | ConvertFrom-Json
    Require ($manifest.files.Count -eq 7 -and $observation.status -eq 'PASS_ORIGINAL_ARCHIVE_OBSERVATION_NOT_RETIRED') 'Original qualified seven-file manifest required'
    Require ($observation.currentControllerReferences.matches.Count -eq 0) 'Current controller depends on archive path'
    $result.sourceManifest = [ordered]@{path=$manifestPath;sha256=(SHA $manifestPath);bytes=(Get-Item -LiteralPath $manifestPath).Length}
    $result.sourceObservation = [ordered]@{path=$observationPath;sha256=(SHA $observationPath);bytes=(Get-Item -LiteralPath $observationPath).Length}
    for($index=0;$index -lt 7;$index++) {
        $row = $manifest.files[$index]
        $target = Join-Path $root $names[$index]
        if($index -eq 0) {
            Require (Test-Path -LiteralPath $target -PathType Leaf) 'Original completed first binary transfer missing'
            $stderrPath = Join-Path $root 'archive-1.stderr.txt'
            $transfer = [ordered]@{originalTransferReused=$true;stderr=[System.IO.File]::ReadAllText($stderrPath);stderrPath=$stderrPath;stderrSHA256=(SHA $stderrPath)}
        } else {
            $command = '/opt/homebrew/bin/python3.12 -B ' + $macController + ' --stream-index ' + $index + ' --manifest-sha256 ' + $manifestSHA
            $transfer = Copy-SSH-Binary $command $target ('archive-' + ($index+1))
        }
        $sourceResult = $transfer.stderr.Trim() | ConvertFrom-Json
        Require ($sourceResult.status -eq 'PASS_EXACT_STREAM_ORIGINAL_BYTES_AND_METADATA_UNCHANGED') 'Original source stream did not qualify'
        $actual = Get-Item -LiteralPath $target
        Require (($actual.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) 'Destination archive must not be reparse point'
        $destSHA = SHA $target
        Require ($actual.Length -eq $row.bytes -and $destSHA -eq $row.sha256) 'Destination byte/hash verification failed'
        $streamPath = Join-Path $root ('source-stream-' + ($index+1) + '.json')
        $streamTransfer = Copy-SSH-Binary ('/bin/cat ' + $macAudit + '/stream-' + ($index+1) + '.json') $streamPath ('stream-receipt-' + ($index+1))
        Require ((SHA $streamPath) -eq $sourceResult.receipt.sha256) 'Original stream receipt bytes differ'
        $originalStream = Get-Content -LiteralPath $streamPath -Raw | ConvertFrom-Json
        Require ($originalStream.controllerSHA256 -eq $controllerSHA -and $originalStream.manifestSHA256 -eq $manifestSHA -and $originalStream.sourceAfter.sha256 -eq $row.sha256 -and $originalStream.sourceAfter.inode -eq $row.inode -and $originalStream.sourceAfter.mode -eq $row.mode) 'Source-after binding differs'
        $entry = [ordered]@{index=$index;originalPath=$row.path;destinationPath=$target;bytes=$actual.Length;sha256=$destSHA;originalManifestIndex=$index;destinationACL=(Get-Acl -LiteralPath $target).Sddl;sourceStreamReceipt=[ordered]@{path=$streamPath;sha256=(SHA $streamPath);originalMacPath=$sourceResult.receipt.path;originalMacSHA256=$sourceResult.receipt.sha256};transfer=$transfer}
        $result.files += $entry
        [void](Write-JSON (Join-Path $root ('verified-' + ($index+1) + '.json')) $entry)
    }
    Require ($result.files.Count -eq 7) 'Incomplete archive copy set'
    $result.status = 'PASS_SEVEN_ORIGINAL_ARCHIVES_OFFHOST_HASH_METADATA_PROTECTED_NOT_RETIRED'
} catch {
    $result.error = $_.Exception.Message
} finally {
    $result.freeBytesAfter = (Get-PSDrive C).Free
    $result.finishedAt = [DateTime]::UtcNow.ToString('o')
    $receipt = Write-JSON (Join-Path $root 'receipt-continuation1.json') $result
    [ordered]@{status=$result.status;receipt=$receipt;fileCount=$result.files.Count;freeBytesBefore=$result.freeBytesBefore;freeBytesAfter=$result.freeBytesAfter;error=$result.error} | ConvertTo-Json -Depth 10
}
if($result.status -notlike 'PASS_*') { exit 1 }

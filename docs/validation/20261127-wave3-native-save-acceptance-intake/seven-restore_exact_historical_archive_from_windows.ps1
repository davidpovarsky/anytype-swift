param([Parameter(Mandatory=$true)][ValidateRange(0,6)][int]$Index, [switch]$Execute)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not $Execute){throw 'Restoration is dormant; root must explicitly request one original archive restoration.'}
$root='C:\Users\DAVID\Code\anytype-wave3-mac-artifacts-20261127\historical-evidence-seven-20261127-01'
$receipt=Join-Path $root 'receipt-continuation1.json'
$manifest=Join-Path $root 'source-manifest-before.json'
function Sha([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
if((Sha $receipt) -ne 'dea06e4824fa836332257cf5c0530b1528409f49a25609377990eb60c8e35186' -or (Sha $manifest) -ne 'd6575b864418cd7b8fdde83776a0fdb4138c70ffb252f81f855fa96c7d7e8c86'){throw 'Original backup provenance changed'}
$backup=Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json
$row=$backup.files[$Index]
$acl=Get-Acl -LiteralPath $root
if(-not $acl.AreAccessRulesProtected -or $acl.Sddl -ne $backup.privateACL){throw 'Private backup ACL changed'}
if((Sha $row.destinationPath) -ne $row.sha256 -or (Get-Item -LiteralPath $row.destinationPath).Length -ne $row.bytes){throw 'Exact original archive bytes changed'}
# Before invoking this dormant procedure, root uploads the reviewed helper bytes through
# the existing SentinelX file-upload route to this exact path; no credential copy is used.
$helper='/Users/m1/sentinelx/uploads/pinkha-wave3-restore-exact-historical-archive.py'
$helperSHA='9bd85733b1ddef1dda7cb6cd8a81728b57e6f3dd7c920502170fb7429a4b5aff'
$info=New-Object Diagnostics.ProcessStartInfo
$info.FileName=(Get-Command ssh).Source
$info.Arguments='-o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 scaleway-mac "/opt/homebrew/bin/python3.12 -B '+$helper+' --index '+$Index+' --controller-sha256 '+$helperSHA+'"'
$info.UseShellExecute=$false
$info.RedirectStandardInput=$true
$info.RedirectStandardOutput=$true
$info.RedirectStandardError=$true
$p=New-Object Diagnostics.Process
$p.StartInfo=$info
$started=$false
$archiveStream=[IO.File]::OpenRead($row.destinationPath)
try{
    $started=$p.Start();if(-not $started){throw 'Pinned SSH failed to start'}
    $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
    $copy=$archiveStream.CopyToAsync($p.StandardInput.BaseStream)
    if(-not $copy.Wait(300000)){$p.Kill();throw 'Owned restoration stream exceeded 300 seconds'}
    [void]$copy.GetAwaiter().GetResult();$p.StandardInput.Close()
    if(-not $p.WaitForExit(60000)){$p.Kill();throw 'Owned restoration SSH did not finish'}
    $output=$stdout.GetAwaiter().GetResult();$errors=$stderr.GetAwaiter().GetResult()
    $proof=[ordered]@{originalBackupSHA256=(Sha $receipt);index=$Index;originalMacPath=$row.originalPath;archiveSHA256=$row.sha256;exitCode=$p.ExitCode;stdout=$output;stderr=$errors;finishedAt=[DateTime]::UtcNow.ToString('o')}
    $out=Join-Path $root ('restore-'+$Index+'-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')
    [IO.File]::WriteAllText($out,(($proof|ConvertTo-Json -Depth 20)+"`n"),(New-Object Text.UTF8Encoding($false)))
    if($p.ExitCode -ne 0){throw ('Original restoration failed; preserved result '+$out)}
    $r=$output|ConvertFrom-Json
    if($r.status -ne 'PASS_EXACT_ARCHIVE_BYTES_AND_RESTORABLE_METADATA' -or $r.restored.sha256 -ne $row.sha256){throw 'Original restored archive did not qualify'}
    [ordered]@{status=$r.status;receipt=$out;sha256=(Sha $out);originalMacPath=$row.originalPath}|ConvertTo-Json
}finally{
    $archiveStream.Dispose()
    if($started -and -not $p.HasExited){$p.Kill();$p.WaitForExit()}
    $p.Dispose()
}

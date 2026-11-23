$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$evidenceParent='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\sdk-ui-page-dispatch-e4edea19ce-20261123'
$evidenceDirectory=Join-Path $evidenceParent 'ci-observer-sdk-attempt1-root-window1'
$expectedBytes=[long]10000000
$who=[System.Security.Principal.WindowsIdentity]::GetCurrent()
if($who.User.Value -ne 'S-1-5-21-2914620446-786530585-2031499938-1001'){throw 'Unexpected artifact owner identity'}
$allowedSids=@('S-1-5-18','S-1-5-32-544',$who.User.Value)
function Assert-PrivateAcl([string]$path,[bool]$isDirectory){
 $item=Get-Item -LiteralPath $path -Force
 if($item.PSIsContainer -ne $isDirectory -or (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)){throw 'Unexpected path type/reparse point'}
 $acl=Get-Acl -LiteralPath $path
 $owner=([System.Security.Principal.NTAccount]$acl.Owner).Translate([System.Security.Principal.SecurityIdentifier]).Value
 if($owner -ne $who.User.Value -or -not $acl.AreAccessRulesProtected){throw 'Unexpected owner or inherited ACL'}
 $entries=@($acl.Access)
 if($entries.Count -ne 3){throw 'Unexpected ACL cardinality'}
 $observed=@()
 foreach($entry in $entries){
  $sid=$entry.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
  if($sid -notin $allowedSids -or $entry.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or $entry.IsInherited -or (($entry.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -ne [System.Security.AccessControl.FileSystemRights]::FullControl)){throw 'Unexpected access rule'}
  $observed+=$sid
 }
 if(@($observed | Select-Object -Unique).Count -ne 3){throw 'Repeated ACL identity'}
 return [ordered]@{owner=$owner;sddl=$acl.Sddl;inheritanceDisabled=$true;reparse=$false}
}
$parentAcl=Assert-PrivateAcl $evidenceParent $true
if(Test-Path -LiteralPath $evidenceDirectory){throw 'Destination already exists; no overwrite'}
if(([System.IO.DriveInfo]::new('C:\')).AvailableFreeSpace -lt ($expectedBytes+2500000000)){throw 'Destination reserve unavailable'}
[System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
$directoryAcl=New-Object System.Security.AccessControl.DirectorySecurity
$directoryAcl.SetAccessRuleProtection($true,$false)
$directoryAcl.SetOwner($who.User)
foreach($sid in $allowedSids){
 $identity=New-Object System.Security.Principal.SecurityIdentifier($sid)
 $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($identity,[System.Security.AccessControl.FileSystemRights]::FullControl,([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit),[System.Security.AccessControl.PropagationFlags]::None,[System.Security.AccessControl.AccessControlType]::Allow)
 $directoryAcl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $evidenceDirectory -AclObject $directoryAcl
$directoryProof=Assert-PrivateAcl $evidenceDirectory $true

$utf8=New-Object System.Text.UTF8Encoding($false)
function Save-Text([string]$name,[string]$body){
 $path=Join-Path $evidenceDirectory $name
 $bytes=$utf8.GetBytes($body)
 $f=New-Object System.IO.FileStream($path,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
 try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
 return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Save-Json([string]$name,$value){return Save-Text $name (($value | ConvertTo-Json -Depth 15 -Compress)+[Environment]::NewLine)}
function Capture-Gh([string]$name,[string]$arguments){
 $si=New-Object System.Diagnostics.ProcessStartInfo
 $si.FileName='gh.exe';$si.Arguments=$arguments
 $si.UseShellExecute=$false;$si.CreateNoWindow=$true
 $si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
 $si.StandardOutputEncoding=$utf8;$si.StandardErrorEncoding=$utf8
 $p=New-Object System.Diagnostics.Process;$p.StartInfo=$si
 $at=[DateTime]::UtcNow.ToString('o')
 if(-not $p.Start()){throw 'Could not start owned gh process'}
 $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
 if(-not $p.WaitForExit(60000)){
  $p.Kill();$p.WaitForExit(5000) | Out-Null
  Save-Json ($name+'.timeout.json') ([ordered]@{status='OWNED_GH_TIMEOUT_NO_AUTOMATIC_REDISPATCH';pid=$p.Id;arguments=$arguments;started_at=$at}) | Out-Null
  throw 'Owned gh process timed out; query existing run identity before any follow-up'
 }
 $out=$stdout.Result;$err=$stderr.Result
 $oh=Save-Text ($name+'.stdout.txt') $out
 $eh=Save-Text ($name+'.stderr.txt') $err
 Save-Json ($name+'.command.json') ([ordered]@{exe='gh.exe';arguments=$arguments;pid=$p.Id;started_at=$at;finished_at=[DateTime]::UtcNow.ToString('o');exit_code=$p.ExitCode;stdout_sha256=$oh;stderr_sha256=$eh;representation='CLI text captured using UTF8 TextReader; not claimed as byte-exact HTTP transport'}) | Out-Null
 if($p.ExitCode -ne 0){throw ('gh command failed: '+$name+'; originals preserved; no automatic retry')}
 return $out
}
$repo='davidpovarsky/anytype-swift'
$runId=45174279596
$attempt=1
$head='e4edea19ce716280f4087f8b9571ad2b4f6f94c5'
$route='sdk06-original-native-continuation'
$request=Join-Path $evidenceParent 'dispatch-summary.json'
if((Get-FileHash -LiteralPath $request).Hash.ToLowerInvariant() -ne '91c35b05a68e6b63c6c20f68f26d9044f4b041e43c1f1e575dd2fbf9af3388d4'){throw 'Exact authorized three-route dispatch receipt differs'}
function Validate-Run($run){
 if(-not $run.display_title.StartsWith('Pinkha '+$route+' ')){throw 'Exact route title differs'}
 if($run.id -ne $runId -or $run.run_attempt -ne $attempt -or $run.head_sha -ne $head -or $run.head_branch -ne 'codex/chatgpt-wave15-shared-20261121' -or $run.path -ne '.github/workflows/torah-inspector-ipados27.yml'){throw 'Exact current selected route attempt identity differs'}
}
$initialText=Capture-Gh 'initial-run-api' ('api repos/'+$repo+'/actions/runs/'+$runId+'/attempts/'+$attempt)
$initial=$initialText | ConvertFrom-Json
Validate-Run $initial
Save-Json 'observer-intent.json' ([ordered]@{protocol='sdk-ui-page-attempt1-bounded-observer-v1';route=$route;run_id=$runId;attempt=$attempt;head=$head;supervisor_pid=$PID;watch_window_seconds=1500;watch_interval_seconds=45;ci_mutations=0;artifact_downloads=0;initial_status=$initial.status;initial_conclusion=$initial.conclusion;new_child_acl=$directoryProof;parent_acl=$parentAcl}) | Out-Null
$watch=$null
$stdoutStream=$null
$stderrStream=$null
$watchExit=$null
$stoppedForBound=$false
$checkpoints=0
$observedRun=$initial
if($initial.status -ne 'completed'){
 $si=New-Object System.Diagnostics.ProcessStartInfo
 $si.FileName='gh.exe';$si.Arguments='run watch 45174279596 --repo '+$repo+' --exit-status --interval 45'
 $si.UseShellExecute=$false;$si.CreateNoWindow=$true;$si.RedirectStandardOutput=$true;$si.RedirectStandardError=$true
 $watch=New-Object System.Diagnostics.Process;$watch.StartInfo=$si
 $stdoutStream=New-Object System.IO.FileStream((Join-Path $evidenceDirectory 'watch.stdout.log'),[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
 $stderrStream=New-Object System.IO.FileStream((Join-Path $evidenceDirectory 'watch.stderr.log'),[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
 try{
  if(-not $watch.Start()){throw 'Owned Release watch failed to start'}
  $watchStarted=$watch.StartTime.ToUniversalTime().ToString('o')
  Save-Json 'watch-start.json' ([ordered]@{pid=$watch.Id;started_at=$watchStarted;arguments=$si.Arguments;run_id=$runId;attempt=$attempt;head=$head;supervisor_pid=$PID}) | Out-Null
  $outTask=$watch.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
  $errTask=$watch.StandardError.BaseStream.CopyToAsync($stderrStream)
  $clock=[System.Diagnostics.Stopwatch]::StartNew()
  while(-not $watch.HasExited){
   if($clock.Elapsed.TotalSeconds -ge 1500){$stoppedForBound=$true;break}
   $watch.WaitForExit(45000) | Out-Null
   $checkpoints++
   $progress=[ordered]@{run_id=$runId;attempt=$attempt;source_sha=$head;watch_pid=$watch.Id;watch_start=$watchStarted;watch_has_exited=$watch.HasExited;elapsed_seconds=$clock.Elapsed.TotalSeconds;checkpoint=$checkpoints;supervisor_pid=$PID;recorded_at=[DateTime]::UtcNow.ToString('o');api_queries_added_by_checkpoint=0}
   $progressText=($progress | ConvertTo-Json -Compress)+[Environment]::NewLine
   Save-Text ('checkpoint-'+$checkpoints.ToString('D3')+'.json') $progressText | Out-Null
   [System.IO.File]::WriteAllText((Join-Path $evidenceDirectory 'latest.json'),$progressText,$utf8)
   if($stdoutStream.Length+$stderrStream.Length -gt 10000000){$stoppedForBound=$true;break}
  }
  if(-not $watch.HasExited){$watch.Kill();if(-not $watch.WaitForExit(10000)){throw 'Owned watch did not exit after bounded stop'}}
  if(-not $outTask.Wait(10000) -or -not $errTask.Wait(10000)){throw 'Owned watch output did not drain'}
  $watchExit=$watch.ExitCode
 }finally{
  if($null -ne $watch -and -not $watch.HasExited){$watch.Kill();$watch.WaitForExit(10000) | Out-Null}
  if($null -ne $stdoutStream){$stdoutStream.Flush($true);$stdoutStream.Dispose()}
  if($null -ne $stderrStream){$stderrStream.Flush($true);$stderrStream.Dispose()}
 }
 $finalText=Capture-Gh 'final-run-api' ('api repos/'+$repo+'/actions/runs/'+$runId+'/attempts/'+$attempt)
 $observedRun=$finalText | ConvertFrom-Json
 Validate-Run $observedRun
}
$selected=@()
$artifactCount=$null
if($observedRun.status -eq 'completed'){
 $jobsText=Capture-Gh 'terminal-jobs-index' ('api "repos/'+$repo+'/actions/runs/'+$runId+'/attempts/'+$attempt+'/jobs?per_page=100"')
 $jobs=$jobsText | ConvertFrom-Json
 if(@($jobs.jobs).Count -ne $jobs.total_count -or $jobs.total_count -gt 100){throw 'Unexpected incomplete terminal job index'}
 $selected=@($jobs.jobs | Where-Object {$_.conclusion -ne 'skipped'} | Select-Object id,name,status,conclusion,runner_id,runner_name,started_at,completed_at,steps)
 $artifactsText=Capture-Gh 'terminal-artifacts-index' ('api "repos/'+$repo+'/actions/runs/'+$runId+'/artifacts?per_page=100"')
 $artifacts=$artifactsText | ConvertFrom-Json
 if(@($artifacts.artifacts).Count -ne $artifacts.total_count -or $artifacts.total_count -gt 100){throw 'Unexpected incomplete artifact index'}
 $artifactCount=$artifacts.total_count
}
$result=[ordered]@{protocol='sdk-ui-page-attempt1-bounded-observer-v1';route=$route;status='OBSERVATION_COMPLETE';run_id=$runId;attempt=$attempt;source_sha=$head;run_status=$observedRun.status;run_conclusion=$observedRun.conclusion;run_updated_at=$observedRun.updated_at;initial_was_terminal=($initial.status -eq 'completed');watch_exit_code=$watchExit;watch_stopped_for_bound=$stoppedForBound;owned_watch_remaining=($null -ne $watch -and -not $watch.HasExited);selected_jobs=$selected;artifact_count=$artifactCount;directory=$evidenceDirectory;ci_mutations=0;artifact_downloads=0;finished_at=[DateTime]::UtcNow.ToString('o')}
$receipt=Save-Json 'observer-result.json' $result
$result.receipt_sha256=$receipt
$result | ConvertTo-Json -Depth 15 -Compress

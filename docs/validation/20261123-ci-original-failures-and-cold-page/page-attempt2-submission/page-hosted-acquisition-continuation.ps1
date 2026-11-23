$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$evidenceParent='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\page-release-dispatch-c0c1f851f8-20261123'
$evidenceDirectory=Join-Path $evidenceParent 'page-hosted-acquisition-continuation-20261123'
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
$head='c0c1f851f80322c9f532e86505047498dfaf1adf'
$observer=Join-Path $evidenceParent 'ci-observer-window1'
$causalPath=Join-Path $observer '45162736256-causal-query-result.json'
$jobsPath=Join-Path $observer '45162736256-terminal-jobs-index.stdout.json'
$runPath=Join-Path $observer '45162736256-initial-run-api.stdout.json'
$causalSha=(Get-FileHash -LiteralPath $causalPath -Algorithm SHA256).Hash.ToLowerInvariant()
$jobsSha=(Get-FileHash -LiteralPath $jobsPath -Algorithm SHA256).Hash.ToLowerInvariant()
$runSha=(Get-FileHash -LiteralPath $runPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($causalSha -ne '1b5a40b2ff8a668f5f061e7110a6b720388aa14f34c6724663959637eb16cb5a' -or $jobsSha -ne '09f9902a4995b795148af287f0da2d191f68af3ce70347ff3b934571a9bcf6f3' -or $runSha -ne 'e5eb9c925560a65a5618d62bcbb1c156f3c9a293e39321ff3248a98f31f3a827'){throw 'Retained original source/causal evidence differs'}
$causal=Get-Content -Raw -LiteralPath $causalPath | ConvertFrom-Json
$jobs=Get-Content -Raw -LiteralPath $jobsPath | ConvertFrom-Json
$run=Get-Content -Raw -LiteralPath $runPath | ConvertFrom-Json
if($run.id -ne 45162736256 -or $run.run_attempt -ne 1 -or $run.head_sha -ne $head -or $run.status -ne 'completed' -or $run.conclusion -ne 'failure'){throw 'Original run was not the exact failed attempt'}
$selected=@($jobs.jobs | Where-Object {$_.id -eq 137651963319})
if($selected.Count -ne 1){throw 'Exact selected original job absent'}
$j=$selected[0]
if($j.name -ne 'semantic-page-apple-mounted / original-products-mounted' -or $j.status -ne 'completed' -or $j.conclusion -ne 'cancelled' -or $j.runner_id -ne 0 -or @($j.steps).Count -ne 0 -or $j.check_run_url -ne 'https://api.github.com/repos/davidpovarsky/anytype-swift/check-runs/137651963319'){throw 'Original selected-job failure boundary changed'}
if($causal.status -ne 'PASS_ORIGINAL_CHECK_RUN_AND_ANNOTATIONS_CAPTURED' -or $causal.run_attempt -ne 1 -or $causal.head -ne $head -or $causal.job_id -ne $j.id -or -not $causal.annotation_index_complete -or @($causal.annotations).Count -ne 1 -or $causal.annotations[0].message -ne 'The job was not acquired by Runner of type hosted even after multiple attempts'){throw 'Exact original acquisition failure not established'}
$login=(Capture-Gh 'identity' 'api user --jq .login').Trim()
if($login -ne 'davidpovarsky'){throw 'Unexpected GitHub identity'}
$intent=[ordered]@{protocol='page-hosted-acquisition-continuation-v1';status='EXACT_JOB_RERUN_INTENT';repository=$repo;run_id=45162736256;original_attempt=1;expected_next_attempt=2;source_sha=$head;selected_job_database_id=$j.id;original_recorded_steps=0;original_runner_id=0;original_product_tests=0;reason='HOSTED_RUNNER_NOT_ACQUIRED';causal_receipt_sha256=$causalSha;jobs_sha256=$jobsSha;run_sha256=$runSha;new_source_changes=0;passed_test_replays=0;allowed_submissions=1;automatic_retry_allowed=$false;parent_acl=$parentAcl;new_child_acl=$directoryProof;created_at=[DateTime]::UtcNow.ToString('o')}
$intentSha=Save-Json 'intent.json' $intent
$arguments='run rerun 45162736256 --job 137651963319 --repo '+$repo
$output=Capture-Gh 'exact-job-rerun' $arguments
$result=[ordered]@{protocol='page-hosted-acquisition-continuation-v1';status='EXACT_JOB_CONTINUATION_REQUEST_ACCEPTED';run_id=45162736256;original_attempt=1;expected_next_attempt=2;source_sha=$head;job_database_id=137651963319;submission_count=1;intent_sha256=$intentSha;finished_at=[DateTime]::UtcNow.ToString('o');product_result='NOT_OBSERVED';observer_owner='acceptance_map';original_attempt_evidence_unchanged=$true;directory=$evidenceDirectory}
$receiptSha=Save-Json 'submission-result.json' $result
$result.receipt_sha256=$receiptSha
$result | ConvertTo-Json -Depth 10 -Compress

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$evidenceParent='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\page-release-dispatch-c0c1f851f8-20261123'
$evidenceDirectory=Join-Path $evidenceParent 'release-owned-boot-continuation-attempt2-20261123'
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
$runPath=Join-Path $observer '45163515182-final-run-api.stdout.json'
$jobsPath=Join-Path $observer '45163515182-terminal-jobs-index.stdout.json'
$runSha=(Get-FileHash -LiteralPath $runPath).Hash.ToLowerInvariant()
$jobsSha=(Get-FileHash -LiteralPath $jobsPath).Hash.ToLowerInvariant()
if($runSha -ne '3d85b48139f96dd384738d77d1d9e12d33a8421eb6a14baacd5b32355190eb62' -or $jobsSha -ne '87cac738a4752cfe6499c896d761b03f0ac13434fee5f1a7835ab7f7d238a05c'){throw 'Original run/job evidence changed'}
$run=Get-Content -Raw -LiteralPath $runPath | ConvertFrom-Json
$jobs=Get-Content -Raw -LiteralPath $jobsPath | ConvertFrom-Json
$selected=@($jobs.jobs | Where-Object {$_.id -eq 137654566730})
if($selected.Count -ne 1){throw 'Exact failed Release job missing'}
$j=$selected[0]
if($run.id -ne 45163515182 -or $run.run_attempt -ne 1 -or $run.head_sha -ne $head -or $run.conclusion -ne 'failure' -or $run.status -ne 'completed' -or $j.conclusion -ne 'failure' -or $j.name -ne 'coherent-original-products / original-products-release'){throw 'Original Release identity differs'}
$failed=@($j.steps | Where-Object {$_.conclusion -eq 'failure'})
if($failed.Count -ne 1 -or $failed[0].number -ne 6 -or $failed[0].name -ne 'Restore original d254 Products and execute only unrun Release scopes'){throw 'Original failed step changed'}
$auditScript=@'
import pathlib,json,hashlib
p=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-original-result-20261123/root-original-outcome-review.json")
raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="964e35383c7f3072e3dc4bd2f369730a5d8f48815c28f0542f5b82a3ed54fc7b"
v=json.loads(raw)
assert v["status"]=="PASS_ORIGINAL_FAILURE_BOUNDARY_VERIFIED" and v["current_product_methods_executed"]==0 and v["outer_cleanup_status"]=="PASS"
assert v["original_failure"]["phase"]=="OWNED_SIMULATOR_READINESS" and v["original_failure"]["timeout_seconds"]==180 and v["owned_kernel_cleanup_groups"]==5 and v["owned_devices_delete_exit0"]==3
print(json.dumps({"sha256":hashlib.sha256(raw).hexdigest(),"product_methods":0,"failure_phase":v["original_failure"]["phase"],"underlying_boot_cause_established":False,"cleanup":v["outer_cleanup_status"]}))
'@
$auditRaw=($auditScript | ssh -T torah-dev python3 -B -u -) -join [Environment]::NewLine
if($LASTEXITCODE -ne 0){throw 'Independent original Oracle audit did not bind'}
$audit=$auditRaw | ConvertFrom-Json
$auditCopySha=Save-Text 'oracle-original-audit-admission.json' ($auditRaw+[Environment]::NewLine)
$login=(Capture-Gh 'identity' 'api user --jq .login').Trim()
if($login -ne 'davidpovarsky'){throw 'Unexpected GitHub identity'}
$intent=[ordered]@{protocol='release-owned-boot-fresh-host-continuation-v1';status='EXACT_JOB_CONTINUATION_INTENT';repository=$repo;run_id=45163515182;original_attempt=1;expected_next_attempt=2;source_sha=$head;original_app_sha='d254a4a1ccd9288f585ff9374088cbaf965b36b4';job_database_id=137654566730;original_product_methods_executed=0;original_failure='OWNED_SIMULATOR_READINESS_BOOTSTATUS_TIMEOUT';original_timeout_seconds=180;new_timeout_seconds=180;underlying_boot_cause_established=$false;experiment='One fresh hosted runner with identical reviewed code, original Products, assertions and budgets; runner/step debugging enabled';code_changes=0;old_passed_methods_replayed=0;allowed_submissions=1;automatic_retry_allowed=$false;original_root_audit_sha256=$audit.sha256;audit_admission_copy_sha256=$auditCopySha;original_run_sha256=$runSha;original_jobs_sha256=$jobsSha;created_at=[DateTime]::UtcNow.ToString('o');parent_acl=$parentAcl;new_child_acl=$directoryProof}
$intentSha=Save-Json 'intent.json' $intent
$output=Capture-Gh 'exact-job-rerun' ('run rerun 45163515182 --job 137654566730 --debug --repo '+$repo)
$result=[ordered]@{protocol='release-owned-boot-fresh-host-continuation-v1';status='EXACT_JOB_CONTINUATION_REQUEST_ACCEPTED';run_id=45163515182;original_attempt=1;expected_next_attempt=2;source_sha=$head;job_database_id=137654566730;submission_count=1;intent_sha256=$intentSha;runner_debug_requested=$true;finished_at=[DateTime]::UtcNow.ToString('o');product_result='NOT_OBSERVED';directory=$evidenceDirectory;automatic_retry_allowed=$false}
$receiptSha=Save-Json 'submission-result.json' $result
$result.receipt_sha256=$receiptSha
$result | ConvertTo-Json -Depth 10 -Compress

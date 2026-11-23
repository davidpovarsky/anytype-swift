$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$evidenceParent='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence'
$evidenceDirectory=Join-Path $evidenceParent 'sdk-ui-page-dispatch-e4edea19ce-20261123'
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
$head='e4edea19ce716280f4087f8b9571ad2b4f6f94c5'
$branch='codex/chatgpt-wave15-shared-20261121'
$gateSha='bb83fb04b5b14ea48482e2c44e4ab98f15994d8f694487719af097a1cbe473e4'
$routes=@('sdk06-original-native-continuation','native-ui-transition-candidate','semantic-page-apple-mounted')
$login=(Capture-Gh 'identity' 'api user --jq .login').Trim()
if($login -ne 'davidpovarsky'){throw 'Unexpected GitHub identity'}
$remote=(Capture-Gh 'published-ref' ('api repos/'+$repo+'/git/ref/heads/'+$branch)) | ConvertFrom-Json
if($remote.object.sha -ne $head){throw 'Published branch changed; no dispatch'}
$endpoint='repos/'+$repo+'/actions/workflows/torah-inspector-ipados27.yml/runs?branch=codex%2Fchatgpt-wave15-shared-20261121&event=workflow_dispatch&per_page=10'
$initial=(Capture-Gh 'runs-before' ('api "'+$endpoint+'"')) | ConvertFrom-Json
$existing=@($initial.workflow_runs | Where-Object {$_.head_sha -eq $head})
if($existing.Count -ne 0){throw 'This newly published source already has runs; inspect identities before any dispatch'}
Save-Json 'all-routes-intent.json' ([ordered]@{status='THREE_DISTINCT_ROUTES_ONCE';at=[DateTime]::UtcNow.ToString('o');routes=$routes;head=$head;branch=$branch;repository=$repo;source_gate_sha256=$gateSha;source_and_Git_work='ORACLE';private_directory=$directoryProof;prior_matching_head_runs=0;automatic_redispatch=$false;release_route='NOT_DISPATCHED_PENDING_ORDERING_REPAIR'}) | Out-Null
$submissions=@()
foreach($route in $routes){
 Save-Json ($route+'-intent.json') ([ordered]@{status='ONE_TIME_DISPATCH_INTENT';at=[DateTime]::UtcNow.ToString('o');route=$route;head=$head;source_gate_sha256=$gateSha;automatic_retry=$false}) | Out-Null
 $text=Capture-Gh ($route+'-dispatch') ('workflow run torah-inspector-ipados27.yml --repo '+$repo+' --ref '+$branch+' -f route='+$route)
 $accepted=[ordered]@{route=$route;status='REQUEST_ACCEPTED_IDENTITY_PENDING';source=$head;new_dispatch_calls=1;at=[DateTime]::UtcNow.ToString('o')}
 Save-Json ($route+'-submission.json') $accepted | Out-Null
 $submissions+=$accepted
}
Save-Json 'dispatch-submissions.json' ([ordered]@{status='ALL_THREE_DISTINCT_REQUESTS_ACCEPTED';source=$head;submissions=$submissions;new_dispatch_calls=3;duplicate_dispatches=0}) | Out-Null
$after=(Capture-Gh 'runs-after-three-submissions' ('api "'+$endpoint+'"')) | ConvertFrom-Json
$records=@()
foreach($route in $routes){
 $matches=@($after.workflow_runs | Where-Object {$_.head_sha -eq $head -and $_.display_title.StartsWith('Pinkha '+$route+' ')})
 if($matches.Count -gt 1){throw 'Ambiguous route identities; never redispatch'}
 if($matches.Count -eq 0){
  $record=[ordered]@{status='DISPATCH_SENT_IDENTITY_PENDING_DO_NOT_REDISPATCH';route=$route;source=$head;new_dispatch_calls=1;matches=0}
 }else{
  $run=$matches[0]
  if($run.head_sha -ne $head -or $run.head_branch -ne $branch -or $run.run_attempt -ne 1 -or $run.event -ne 'workflow_dispatch'){throw 'Actual run identity mismatch'}
  $record=[ordered]@{status='EXACT_SOURCE_ROUTE_IDENTIFIED';at=[DateTime]::UtcNow.ToString('o');route=$route;run_id=$run.id;url=$run.html_url;source=$run.head_sha;branch=$run.head_branch;attempt=$run.run_attempt;event=$run.event;workflow_status=$run.status;conclusion=$run.conclusion;created_at=$run.created_at;new_dispatch_calls=1;source_gate_sha256=$gateSha}
 }
 Save-Json ($route+'-receipt.json') $record | Out-Null
 $records+=$record
}
$summary=[ordered]@{status='THREE_DISTINCT_REQUESTS_ACCEPTED';source=$head;records=$records;receipts_directory=$evidenceDirectory;source_gate_sha256=$gateSha;duplicate_dispatches=0;release_dispatched=$false;identified_routes=@($records | Where-Object {$_.status -eq 'EXACT_SOURCE_ROUTE_IDENTIFIED'}).Count}
$summarySha=Save-Json 'dispatch-summary.json' $summary
[ordered]@{status=$summary.status;source=$head;records=$records;receipts_directory=$evidenceDirectory;summary_sha256=$summarySha;duplicate_dispatches=0;release_dispatched=$false;identified_routes=$summary.identified_routes} | ConvertTo-Json -Depth 12 -Compress

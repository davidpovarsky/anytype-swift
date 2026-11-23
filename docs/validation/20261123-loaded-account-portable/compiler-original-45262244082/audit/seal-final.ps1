$ErrorActionPreference='Stop'
$base='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\loaded-account-compiler-original-45262244082-1\audit1'
$owner='S-1-5-21-2914620446-786530585-2031499938-1001'
$sids=@($owner,'S-1-5-18','S-1-5-32-544')
$parent=(Get-Acl -LiteralPath $base).Sddl
function Save([string]$path,$value){
$b=[Text.Encoding]::UTF8.GetBytes(($value|ConvertTo-Json -Depth 16)+[char]10)
$f=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$f.Write($b,0,$b.Length);$f.Flush($true)}finally{$f.Dispose()}
}
function Meta($p){
$i=Get-Item -LiteralPath $p -Force
if($i.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'reparse'}
$a=Get-Acl -LiteralPath $p
$v=[ordered]@{relative=$i.FullName.Substring($base.Length+1).Replace('\','/');directory=$i.PSIsContainer;owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;sddl=$a.Sddl;protected=$a.AreAccessRulesProtected;attributes=[string][int]$i.Attributes;creation_ticks=[string]$i.CreationTimeUtc.Ticks;last_write_ticks=[string]$i.LastWriteTimeUtc.Ticks}
if(-not $i.PSIsContainer){$v.bytes=[string]$i.Length;$v.sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
return $v
}
function CloseAcl($p){
$i=Get-Item -LiteralPath $p -Force
if($i.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'reparse'}
if($i.PSIsContainer){$a=[Security.AccessControl.DirectorySecurity]::new();$inh=[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'}else{$a=[Security.AccessControl.FileSecurity]::new();$inh=[Security.AccessControl.InheritanceFlags]::None}
$a.SetOwner([Security.Principal.SecurityIdentifier]::new($owner));$a.SetAccessRuleProtection($true,$false)
foreach($s in $sids){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($s),[Security.AccessControl.FileSystemRights]::FullControl,$inh,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow))}
Set-Acl -LiteralPath $p -AclObject $a
if(-not $i.PSIsContainer){(Get-Item -LiteralPath $p).IsReadOnly=$true}
$q=Get-Acl -LiteralPath $p
$rr=@($q.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if($q.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $owner -or -not $q.AreAccessRulesProtected -or $rr.Count -ne 3 -or ((@($rr.IdentityReference.Value|Sort-Object)-join ',') -ne (@($sids|Sort-Object)-join ','))){throw 'final closed owner acl'}
foreach($r in $rr){if($r.IsInherited -or $r.AccessControlType -ne 'Allow' -or $r.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl -or $r.InheritanceFlags -ne $inh -or $r.PropagationFlags -ne 'None'){throw 'final rights'}}
}
$items=@(Get-ChildItem -LiteralPath $base -Recurse -Force)
if($items.Count -gt 180){throw 'bounded set'}
$before=@($items|ForEach-Object{Meta $_.FullName})
Save (Join-Path $base 'seal-final-before.json') ([ordered]@{schema='audit-owned-private-ACL-before';scope='New audit copies and operational receipts only; original ZIP, observer files and parent ACL excluded';items=$before;prior_seal_failures=@('attempt1 access SDDL comparison refusal; original before field not persisted','attempt2 fixed explicit SID comparison refused OWNER RIGHTS on Python-created copies');attempt2_transport_failure='WinError206 before remote invocation; source then staged without payload replay'})
foreach($i in @($items|Where-Object{$_.PSIsContainer})){CloseAcl $i.FullName}
foreach($i in @($items|Where-Object{-not $_.PSIsContainer})){CloseAcl $i.FullName}
CloseAcl (Join-Path $base 'seal-final-before.json')
$after=@()
foreach($v in $before){
$p=Join-Path $base $v.relative.Replace('/','\')
$q=Meta $p
if(-not $v.directory -and ($q.sha256 -ne $v.sha256 -or $q.bytes -ne $v.bytes)){throw 'audit byte changed'}
$after+=$q
}
if((Get-Acl -LiteralPath $base).Sddl -ne $parent){throw 'parent changed'}
$result=[ordered]@{schema='compiler-audit-owned-private-seal-final-v1';status='PASS';root=$base;parent_sddl_unchanged=$parent;new_audit_copy_count=@($after|Where-Object{-not $_.directory}).Count;new_directory_count=@($after|Where-Object{$_.directory}).Count;before=@{path='seal-final-before.json';sha256=(Get-FileHash -LiteralPath (Join-Path $base 'seal-final-before.json') -Algorithm SHA256).Hash.ToLower()};after=$after;all_payload_hashes_unchanged=$true;closed_explicit_three_sid_acl=$true;private_owner_sid=$owner;original_zip_untouched=$true;historical_producer_status='FAILED';historical_cleanup_status='FAILED';new_product_execution=0;new_container_execution=0;new_ci_queries=0}
$p=Join-Path $base 'audit-final-seal.json';Save $p $result;CloseAcl $p
[ordered]@{status='PASS';files=$result.new_audit_copy_count;directories=$result.new_directory_count;seal_path=$p;seal_bytes=(Get-Item -LiteralPath $p).Length;seal_sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower();source_cause_audit_sha256=(Get-FileHash -LiteralPath (Join-Path $base 'source-cause-audit.json') -Algorithm SHA256).Hash.ToLower()}|ConvertTo-Json -Compress

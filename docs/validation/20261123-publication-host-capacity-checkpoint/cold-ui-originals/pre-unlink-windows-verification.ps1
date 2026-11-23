$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$expectedFinal=@'
{"name":"final-seal.json","bytes":8740,"ntfs_file_id":"File ID is 0x000000000000000000140000001a20ff","attributes":"ReadOnly, Archive","creation_ticks":"639310337068112823","last_write_ticks":"639310337068690186","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":true,"non_reparse":true,"sha256":"c10db26a74122967df1bc704bbc747600243b8954c6424462e5acbb56ed977ee"}
'@|ConvertFrom-Json
$d='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-ui-original-45148353071-1'
$s=Join-Path $d 'final-seal.json'
$archive=Join-Path $d 'original-14807326846.zip'
$allowed=@('S-1-5-18','S-1-5-32-544','S-1-5-21-2914620446-786530585-2031499938-1001')|Sort-Object
function Observe([string]$p){
 $f=Get-Item -LiteralPath $p -Force
 if($f.PSIsContainer -or ($f.Attributes-band [IO.FileAttributes]::ReparsePoint)-ne 0 -or ($f.Attributes-band [IO.FileAttributes]::ReadOnly)-eq 0){throw 'Unexpected file type/attributes'}
 $a=Get-Acl -LiteralPath $p
 $sid=([Security.Principal.NTAccount]$a.Owner).Translate([Security.Principal.SecurityIdentifier]).Value
 $rules=@($a.Access)
 $sids=@($rules|ForEach-Object{$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value}|Sort-Object)
 if($sid-ne 'S-1-5-21-2914620446-786530585-2031499938-1001' -or -not $a.AreAccessRulesProtected -or $rules.Count-ne 3 -or ($sids-join '|')-cne($allowed-join '|')){throw 'Owner/private ACL mismatch'}
 foreach($rule in $rules){if($rule.AccessControlType-ne [Security.AccessControl.AccessControlType]::Allow -or $rule.FileSystemRights-ne [Security.AccessControl.FileSystemRights]::FullControl -or $rule.IsInherited){throw 'Unexpected file rule'}}
 $id=(& fsutil.exe file queryfileid $p 2>&1|Out-String).Trim()
 if($LASTEXITCODE-ne 0){throw 'FileID observation failed'}
 return [ordered]@{name=$f.Name;bytes=$f.Length;ntfs_file_id=$id;attributes=$f.Attributes.ToString();creation_ticks=$f.CreationTimeUtc.Ticks.ToString();last_write_ticks=$f.LastWriteTimeUtc.Ticks.ToString();owner_sid=$sid;sddl=$a.Sddl;protected=$true;non_reparse=$true}
}
$cursor=Get-Item -LiteralPath $d -Force
while($null-ne $cursor){if(($cursor.Attributes-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'Reparse ancestor'};$cursor=$cursor.Parent}
$final=Observe $s
foreach($field in @('name','bytes','ntfs_file_id','attributes','creation_ticks','last_write_ticks','owner_sid','sddl','protected','non_reparse')){if([string]$final[$field]-cne [string]$expectedFinal.$field){throw "Final seal metadata changed: $field"}}
$hash=(Get-FileHash -LiteralPath $s -Algorithm SHA256).Hash.ToLowerInvariant()
if($hash-cne 'c10db26a74122967df1bc704bbc747600243b8954c6424462e5acbb56ed977ee'){throw 'Final seal bytes changed'}
$sealed=Get-Content -LiteralPath $s -Raw|ConvertFrom-Json
$current=Observe $archive
foreach($field in @('name','bytes','ntfs_file_id','attributes','creation_ticks','last_write_ticks','owner_sid','sddl','protected','non_reparse')){if([string]$current[$field]-cne [string]$sealed.archive.$field){throw "Archive metadata changed: $field"}}
if($current.bytes-ne 140198044 -or $sealed.archive_sha256-cne 'd30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8'){throw 'Archive identity mismatch'}
if((Get-Acl -LiteralPath $d).Sddl-cne $sealed.directory_sddl){throw 'Evidence directory ACL changed'}
[ordered]@{status='PASS_FRESH_PRE_UNLINK_WINDOWS_IDENTITY_WITHOUT_PAYLOAD_REREAD';at=[DateTime]::UtcNow.ToString('o');directory=$d;directory_sddl=$sealed.directory_sddl;final_seal=$final;final_seal_sha256=$hash;archive=$current;archive_sha256_from_two_qualified_passes=$sealed.archive_sha256;archive_payload_read=$false;mutations=0;free=([IO.DriveInfo]::new('C:\')).AvailableFreeSpace}|ConvertTo-Json -Depth 10 -Compress

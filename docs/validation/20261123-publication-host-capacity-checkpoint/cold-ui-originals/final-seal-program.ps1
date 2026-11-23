$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$before=@'
{"status":"READ_ONLY_POST_SECOND_SEAL_FAILURE","at":"2026-11-23T12:27:14.9811944Z","directory":"C:\\Users\\DAVID\\AppData\\Local\\SentinelX\\anytapy-immutable-evidence\\native-ui-original-45148353071-1","directory_sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","files":[{"name":"copy-intent.json","bytes":1980,"ntfs_file_id":"File ID is 0x000000000000000000190000001a09da","attributes":"ReadOnly, Archive","creation_ticks":"639310330997278409","last_write_ticks":"639310330997278409","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"256f309b6a7a191d53173dfc714dd9647aeb297934a5e1691187918f81737f71"},{"name":"copy-progress-100663296.json","bytes":102,"ntfs_file_id":"File ID is 0x0000000000000000004100000019eed8","attributes":"ReadOnly, Archive","creation_ticks":"639310331169464029","last_write_ticks":"639310331169464029","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"1eadf10702290c00353e5867fd03e337c1363f06efceac5a5c6906ff7695fb9e"},{"name":"copy-progress-134217728.json","bytes":102,"ntfs_file_id":"File ID is 0x0000000000000000002c0000001a0a1e","attributes":"ReadOnly, Archive","creation_ticks":"639310331227686445","last_write_ticks":"639310331227686445","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"3c7acf3622b343e1ebb93e64e8dadc4e781f98cf77f20c8386e16daf23a12967"},{"name":"copy-progress-33554432.json","bytes":100,"ntfs_file_id":"File ID is 0x0000000000000000003700000019e2a4","attributes":"ReadOnly, Archive","creation_ticks":"639310331053128319","last_write_ticks":"639310331053141018","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"61dbea95863d9c63b717be04746e30a5380763bc5e8c7a235e1c0aae64966c39"},{"name":"copy-progress-67108864.json","bytes":100,"ntfs_file_id":"File ID is 0x0000000000000000002c00000019ef13","attributes":"ReadOnly, Archive","creation_ticks":"639310331111387394","last_write_ticks":"639310331111387394","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"3d276ebc1f985f8be8bbb0705a62c8ca5d7bd69aa438559b615c3057a07b10d0"},{"name":"copy-receipt.json","bytes":1370,"ntfs_file_id":"File ID is 0x000000000000000000250000001a08e8","attributes":"ReadOnly, Archive","creation_ticks":"639310331269915646","last_write_ticks":"639310331269915646","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"074cd0f50f4009f189d2951954ea7a3daa1e62fad095856a5e13074d71ef4641"},{"name":"independent-readback.json","bytes":1411,"ntfs_file_id":"File ID is 0x000000000000000000230000001a0a22","attributes":"ReadOnly, Archive","creation_ticks":"639310331861539597","last_write_ticks":"639310331861539597","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"78bac6a25a354f0c936626f14543a52d1a8095b47ed88f25ca98a9f9fc296671"},{"name":"original-14807326846.zip","bytes":140198044,"ntfs_file_id":"File ID is 0x000000000000000000150000001a09dc","attributes":"ReadOnly, Archive","creation_ticks":"639310330997364209","last_write_ticks":"639310331238035431","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":true,"non_reparse":true},{"name":"seal.json","bytes":0,"ntfs_file_id":"File ID is 0x0000000000000000001e0000001a0ced","attributes":"Archive","creation_ticks":"639310334837352010","last_write_ticks":"639310334837352010","owner_sid":"S-1-5-32-544","sddl":"O:BAG:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},{"name":"transport-process.json","bytes":166,"ntfs_file_id":"File ID is 0x000000000000000000200000001a09dd","attributes":"ReadOnly, Archive","creation_ticks":"639310330997745670","last_write_ticks":"639310330997745670","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"687cdd60752ceac54e03c7fff2caaa7b28e4c9b599f7d642b66ab86e907414e3"},{"name":"transport.stderr","bytes":0,"ntfs_file_id":"File ID is 0x000000000000000000190000001a0a30","attributes":"ReadOnly, Archive","creation_ticks":"639310331238152664","last_write_ticks":"639310331238152664","owner_sid":"S-1-5-21-2914620446-786530585-2031499938-1001","sddl":"O:S-1-5-21-2914620446-786530585-2031499938-1001G:S-1-5-21-2914620446-786530585-2031499938-1001D:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FA;;;S-1-5-21-2914620446-786530585-2031499938-1001)","protected":false,"non_reparse":true,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}],"mutations":0,"archive_payload_read":false}
'@|ConvertFrom-Json
$directory='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-ui-original-45148353071-1'
$expectedSid='S-1-5-21-2914620446-786530585-2031499938-1001'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
if($who.User.Value -ne $expectedSid){throw 'Unexpected identity'}
$allowed=@('S-1-5-18','S-1-5-32-544',$expectedSid)|Sort-Object
function Observe([string]$path,[bool]$payloadHash){
 $f=Get-Item -LiteralPath $path -Force
 if($f.PSIsContainer -or (($f.Attributes -band [IO.FileAttributes]::ReparsePoint)-ne 0)){throw 'Nonregular or reparse file'}
 $a=Get-Acl -LiteralPath $path
 $id=(& fsutil.exe file queryfileid $path 2>&1|Out-String).Trim()
 if($LASTEXITCODE-ne 0){throw 'File ID observation failed'}
 $sids=@($a.Access|ForEach-Object{$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value}|Sort-Object -Unique)
 if(($sids-join '|')-ne($allowed-join '|') -or @($a.Access).Count-ne 3){throw 'Unexpected ACL member'}
 foreach($rule in $a.Access){if($rule.AccessControlType-ne [Security.AccessControl.AccessControlType]::Allow -or $rule.FileSystemRights-ne [Security.AccessControl.FileSystemRights]::FullControl){throw 'Unexpected ACL rights'}}
 $r=[ordered]@{name=$f.Name;bytes=$f.Length;ntfs_file_id=$id;attributes=$f.Attributes.ToString();creation_ticks=$f.CreationTimeUtc.Ticks.ToString();last_write_ticks=$f.LastWriteTimeUtc.Ticks.ToString();owner_sid=([Security.Principal.NTAccount]$a.Owner).Translate([Security.Principal.SecurityIdentifier]).Value;sddl=$a.Sddl;protected=$a.AreAccessRulesProtected;non_reparse=$true}
 if($payloadHash){if($f.Length-gt 1048576){throw 'Metadata exceeds bound'};$r.sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
 return $r
}
function SameMetadata($now,$old){
 foreach($field in @('name','bytes','ntfs_file_id','creation_ticks','last_write_ticks','attributes','owner_sid','sddl','protected','non_reparse')){
  if([string]$now[$field] -cne [string]$old.$field){throw "Changed metadata: $field"}
 }
}
$cursor=Get-Item -LiteralPath $directory -Force
while($null-ne $cursor){
 if(($cursor.Attributes-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'Reparse ancestor'}
 $cursor=$cursor.Parent
}
if((Get-Acl -LiteralPath $directory).Sddl-cne $before.directory_sddl){throw 'Directory ACL changed'}
$names=@(Get-ChildItem -LiteralPath $directory -Force|ForEach-Object{$_.Name}|Sort-Object)
$expectedNames=@($before.files|ForEach-Object{$_.name}|Sort-Object)
if(($names-join '|')-cne($expectedNames-join '|') -or $names.Count-ne 11){throw 'Unexpected original membership'}
$rows=@()
foreach($old in $before.files){
 $path=Join-Path $directory $old.name
 $now=Observe $path ($old.name-ne 'original-14807326846.zip')
 SameMetadata $now $old
 if($old.name-ne 'original-14807326846.zip' -and $now.sha256-cne $old.sha256){throw 'Changed metadata bytes'}
 if($old.name-ne 'seal.json' -and $now.owner_sid-ne $expectedSid){throw 'Unexpected prior owner'}
 $rows+=$now
}
$archiveRow=@($rows|Where-Object{$_.name-eq 'original-14807326846.zip'})[0]
$copy=Get-Content -LiteralPath (Join-Path $directory 'copy-receipt.json') -Raw|ConvertFrom-Json
$readback=Get-Content -LiteralPath (Join-Path $directory 'independent-readback.json') -Raw|ConvertFrom-Json
if($copy.status-ne 'PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH' -or $readback.status-ne 'PASS_INDEPENDENT_FULL_DESTINATION_READBACK'){throw 'Original full-hash receipts not PASS'}
if($archiveRow.bytes-ne 140198044 -or $copy.sha256-cne 'd30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8' -or $readback.sha256-cne $copy.sha256 -or $archiveRow.ntfs_file_id-cne $copy.ntfs_file_id -or $archiveRow.ntfs_file_id-cne $readback.ntfs_file_id){throw 'Original archive identity mismatch'}
if($archiveRow.sddl-cne $copy.file_security.sddl -or $archiveRow.sddl-cne $readback.file_sddl -or -not $archiveRow.protected){throw 'Original archive security mismatch'}
$failedPath=Join-Path $directory 'seal.json'
$failedBefore=@($rows|Where-Object{$_.name-eq 'seal.json'})[0]
if($failedBefore.bytes-ne 0 -or $failedBefore.owner_sid-ne 'S-1-5-32-544'){throw 'Unexpected failed intermediate'}
$oldAcl=Get-Acl -LiteralPath $failedPath
$oldNonowner=$oldAcl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Group-bor [Security.AccessControl.AccessControlSections]::Access)
$oldAcl.SetOwner($who.User)
Set-Acl -LiteralPath $failedPath -AclObject $oldAcl
$failedAfter=Observe $failedPath $true
$updatedAcl=Get-Acl -LiteralPath $failedPath
$newNonowner=$updatedAcl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Group-bor [Security.AccessControl.AccessControlSections]::Access)
if($failedAfter.owner_sid-ne $expectedSid -or $oldNonowner-cne $newNonowner){throw 'Owner-only correction changed non-owner ACL'}
foreach($field in @('bytes','sha256','ntfs_file_id','creation_ticks','last_write_ticks','attributes')){if([string]$failedAfter[$field]-cne [string]$failedBefore[$field]){throw "Failed intermediate changed: $field"}}
[IO.File]::SetAttributes($failedPath,([IO.File]::GetAttributes($failedPath)-bor [IO.FileAttributes]::ReadOnly))
$failedFinal=Observe $failedPath $true
$smallRows=@($rows|Where-Object{$_.name-ne 'original-14807326846.zip' -and $_.name-ne 'seal.json'})
$proof=[ordered]@{
 status='SEALED_VERIFIED_IMMUTABLE_ARCHIVE_COPY_ONLY';at=[DateTime]::UtcNow.ToString('o');directory=$directory
 archive=$archiveRow;archive_sha256=$copy.sha256;archive_payload_read_this_seal=$false;qualified_full_destination_hash_passes=2
 small_originals=$smallRows;failed_seal=[ordered]@{status='PRESERVED_EMPTY_UNQUALIFIED_HANDLE_ACL_FAILURE';before=$failedBefore;after=$failedFinal;content_unchanged=$true;nonowner_acl_unchanged=$true;owner_only_corrected=$true;readonly_added=$true}
 preserved_failure_seal=[ordered]@{path='/mnt/development/projects/diagnostics/native-ui-451483-cold-archive-relocation-20261123/pre-final-seal-originals.json';sha256='91a64a9654a52b2a0cc35056c743fb023a2acb982916f6d8ca32b9e4f863376c'}
 directory_sddl=$before.directory_sddl;source_oracle_path=$copy.source_path;source_unlink_performed=$false;archive_content_mutations=0;archive_or_parent_acl_changes=0;new_github_downloads=0
}
$finalPath=Join-Path $directory 'final-seal.json'
if(Test-Path -LiteralPath $finalPath){throw 'Final seal already exists'}
$empty=[IO.FileStream]::new($finalPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
$empty.Dispose()
$security=New-Object Security.AccessControl.FileSecurity
$security.SetOwner($who.User)
$security.SetAccessRuleProtection($true,$false)
foreach($sid in $allowed){
 $identity=New-Object Security.Principal.SecurityIdentifier($sid)
 $rule=New-Object Security.AccessControl.FileSystemAccessRule($identity,[Security.AccessControl.FileSystemRights]::FullControl,[Security.AccessControl.AccessControlType]::Allow)
 $security.AddAccessRule($rule)
}
Set-Acl -LiteralPath $finalPath -AclObject $security
$emptyObserved=Observe $finalPath $true
if($emptyObserved.bytes-ne 0 -or $emptyObserved.owner_sid-ne $expectedSid -or -not $emptyObserved.protected){throw 'Private owner/ACL must be established before content'}
$proof.final_seal_precontent_identity=$emptyObserved
$utf8=[Text.UTF8Encoding]::new($false)
$raw=$utf8.GetBytes(($proof|ConvertTo-Json -Depth 16 -Compress)+[Environment]::NewLine)
$stream=[IO.FileStream]::new($finalPath,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{if($stream.Length-ne 0){throw 'Fresh final seal no longer empty'};$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
[IO.File]::SetAttributes($finalPath,([IO.File]::GetAttributes($finalPath)-bor [IO.FileAttributes]::ReadOnly))
$final=Observe $finalPath $true
if($final.ntfs_file_id-cne $emptyObserved.ntfs_file_id -or $final.owner_sid-ne $expectedSid -or -not $final.protected -or $final.bytes-ne $raw.Length){throw 'Final seal identity mismatch'}
$archiveNow=Observe (Join-Path $directory 'original-14807326846.zip') $false
SameMetadata $archiveNow @($before.files|Where-Object{$_.name-eq 'original-14807326846.zip'})[0]
if((Get-Acl -LiteralPath $directory).Sddl-cne $before.directory_sddl){throw 'Directory ACL changed'}
[ordered]@{status=$proof.status;final_seal=$final;archive_ntfs_file_id=$archiveRow.ntfs_file_id;archive_sha256=$copy.sha256;small_originals=$smallRows.Count;failed_empty_seal_preserved=$true;source_unlink_performed=$false;archive_payload_read_this_seal=$false;free=([IO.DriveInfo]::new('C:\')).AvailableFreeSpace}|ConvertTo-Json -Depth 8 -Compress

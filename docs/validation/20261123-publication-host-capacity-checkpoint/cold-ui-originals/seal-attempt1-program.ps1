$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$directory='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-ui-original-45148353071-1'
$archive=Join-Path $directory 'original-14807326846.zip'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
if($who.User.Value -ne 'S-1-5-21-2914620446-786530585-2031499938-1001'){throw 'Wrong owner identity'}
$copy=Get-Content -Raw -LiteralPath (Join-Path $directory 'copy-receipt.json')|ConvertFrom-Json
$readback=Get-Content -Raw -LiteralPath (Join-Path $directory 'independent-readback.json')|ConvertFrom-Json
if($copy.status -ne 'PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH' -or $readback.status -ne 'PASS_INDEPENDENT_FULL_DESTINATION_READBACK' -or $copy.sha256 -ne $readback.sha256 -or $readback.sha256 -ne 'd30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8'){throw 'Qualified original identity mismatch'}
$file=Get-Item -LiteralPath $archive -Force
if($file.Length -ne 140198044 -or (($file.Attributes -band [IO.FileAttributes]::ReadOnly) -eq 0) -or (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)){throw 'Archive metadata mismatch'}
$id=(& fsutil.exe file queryfileid $archive 2>&1|Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $id -ne $copy.ntfs_file_id -or $id -ne $readback.ntfs_file_id){throw 'Archive fileID mismatch'}
$acl=Get-Acl -LiteralPath $archive
if($acl.Sddl -ne $copy.file_security.sddl -or $acl.Sddl -ne $readback.file_sddl){throw 'Archive security changed'}
$diracl=Get-Acl -LiteralPath $directory
if($diracl.Sddl -ne $readback.directory_sddl){throw 'Directory security changed'}
$rows=@()
foreach($item in Get-ChildItem -LiteralPath $directory -Force){
 if($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)){throw 'Unexpected evidence member'}
 if($item.Name -eq 'original-14807326846.zip'){continue}
 if($item.Name -notin @('copy-intent.json','transport-process.json','transport.stderr','copy-receipt.json','independent-readback.json') -and $item.Name -notmatch '^copy-progress-[0-9]+\.json$'){throw 'Unexpected small original name'}
 if($item.Length -gt 1048576){throw 'Small original exceeds bound'}
 $s=Get-Acl -LiteralPath $item.FullName
 $owner=([Security.Principal.NTAccount]$s.Owner).Translate([Security.Principal.SecurityIdentifier]).Value
 if($owner -ne $who.User.Value){throw 'Small original owner mismatch'}
 $sids=@($s.Access|ForEach-Object{$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value}|Sort-Object -Unique)
 if(($sids -join '|') -ne ((@('S-1-5-18','S-1-5-32-544',$who.User.Value)|Sort-Object)-join '|')){throw 'Small original ACL is not private'}
 $hash=(Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
 [IO.File]::SetAttributes($item.FullName,([IO.File]::GetAttributes($item.FullName)-bor [IO.FileAttributes]::ReadOnly))
 $rows+=[ordered]@{name=$item.Name;bytes=$item.Length;sha256=$hash;owner_sid=$owner;readonly=$true;sddl=$s.Sddl}
}
$proof=[ordered]@{status='SEALED_VERIFIED_IMMUTABLE_ARCHIVE_COPY_ONLY';sealed_at=[DateTime]::UtcNow.ToString('o');directory=$directory;archive=[ordered]@{name=$file.Name;bytes=$file.Length;sha256=$copy.sha256;ntfs_file_id=$id;creation_ticks=$file.CreationTimeUtc.Ticks.ToString();last_write_ticks=$file.LastWriteTimeUtc.Ticks.ToString();readonly=$true;non_reparse=$true;owner_sid=$who.User.Value;sddl=$acl.Sddl};directory_sddl=$diracl.Sddl;small_originals=$rows;source_oracle_path=$copy.source_path;source_retained=$true;source_unlink_performed=$false;source_mutations=0;new_github_downloads=0;full_destination_hash_passes=2}
$path=Join-Path $directory 'seal.json'
if(Test-Path -LiteralPath $path){throw 'Seal already exists'}
$utf8=[Text.UTF8Encoding]::new($false)
$raw=$utf8.GetBytes(($proof|ConvertTo-Json -Depth 14 -Compress)+[Environment]::NewLine)
$stream=[IO.FileStream]::new($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
[IO.File]::SetAttributes($path,([IO.File]::GetAttributes($path)-bor [IO.FileAttributes]::ReadOnly))
[ordered]@{status=$proof.status;path=$path;bytes=$raw.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();small_original_count=$rows.Count;archive_ntfs_file_id=$id;source_retained=$true;free=([IO.DriveInfo]::new('C:\')).AvailableFreeSpace}|ConvertTo-Json -Depth 6 -Compress

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$evidenceParent='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence'
$evidenceDirectory=Join-Path $evidenceParent 'semantic-page-original-45116855451-1'
$expectedBytes=[long]703289417
$expectedSha='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'
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

$parentProof=Assert-PrivateAcl $evidenceParent $true
$directoryProof=Assert-PrivateAcl $evidenceDirectory $true
$receiptPath=Join-Path $evidenceDirectory 'copy-receipt.json'
$receipt=Get-Content -Raw -LiteralPath $receiptPath | ConvertFrom-Json
if($receipt.status -ne 'PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH' -or $receipt.sha256 -ne $expectedSha -or [long]$receipt.bytes -ne $expectedBytes -or $receipt.oracle_source_mutations -ne 0){throw 'Copy receipt identity mismatch'}
$path=Join-Path $evidenceDirectory 'original-14794983588.zip'
if($receipt.destination -ne $path){throw 'Copy destination mismatch'}
$transport=Get-Content -Raw -LiteralPath (Join-Path $evidenceDirectory 'transport-process.json') | ConvertFrom-Json
if($null -ne (Get-Process -Id $transport.pid -ErrorAction SilentlyContinue)){throw 'Owned transport PID remains'}
$before=Get-Item -LiteralPath $path -Force
if($before.Length -ne $expectedBytes -or (($before.Attributes -band [System.IO.FileAttributes]::ReadOnly) -eq 0)){throw 'Destination size/readonly mismatch'}
$fileProof=Assert-PrivateAcl $path $false
$fileId=(& fsutil.exe file queryfileid $path 2>&1 | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $fileId -ne $receipt.ntfs_file_id){throw 'Destination NTFS identity mismatch'}
$sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
$after=Get-Item -LiteralPath $path -Force
if($sha -ne $expectedSha -or $after.Length -ne $expectedBytes -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks -or $before.CreationTimeUtc.Ticks -ne $after.CreationTimeUtc.Ticks){throw 'Destination full independent readback mismatch'}
if($fileProof.sddl -ne $receipt.file_security.sddl -or $directoryProof.sddl -ne $receipt.directory_security.sddl){throw 'Destination security identity changed'}
$proof=[ordered]@{status='PASS_INDEPENDENT_FULL_DESTINATION_READBACK';verified_at=[DateTime]::UtcNow.ToString('o');path=$path;bytes=$after.Length;sha256=$sha;ntfs_file_id=$fileId;owner_sid=$fileProof.owner;file_sddl=$fileProof.sddl;directory_sddl=$directoryProof.sddl;parent_sddl=$parentProof.sddl;readonly=$true;non_reparse=$true;owned_transport_absent=$true;transport_pid=$transport.pid;receipt_path=$receiptPath;receipt_sha256=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant();oracle_source_mutations=0}
$proofPath=Join-Path $evidenceDirectory 'independent-readback.json'
if(Test-Path -LiteralPath $proofPath){throw 'Independent proof already exists'}
$utf8=New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($proofPath,(($proof | ConvertTo-Json -Depth 10 -Compress)+[Environment]::NewLine),$utf8)
$proof | ConvertTo-Json -Depth 10 -Compress

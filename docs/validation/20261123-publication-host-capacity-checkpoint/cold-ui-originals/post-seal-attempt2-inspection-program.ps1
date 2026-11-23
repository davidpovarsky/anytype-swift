$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$d='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-ui-original-45148353071-1'
$rows=@()
foreach($f in Get-ChildItem -LiteralPath $d -Force){
 if($f.PSIsContainer -or (($f.Attributes-band [IO.FileAttributes]::ReparsePoint)-ne 0)){throw 'Unexpected member'}
 $acl=Get-Acl -LiteralPath $f.FullName
 $id=(& fsutil.exe file queryfileid $f.FullName 2>&1|Out-String).Trim()
 if($LASTEXITCODE-ne 0){throw 'File identity observation failed'}
 $row=[ordered]@{name=$f.Name;bytes=$f.Length;ntfs_file_id=$id;attributes=$f.Attributes.ToString();creation_ticks=$f.CreationTimeUtc.Ticks.ToString();last_write_ticks=$f.LastWriteTimeUtc.Ticks.ToString();owner_sid=([Security.Principal.NTAccount]$acl.Owner).Translate([Security.Principal.SecurityIdentifier]).Value;sddl=$acl.Sddl;protected=$acl.AreAccessRulesProtected;non_reparse=$true}
 if($f.Name-ne 'original-14807326846.zip'){
  if($f.Length-gt 1048576){throw 'Metadata bound exceeded'}
  $row.sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
 }
 $rows+=$row
}
[ordered]@{status='READ_ONLY_POST_SECOND_SEAL_FAILURE';at=[DateTime]::UtcNow.ToString('o');directory=$d;directory_sddl=(Get-Acl -LiteralPath $d).Sddl;files=$rows;mutations=0;archive_payload_read=$false}|ConvertTo-Json -Depth 10 -Compress
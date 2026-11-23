$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$d='C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-ui-original-45148353071-1'
$names=@('copy-intent.json','copy-progress-100663296.json','copy-progress-134217728.json','copy-progress-33554432.json','copy-progress-67108864.json','copy-receipt.json','independent-readback.json','transport-process.json','transport.stderr','seal.json','final-seal.json')
$actual=@(Get-ChildItem -LiteralPath $d -Force|ForEach-Object{$_.Name}|Sort-Object)
$expected=@($names+@('original-14807326846.zip')|Sort-Object)
if(($actual-join '|')-cne($expected-join '|')){throw 'Unexpected directory membership'}
$rows=@();$total=0
foreach($n in $names){
 $p=Join-Path $d $n
 $f=Get-Item -LiteralPath $p -Force
 if($f.PSIsContainer -or ($f.Attributes-band [IO.FileAttributes]::ReparsePoint)-ne 0 -or ($f.Attributes-band [IO.FileAttributes]::ReadOnly)-eq 0 -or $f.Length-gt 1048576){throw 'Metadata shape bound'}
 $a=Get-Acl -LiteralPath $p
 $owner=([Security.Principal.NTAccount]$a.Owner).Translate([Security.Principal.SecurityIdentifier]).Value
 if($owner-ne 'S-1-5-21-2914620446-786530585-2031499938-1001'){throw 'Owner mismatch'}
 $raw=[IO.File]::ReadAllBytes($p);$total+=$raw.Length
 if($total-gt 1048576){throw 'Total metadata bound'}
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$sha=([BitConverter]::ToString($hash.ComputeHash($raw))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
 $id=(& fsutil.exe file queryfileid $p 2>&1|Out-String).Trim();if($LASTEXITCODE-ne 0){throw 'FileID failure'}
 $rows+=[ordered]@{name=$n;bytes=$raw.Length;sha256=$sha;base64=[Convert]::ToBase64String($raw);owner_sid=$owner;sddl=$a.Sddl;protected=$a.AreAccessRulesProtected;ntfs_file_id=$id;creation_ticks=$f.CreationTimeUtc.Ticks.ToString();last_write_ticks=$f.LastWriteTimeUtc.Ticks.ToString();attributes=$f.Attributes.ToString();non_reparse=$true;readonly=$true}
}
[ordered]@{status='READ_ONLY_EXACT_SMALL_ORIGINALS';at=[DateTime]::UtcNow.ToString('o');directory=$d;directory_sddl=(Get-Acl -LiteralPath $d).Sddl;files=$rows;total_bytes=$total;archive_payload_read=$false;mutations=0}|ConvertTo-Json -Depth 10 -Compress

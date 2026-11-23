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
function Write-Record([string]$name,$value){
 $text=($value | ConvertTo-Json -Depth 12 -Compress)+[Environment]::NewLine
 $path=Join-Path $evidenceDirectory $name
 $temporary=$path+'.writing'
 [System.IO.File]::WriteAllText($temporary,$text,$utf8)
 if(Test-Path -LiteralPath $path){throw 'Immutable receipt name collision'}
 [System.IO.File]::Move($temporary,$path)
}
$sourceRecord=ConvertFrom-Json -InputObject @'
{"status":"SOURCE_ARCHIVE_BYTES_VERIFIED_READ_ONLY","at":"2026-11-23T11:11:35.491784+00:00","path":"/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit/artifact-14794983588.zip","metadata":{"allocated":"703295488","bytes":"703289417","ctime_ns":"1795416720571794129","device":"2064","gid":"1002","inode":"1114801","mode":"436","mtime_ns":"1795416720054790888","nlink":"1","uid":"1001"},"sha256":"082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46","source_mutations":0,"app_source":"68148339c275268795360d71d519a5baf003adf8","origin_run":45116855451,"origin_attempt":1,"artifact_id":14794983588,"pinned_admission":"Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json","pinned_admission_source":"c0c1f851f80322c9f532e86505047498dfaf1adf","qualification":"Copy-only full source hash and four stable exact metadata observations; final peer and reader gate required before redundant Oracle unlink."}
'@
$remotePython=@'
import pathlib,os,sys,hashlib,stat,json
p=pathlib.Path('/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit/artifact-14794983588.zip')
assert p.resolve()==p and p.is_file() and not p.is_symlink()
def metadata(st):return {'device':st.st_dev,'inode':st.st_ino,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'nlink':st.st_nlink,'bytes':st.st_size,'allocated':st.st_blocks*512,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
expected={k:int(v) for k,v in json.loads('{"allocated":"703295488","bytes":"703289417","ctime_ns":"1795416720571794129","device":"2064","gid":"1002","inode":"1114801","mode":"436","mtime_ns":"1795416720054790888","nlink":"1","uid":"1001"}').items()}
assert metadata(p.stat())==expected
digest=hashlib.sha256();count=0
with p.open('rb') as f:
 assert metadata(os.fstat(f.fileno()))==expected
 while True:
  b=f.read(4*1024*1024)
  if not b:break
  count+=len(b);assert count<=703289417
  digest.update(b);sys.stdout.buffer.write(b)
 assert metadata(os.fstat(f.fileno()))==expected
sys.stdout.buffer.flush()
assert metadata(p.stat())==expected
assert count==703289417 and digest.hexdigest()=='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'

'@
$started=[DateTime]::UtcNow.ToString('o')
Write-Record 'copy-intent.json' ([ordered]@{status='COPY_ONLY_SOURCE_REMAINS_ON_ORACLE';started_at=$started;source=$sourceRecord;destination_directory=$evidenceDirectory;directory_security=$directoryProof;expected_bytes=$expectedBytes;expected_sha256=$expectedSha;oracle_unlink_authorized_by_this_program=$false})
$partial=Join-Path $evidenceDirectory 'original-14794983588.zip.partial'
$final=Join-Path $evidenceDirectory 'original-14794983588.zip'
$process=$null
$destinationStream=$null
$received=[long]0
$watch=[System.Diagnostics.Stopwatch]::StartNew()
try{
 $destinationStream=New-Object System.IO.FileStream($partial,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None,1048576,[System.IO.FileOptions]::SequentialScan)
 $startInfo=New-Object System.Diagnostics.ProcessStartInfo
 $startInfo.FileName='ssh.exe'
 $startInfo.Arguments='-T torah-dev python3 -B -u -'
 $startInfo.UseShellExecute=$false
 $startInfo.CreateNoWindow=$true
 $startInfo.RedirectStandardInput=$true
 $startInfo.RedirectStandardOutput=$true
 $startInfo.RedirectStandardError=$true
 $process=New-Object System.Diagnostics.Process
 $process.StartInfo=$startInfo
 if(-not $process.Start()){throw 'Could not start owned SSH transport'}
 $errorRead=$process.StandardError.ReadToEndAsync()
 $process.StandardInput.Write($remotePython)
 $process.StandardInput.Close()
 Write-Record 'transport-process.json' ([ordered]@{pid=$process.Id;started_at=[DateTime]::UtcNow.ToString('o');exe='ssh.exe';arguments=$startInfo.Arguments;scope='ONE_EXISTING_ORACLE_ARCHIVE_READ_ONLY'})
 $buffer=New-Object byte[] 1048576
 $lastProgress=[long]0
 while($true){
  if($watch.Elapsed.TotalSeconds -gt 1200){throw 'Owned archive copy time budget exceeded'}
  $readTask=$process.StandardOutput.BaseStream.ReadAsync($buffer,0,$buffer.Length)
  if(-not $readTask.Wait(60000)){throw 'Owned archive transport read stalled for60seconds'}
  $n=$readTask.Result
  if($n -eq 0){break}
  $received+=$n
  if($received -gt $expectedBytes){throw 'Archive exceeded exact original size'}
  $destinationStream.Write($buffer,0,$n)
  if(($received-$lastProgress) -ge 33554432){
   $destinationStream.Flush()
   Write-Record ('copy-progress-'+$received+'.json') ([ordered]@{at=[DateTime]::UtcNow.ToString('o');received=$received;expected=$expectedBytes;seconds=$watch.Elapsed.TotalSeconds})
   $lastProgress=$received
  }
 }
 $destinationStream.Flush($true)
 $destinationStream.Dispose()
 $destinationStream=$null
 if(-not $process.WaitForExit(30000)){throw 'Owned SSH transport did not exit'}
 $stderr=$errorRead.Result
 [System.IO.File]::WriteAllText((Join-Path $evidenceDirectory 'transport.stderr'),$stderr,$utf8)
 if($process.ExitCode -ne 0 -or $received -ne $expectedBytes){throw 'Original source/transport identity verification failed'}
 $actualSha=(Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
 if($actualSha -ne $expectedSha -or (Get-Item -LiteralPath $partial).Length -ne $expectedBytes){throw 'Destination full original hash mismatch'}
 [System.IO.File]::Move($partial,$final)
 $fileAcl=New-Object System.Security.AccessControl.FileSecurity
 $fileAcl.SetAccessRuleProtection($true,$false)
 $fileAcl.SetOwner($who.User)
 foreach($sid in $allowedSids){
  $identity=New-Object System.Security.Principal.SecurityIdentifier($sid)
  $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($identity,[System.Security.AccessControl.FileSystemRights]::FullControl,[System.Security.AccessControl.AccessControlType]::Allow)
  $fileAcl.AddAccessRule($rule)
 }
 Set-Acl -LiteralPath $final -AclObject $fileAcl
 $fileSecurity=Assert-PrivateAcl $final $false
 [System.IO.File]::SetAttributes($final,([System.IO.File]::GetAttributes($final) -bor [System.IO.FileAttributes]::ReadOnly))
 $fileId=(& fsutil.exe file queryfileid $final 2>&1 | Out-String).Trim()
 if($LASTEXITCODE -ne 0 -or $fileId -notmatch '0x[0-9a-fA-F]+'){throw 'NTFS file identity unavailable; retain final file without qualification'}
 $record=[ordered]@{status='PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH';started_at=$started;finished_at=[DateTime]::UtcNow.ToString('o');seconds=$watch.Elapsed.TotalSeconds;source_path=$sourceRecord.path;source_run=$sourceRecord.origin_run;source_artifact=$sourceRecord.artifact_id;destination=$final;bytes=$received;sha256=$actualSha;ntfs_file_id=$fileId;file_security=$fileSecurity;directory_security=$directoryProof;readonly=$true;oracle_source_retained=$true;oracle_source_mutations=0;new_github_downloads=0}
 Write-Record 'copy-receipt.json' $record
 $record | ConvertTo-Json -Depth 12 -Compress
}catch{
 if($null -ne $destinationStream){$destinationStream.Dispose()}
 if($null -ne $process){try{if(-not $process.HasExited){$process.Kill();$process.WaitForExit(5000) | Out-Null}}catch{}}
 $failure=[ordered]@{status='FAIL_ORIGINAL_AND_PARTIAL_RETAINED';started_at=$started;failed_at=[DateTime]::UtcNow.ToString('o');received_bytes=$received;seconds=$watch.Elapsed.TotalSeconds;error_type=$_.Exception.GetType().FullName;error=$_.Exception.Message;oracle_source_retained=$true;partial_path=$partial;final_path=$final}
 Write-Record 'copy-failure.json' $failure
 $failure | ConvertTo-Json -Depth 10 -Compress
 exit 1
}

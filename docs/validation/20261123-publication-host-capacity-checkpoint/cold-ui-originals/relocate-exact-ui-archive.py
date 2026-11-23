from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat,subprocess,time
D=Path("/mnt/development/projects/diagnostics/native-ui-451483-cold-archive-relocation-20261123")
SOURCE=Path("/mnt/development/projects/diagnostics/native-ui-451483-original-result-20261123/artifact-14807326846.zip")
LOCATION=Path(str(SOURCE)+".location.json")
PREPARED_SHA="82042a965961fe1952f566de828c395b546e58c0f93ab19b119223049750e07a"
SHA="d30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8"
WINDOWS_SEAL="c10db26a74122967df1bc704bbc747600243b8954c6424462e5acbb56ed977ee"
PRODUCER="9cafd32811e50f4e883efb034888d7ce1e349c02"
COMPILED="4b09cc5478c60c1c6728a54f2a27a115637a835b"
def sha(data):return hashlib.sha256(data).hexdigest()
def meta(st):return {k:str(v) for k,v in {"device":st.st_dev,"inode":st.st_ino,"mode":stat.S_IMODE(st.st_mode),"uid":st.st_uid,"gid":st.st_gid,"nlink":st.st_nlink,"bytes":st.st_size,"allocated":st.st_blocks*512,"mtime_ns":st.st_mtime_ns,"ctime_ns":st.st_ctime_ns}.items()}
def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
def put(path,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
    assert shutil.disk_usage(D).free-len(data)>=2500000000,"capacity guard"
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(fd,"wb") as f:f.write(data);f.flush();os.fsync(f.fileno())
    fsync_dir(path.parent)
    return {"path":str(path),"bytes":len(data),"sha256":sha(data)}
def protected_files():
    rows=[]
    for p in sorted(SOURCE.parent.rglob("*")):
        if p==SOURCE or p==LOCATION:continue
        st=p.lstat()
        if stat.S_ISDIR(st.st_mode):continue
        assert stat.S_ISREG(st.st_mode) and not p.is_symlink(),str(p)
        rows.append({"path":str(p.relative_to(SOURCE.parent)),"metadata":meta(st)})
    return rows
assert shutil.disk_usage(D).free-2097152>=2500000000,"capacity guard"
assert not LOCATION.exists() and not LOCATION.is_symlink()
prepared_raw=(D/"prepared-relocation-proof.json").read_bytes()
assert sha(prepared_raw)==PREPARED_SHA
prepared=json.loads(prepared_raw)
for row in prepared["original_file_index"]:
    p=D/row["path"];data=p.read_bytes()
    assert len(data)==row["bytes"] and sha(data)==row["sha256"]
source=prepared["source"]
assert source["path"]==str(SOURCE) and source["sha256"]==SHA
assert source["app_source"]==PRODUCER
assert int(source["metadata"]["bytes"])==140198044 and int(source["metadata"]["allocated"])==140206080
assert meta(SOURCE.lstat())==source["metadata"] and stat.S_ISREG(SOURCE.lstat().st_mode) and not SOURCE.is_symlink()
for parent in [SOURCE.parent,*SOURCE.parent.parents]:
    assert not parent.is_symlink() and parent.is_dir()
windows_raw=(D/"pre-unlink-windows-verification.json").read_bytes()
windows=json.loads(windows_raw)
assert windows["status"]=="PASS_FRESH_PRE_UNLINK_WINDOWS_IDENTITY_WITHOUT_PAYLOAD_REREAD"
assert windows["final_seal_sha256"]==WINDOWS_SEAL
assert windows["archive_sha256_from_two_qualified_passes"]==SHA
assert windows["archive"]["ntfs_file_id"]=="File ID is 0x000000000000000000150000001a09dc"
assert windows["archive"]["bytes"]==140198044 and windows["archive"]["owner_sid"]=="S-1-5-21-2914620446-786530585-2031499938-1001"
assert windows["archive"]["protected"] and windows["archive"]["non_reparse"]
assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(windows["at"].replace("Z","+00:00"))).total_seconds()<300,"Windows proof too old"
assert not windows["archive_payload_read"] and windows["mutations"]==0
before=protected_files()
before_ref=put(D/"protected-originals-before-unlink.json",{"files":before,"count":len(before),"excluded_only":[str(SOURCE),str(LOCATION)]})
restore_path=D/"restore-plan.json";restore_bytes=restore_path.read_bytes()
assert sha(restore_bytes)=="322c6b63017f6ac56771c516af03a79e5d102d81c7dc4c1f229301043c5d26b5"
linkage={
 "schema":"anytapy-cold-archive-restore-linkage-v1","status":"DURABLE_RESTORE_LINKAGE_PREPARED_BEFORE_EXACT_UNLINK",
 "sourceOracle":str(SOURCE),"locationPointer":str(LOCATION),"destinationWindows":windows["directory"]+"\\original-14807326846.zip",
 "producerSource":PRODUCER,"compiledAppSource":COMPILED,"runID":45148353071,"runAttempt":1,"artifactID":14807326846,
 "bytes":140198044,"sha256":SHA,"windowsFinalSealSHA256":WINDOWS_SEAL,
 "restorePlan":{"path":str(restore_path),"sha256":sha(restore_bytes)},
 "preparedProof":{"path":str(D/"prepared-relocation-proof.json"),"sha256":PREPARED_SHA},
 "originalRawSourceRecord":{"path":str(D/"source-original.json"),"sha256":sha((D/"source-original.json").read_bytes()),"legacyField":"app_source","legacyFieldMeaning":"producing workflow/controller HEAD; preserved unchanged, not compiled App source"},
 "sourceMetadataStrings":source["metadata"],"authorization":"Parent /root explicitly authorized unlink only this exact redundant Oracle ZIP after fresh destination and privileged zero-reader checks; no other source/artifact/Git mutation.",
 "at":datetime.now(timezone.utc).isoformat()
}
linkage_ref=put(D/"unlink-restore-linkage.json",linkage)
pointer={
 "schema":"anytapy-cold-archive-location-v1","status":"VERIFIED_IMMUTABLE_COPY_LOCATION",
 "originalOraclePath":str(SOURCE),"retainedWindowsPath":linkage["destinationWindows"],
 "runID":45148353071,"runAttempt":1,"artifactID":14807326846,
 "producerSource":PRODUCER,"compiledAppSource":COMPILED,"bytes":140198044,"sha256":SHA,
 "ntfsFileID":windows["archive"]["ntfs_file_id"],"ownerSID":windows["archive"]["owner_sid"],"privateSDDL":windows["archive"]["sddl"],"readonly":True,"nonReparse":True,
 "finalSeal":{"path":windows["directory"]+"\\final-seal.json","sha256":WINDOWS_SEAL},
 "freshDestinationProof":{"path":str(D/"pre-unlink-windows-verification.json"),"sha256":sha(windows_raw)},
 "restoreLinkage":linkage_ref,"restorePlan":linkage["restorePlan"],"originalSourceMetadataStrings":source["metadata"],
 "sourceFieldClarification":"The preserved raw source-original.app_source field is the producing controller HEAD. compiledAppSource separately identifies the immutable App compiled at 4b09cc5478c60c1c6728a54f2a27a115637a835b.",
 "createdBeforeUnlink":True,"createdAt":datetime.now(timezone.utc).isoformat()
}
pointer_ref=put(LOCATION,pointer)
assert sha(LOCATION.read_bytes())==pointer_ref["sha256"]
assert sha((D/"unlink-restore-linkage.json").read_bytes())==linkage_ref["sha256"]
assert protected_files()==before
assert meta(SOURCE.lstat())==source["metadata"]
scanner=(D/"process-scanner.py").read_bytes()
assert sha(scanner)=="cb7e8c8bca4aafc08684b0961af5b9700bce293098b57d722a085237546ada46"
anc=[];pid=os.getpid()
while pid>1 and pid not in anc:
    anc.append(pid)
    try:pid=int(Path("/proc/"+str(pid)+"/stat").read_text().rsplit(")",1)[1].split()[1])
    except (FileNotFoundError,ValueError):break
gate_start=datetime.now(timezone.utc).isoformat()
proc=subprocess.run(["sudo","-n","python3","-B","-c",scanner.decode(),json.dumps([str(SOURCE)]),json.dumps(anc)],capture_output=True,timeout=30)
gate_finished=time.monotonic()
for name,data in (("immediate-unlink-process-scan.stdout",proc.stdout),("immediate-unlink-process-scan.stderr",proc.stderr)):
    fd=os.open(D/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(fd,"wb") as f:f.write(data);f.flush();os.fsync(f.fileno())
assert proc.returncode==0,proc.stderr.decode()
observed=json.loads(proc.stdout)
assert observed["uid"]==0 and not observed["hits"] and not observed["denied"],observed
parent_fd=os.open(SOURCE.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:
    exact=os.stat(SOURCE.name,dir_fd=parent_fd,follow_symlinks=False)
    assert meta(exact)==source["metadata"] and stat.S_ISREG(exact.st_mode)
    assert os.stat(SOURCE.parent).st_ino==os.fstat(parent_fd).st_ino
    before_free=shutil.disk_usage(SOURCE.parent).free
    assert time.monotonic()-gate_finished<2,"Reader gate stale"
    preunlink_elapsed=time.monotonic()-gate_finished
    os.unlink(SOURCE.name,dir_fd=parent_fd)
    os.fsync(parent_fd)
finally:os.close(parent_fd)
assert not SOURCE.exists() and not SOURCE.is_symlink()
after_free=shutil.disk_usage(SOURCE.parent).free
after=protected_files()
assert after==before,"Protected extracted originals/reviews changed"
assert sha(LOCATION.read_bytes())==pointer_ref["sha256"]
assert sha((D/"unlink-restore-linkage.json").read_bytes())==linkage_ref["sha256"]
receipt={
 "status":"PASS_EXACT_DUPLICATE_RELOCATED_ORACLE_CARRIER_UNLINKED","at":datetime.now(timezone.utc).isoformat(),
 "sourceOracle":str(SOURCE),"destinationWindows":linkage["destinationWindows"],
 "bytes":140198044,"sha256":SHA,"allocatedBytesRecovered":140206080,
 "freeBytesBeforeExactUnlink":before_free,"freeBytesAfterExactUnlink":after_free,"observedFreeDelta":after_free-before_free,
 "producerSource":PRODUCER,"compiledAppSource":COMPILED,"legacySourceOriginalRecordUnchanged":True,
 "locationPointer":pointer_ref,"restoreLinkage":linkage_ref,"restorePlan":linkage["restorePlan"],"preparedProof":linkage["preparedProof"],
 "freshWindowsProof":{"path":str(D/"pre-unlink-windows-verification.json"),"sha256":sha(windows_raw)},
 "immediatePrivilegedReaderGate":{"startedAt":gate_start,"scannerSHA256":sha(scanner),"excludedObserverAncestry":anc,"observation":observed,"scanToUnlinkSeconds":preunlink_elapsed},
 "sourceMetadataBeforeUnlink":meta(exact),"sourceAbsentAfterUnlink":True,"unlinkedPaths":[str(SOURCE)],
 "protectedOriginalFiles":len(before),"protectedMetadataBeforeAfterEqual":True,"protectedOriginalsSnapshot":before_ref,
 "preservedPreparedOriginalFiles":len(prepared["original_file_index"]),"archivePayloadRereads":0,"newDownloads":0,
 "projectSourceGitWorktreeMutations":0,"testsOrBuilds":0,"windowsArchiveMutations":0
}
receipt_ref=put(D/"relocation-receipt.json",receipt)
print(json.dumps({"receipt":receipt_ref,"pointer":pointer_ref,"restoreLinkage":linkage_ref,"allocatedBytesRecovered":140206080,"freeBefore":before_free,"freeAfter":after_free,"observedDelta":after_free-before_free,"protectedOriginalFiles":len(before),"reader":observed,"scanToUnlinkSeconds":preunlink_elapsed,"sourceAbsent":True},sort_keys=True))

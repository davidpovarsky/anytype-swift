from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat,subprocess
D=Path("/mnt/development/projects/diagnostics/native-ui-451483-cold-archive-relocation-20261123")
assert shutil.disk_usage(D).free-262144>=2500000000,"capacity guard"
source=json.loads((D/"source-original.json").read_bytes());p=Path(source["path"])
def sha(b):return hashlib.sha256(b).hexdigest()
def meta(st):return {k:str(v) for k,v in {"device":st.st_dev,"inode":st.st_ino,"mode":stat.S_IMODE(st.st_mode),"uid":st.st_uid,"gid":st.st_gid,"nlink":st.st_nlink,"bytes":st.st_size,"allocated":st.st_blocks*512,"mtime_ns":st.st_mtime_ns,"ctime_ns":st.st_ctime_ns}.items()}
def write(name,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
    target=D/name
    assert not target.exists() and not target.is_symlink()
    with target.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.chmod(target,0o400)
    return {"path":name,"bytes":len(data),"sha256":sha(data)}
assert meta(p.lstat())==source["metadata"] and stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink()
scanner=(D/"process-scanner.py").read_bytes()
assert sha(scanner)=="cb7e8c8bca4aafc08684b0961af5b9700bce293098b57d722a085237546ada46"
anc=[];pid=os.getpid()
while pid>1 and pid not in anc:
    anc.append(pid)
    try:pid=int(Path("/proc/"+str(pid)+"/stat").read_text().rsplit(")",1)[1].split()[1])
    except (FileNotFoundError,ValueError):break
started=datetime.now(timezone.utc).isoformat()
proc=subprocess.run(["sudo","-n","python3","-B","-c",scanner.decode(),json.dumps([str(p)]),json.dumps(anc)],capture_output=True,timeout=30)
for name,data in (("final-process-scan.stdout",proc.stdout),("final-process-scan.stderr",proc.stderr)):
    with (D/name).open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
assert proc.returncode==0,proc.stderr.decode()
observed=json.loads(proc.stdout)
assert observed["uid"]==0 and not observed["hits"] and not observed["denied"]
assert meta(p.lstat())==source["metadata"]
reader={"status":"PASS_FRESH_PRIVILEGED_READ_ONLY_SOURCE_READER_CHECK","started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"source":str(p),"source_metadata":meta(p.lstat()),"source_metadata_unchanged":True,"scanner_sha256":sha(scanner),"excluded_observer_ancestry":anc,"observation":observed,"source_unlink_performed":False,"source_mutations":0,"must_refresh_immediately_before_root_unlink":True}
reader_ref=write("final-source-reader-proof.json",reader)
small=D/"windows-small-originals"
copy=json.loads((small/"copy-receipt.json").read_bytes())
readback=json.loads((small/"independent-readback.json").read_bytes())
final_raw=(small/"final-seal.json").read_bytes()
assert sha(final_raw)=="c10db26a74122967df1bc704bbc747600243b8954c6424462e5acbb56ed977ee"
final=json.loads(final_raw)
assert copy["status"]=="PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH"
assert readback["status"]=="PASS_INDEPENDENT_FULL_DESTINATION_READBACK"
assert final["status"]=="SEALED_VERIFIED_IMMUTABLE_ARCHIVE_COPY_ONLY"
assert copy["sha256"]==readback["sha256"]==final["archive_sha256"]==source["sha256"]
assert final["archive"]["bytes"]==int(source["metadata"]["bytes"])==140198044
assert final["archive"]["ntfs_file_id"]==copy["ntfs_file_id"]==readback["ntfs_file_id"]=="File ID is 0x000000000000000000150000001a09dc"
assert final["archive"]["owner_sid"]=="S-1-5-21-2914620446-786530585-2031499938-1001"
assert final["archive"]["protected"] and final["archive"]["non_reparse"]
assert final["archive"]["sddl"]==copy["file_security"]["sddl"]==readback["file_sddl"]
assert final["failed_seal"]["content_unchanged"] and final["failed_seal"]["nonowner_acl_unchanged"]
assert final["failed_seal"]["before"]["bytes"]==final["failed_seal"]["after"]["bytes"]==0
assert not final["source_unlink_performed"]
restore={
 "status":"RESTORE_RECIPE_ONLY_NOT_EXECUTED",
 "source_windows":final["directory"]+"\\original-14807326846.zip",
 "destination_oracle":str(p),
 "bytes":140198044,"sha256":source["sha256"],
 "windows_identity":{"ntfs_file_id":final["archive"]["ntfs_file_id"],"owner_sid":final["archive"]["owner_sid"],"sddl":final["archive"]["sddl"],"readonly":True,"non_reparse":True},
 "original_oracle_metadata_strings":source["metadata"],
 "steps":[
 "Refresh both source Windows immutable identity/security and Oracle capacity/process checks.",
 "Refuse if the exact original destination or any reparse/symlink component exists; never overwrite it.",
 "Create a fresh task-owned .partial beside the target with O_CREAT|O_EXCL|O_NOFOLLOW and mode 0600.",
 "Stream exactly 140198044 bytes from the retained private archive via the existing authenticated connection; verify full SHA-256 and size on both ends without exposing credentials.",
 "fsync the completed file; set the original uid 1001, gid 1002, mode 0400 and mtime_ns 1795429704588428412 only on that fresh file.",
 "Publish without replacement, fsync its parent directory and preserve an original restore receipt; verify exact bytes/hash/mode/uid/gid/mtime.",
 "Record the new inode, ctime and destination identity honestly; they cannot be recreated as the historical inode/ctime."
 ],
 "network_redownload_required":False,"project_code_or_products_move":False}
restore_ref=write("restore-plan.json",restore)
files=[]
for path in sorted(D.rglob("*")):
    if path.is_dir():continue
    assert path.is_file() and not path.is_symlink(),str(path)
    data=path.read_bytes()
    assert len(data)<2097152,str(path)
    st=path.stat()
    files.append({"path":str(path.relative_to(D)),"bytes":len(data),"sha256":sha(data),"mode":oct(stat.S_IMODE(st.st_mode))})
proof={
 "status":"READY_FOR_ROOT_REVIEW_COPY_AND_READBACK_COMPLETE_SOURCE_RETAINED",
 "at":datetime.now(timezone.utc).isoformat(),"diagnostics":str(D),
 "source":source,"destination_directory":final["directory"],
 "destination_archive":{"name":"original-14807326846.zip","bytes":140198044,"sha256":source["sha256"],"ntfs_file_id":final["archive"]["ntfs_file_id"],"owner_sid":final["archive"]["owner_sid"],"sddl":final["archive"]["sddl"],"readonly":True,"non_reparse":True},
 "windows_final_seal":{"path":str(small/"final-seal.json"),"sha256":sha(final_raw),"bytes":len(final_raw)},
 "reader_proof":reader_ref,"restore_plan":restore_ref,
 "copy_and_independent_readback_passes":2,
 "preserved_failures":[{"phase":"first metadata seal","result":"owner guard refused nine new metadata files with default Administrators owner; archive owner/ACL already correct"},{"phase":"second metadata seal","result":"write-only FileStream ACL operation failed; empty unqualified seal preserved and later owner-only corrected"},{"phase":"originals-preservation composer","result":"replacement token syntax failure before any statement/write; corrected reader and original failure preserved"}],
 "scoped_metadata_followup":"Nine new small receipt owners and empty failed receipt owner corrected to DAVID with bytes/FileID/timestamps/non-owner ACL preserved; readonly added. New final seal owner and explicit private ACL verified before content.",
 "source_unlink_authorized":False,"source_unlink_performed":False,"source_mutations":0,"source_still_present":p.is_file(),
 "archive_content_mutations":0,"archive_or_parent_acl_changes":0,"project_source_or_git_changes":0,"product_builds_or_tests":0,"new_github_downloads":0,
 "fresh_root_reader_check_required_before_unlink":True,"free_bytes":shutil.disk_usage(D).free,
 "original_file_index":files
}
ref=write("prepared-relocation-proof.json",proof)
assert meta(p.lstat())==source["metadata"]
print(json.dumps({"proof":ref,"reader_proof":reader_ref,"restore_plan":restore_ref,"file_count":len(files),"source_still_present":True,"source_unlink_performed":False,"reader":observed,"free":shutil.disk_usage(D).free},sort_keys=True))

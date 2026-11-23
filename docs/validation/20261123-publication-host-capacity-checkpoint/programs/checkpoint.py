import hashlib,json,os,shutil,stat,subprocess,time
from pathlib import Path
R=Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
B=Path("/mnt/development/projects/diagnostics")
OUT=R/"docs/validation/20261123-publication-host-capacity-checkpoint"
EXPECTED="e4edea19ce716280f4087f8b9571ad2b4f6f94c5"
def need(c,m):
 if not c:raise RuntimeError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(R),*a],timeout=60)
need(git("rev-parse","HEAD").decode().strip()==EXPECTED,"HEAD differs")
need(git("status","--porcelain=v1","--untracked-files=all")==b"","main not clean")
need(not OUT.exists(),"checkpoint exists")
need(shutil.disk_usage(R).free>=2500000000+16*1024**2,"capacity")
C=B/"native-ui-451483-cold-archive-relocation-20261123"
P=B/"sdk-ui-page-composition-20261123"
O=B/"sdk-ui-page-publication-originals-20261123"
H=B/"sdk-ui-host-continuation-originals-20261123"
pointer=B/"native-ui-451483-original-result-20261123/artifact-14807326846.zip.location.json"
critical={
 C/"relocation-receipt.json":"05eb06415ccc5eff440fbfa6ae20cf86a047790993646792923a8e55fee28f5b",
 C/"unlink-restore-linkage.json":"e4750f229788d94e7dd36984d703fc3450abb95c6b4e2f93a9bede84f8a5aedc",
 C/"protected-originals-before-unlink.json":"bef16a2b4c139563255e6de1a70337d2329c0c9d851e9242ecb83c840508603d",
 pointer:"f410182838e5abfa867de5336e49d3a2fc5ff90483a1e006af5ccaa7cd76d12f",
 P/"publication.json":"18f924b771139cf39ea76530fc9ebbe7e7c3b47eaa8ceac5b1d826cd08fb0dcf",
 O/"transfer-receipt.json":"5be67b02fefc62b8d94d6dc2ea836ac9fbd0461c076e5348605e7f17c3eeb858",
 H/"transfer-receipt.json":"492ed664947fe043e70266b5405a0fa6bf2289c134b08fe54c4d74dbcfa379c5"}
for p,h in critical.items():need(sha(p.read_bytes())==h,"critical original differs "+str(p))
need(not pointer.with_suffix("").exists(),"relocated duplicate still exists")
selected=[]
for base,prefix in [(C,"cold-ui-originals"),(O,"dispatch-originals"),(H,"host-continuation-originals")]:
 for name in subprocess.check_output(["rg","--files",str(base)],timeout=30).decode().splitlines():
  p=Path(name);selected.append((p,Path(prefix)/p.relative_to(base)))
for p in P.iterdir():
 if p.is_file() and (p.name.startswith("publication") or p.name.startswith("observe-") or p.name in {"publish-scoped-owner-session.py","dispatch-three-routes.ps1"}):
  selected.append((p,Path("publication-originals")/p.name))
selected.append((pointer,Path("cold-ui-originals")/"artifact-14807326846.zip.location.json"))
need(len(selected)==len({str(r) for _,r in selected}),"duplicate destination")
need(len(selected)<400 and sum(p.stat().st_size for p,_ in selected)<8*1024**2,"bounded original inventory")
OUT.mkdir(parents=True,mode=0o700)
rows=[]
for p,rel in sorted(selected,key=lambda x:str(x[1])):
 info=p.lstat();need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and p.resolve()==p,"nonregular original "+str(p))
 b=p.read_bytes();dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 need(dest.read_bytes()==b,"copy differs")
 after=p.lstat()
 need((after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_mode)==(info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_mode),"original changed during copy")
 rows.append({"source":str(p),"destination":str(rel),"bytes":len(b),"sha256":sha(b),"source_inode":str(info.st_ino),"source_mtime_ns":str(info.st_mtime_ns),"source_ctime_ns":str(info.st_ctime_ns),"source_mode":stat.S_IMODE(info.st_mode)})
receipt={"protocol":"publication-host-capacity-durable-checkpoint-v1","base_head":EXPECTED,"originals":rows,"count":len(rows),"bytes":sum(x["bytes"] for x in rows),"publication_head":EXPECTED,"dispatch_runs":{"sdk":45174279596,"ui":45174286335,"page":45174292731},"known_terminal_attempt1":{"sdk":"NO_HOST_ACQUIRED_ZERO_STEPS","ui":"NO_HOST_ACQUIRED_ZERO_STEPS"},"sdk_ui_one_owned_continuation_submitted":True,"page_result_not_claimed":True,"relocated_exact_duplicate":"artifact-14807326846.zip","allocated_bytes_recovered":140206080,"preserved_original_ui_files":3292,"original_failures_preserved":True,"source_or_product_changes":0,"tests_replayed":0,"artifact_redownloads":0,"credentials_copied":False,"created_ns":str(time.time_ns())}
raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
with (OUT/"checkpoint.json").open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
readme="""# Publication, host acquisition, and capacity checkpoint

This checkpoint preserves original operational evidence; it makes no product acceptance claim.

## Published source and controls

Oracle Git published e4edea19ce716280f4087f8b9571ad2b4f6f94c5 without force, after the source retention gate. The original mirror/refspec failure and missing workflow OAuth scope rejection remain intact. Publication succeeded using the existing authorized davidpovarsky Windows session passed over SSH stdin into process-local GH_TOKEN on Oracle. No token or persistent credential change was retained. All Git/source work remained on Oracle.

SDK06, the five failed UI scopes, and mounted Page each received one original dispatch against that source. All three original dispatch and exact identity receipts are included.

## Actual CI boundary

SDK run45174279596/1 and UI run45174286335/1 completed without acquiring a hosted runner: runner_id0, zero steps, zero artifacts. Their original GitHub check annotations state that the job was not acquired by a hosted runner even after multiple attempts. This is not a product test outcome. One owned failed-job debug continuation was submitted per route, retaining source, selection and budgets. Attempt2 observers run independently; no result is inferred here. Page run45174292731 remains outside the terminal conclusions of this checkpoint.

## Reversible exact duplicate relocation

The sole Oracle duplicate of UI artifact14807326846 was removed only after the complete 140198044-byte Windows copy and independent readback matched SHA-256 d30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8, private ownership/ACL and file identity were sealed, and an immediate process scan reported no users or denied inspections. A durable pointer and exact restore linkage were written before unlink. Exactly140206080 allocated bytes were recovered. All3292 extracted originals, protected reviews, worktrees, refs, Git objects and failures remain preserved.

The original metadata-owner and seal-attempt failures are retained with their corrections. The older source-original.app_source field was misnamed:9cafd32811e50f4e883efb034888d7ce1e349c02 is the producer controller, while the compiled immutable App is4b09cc5478c60c1c6728a54f2a27a115637a835b. Original bytes were not rewritten; the later restore linkage states both roles.

## Limits

This documentation checkpoint runs no host control, Apple product method or build. The original passing control evidence is reused with its existing scope. Native lifecycle, SDK/product execution, the failed UI scopes, Page/Release, migration parity and physical-device acceptance remain open until their separate evidence qualifies them. Every copied original is bound by size and SHA-256 in checkpoint.json. Nanosecond metadata is encoded as strings.
"""
(OUT/"README.md").write_text(readme)
program=Path("/mnt/development/projects/diagnostics/publication-host-capacity-checkpoint-20261123/checkpoint.py")
dest=OUT/"programs/checkpoint.py";dest.parent.mkdir()
dest.write_bytes(program.read_bytes())
relative=OUT.relative_to(R).as_posix()
git("add","--",relative)
changed=git("diff","--cached","--name-only").decode().splitlines()
need(changed and all(x.startswith(relative+"/") for x in changed),"staged scope")
proc=subprocess.run(["git","-C",str(R),"-c","gc.auto=0","-c","user.name=davidpovarsky","-c","user.email=your-email@example.com","commit","-m","docs: retain publication, host acquisition and exact UI archive relocation"],capture_output=True,timeout=120)
log=program.parent
for n,data in [("commit.stdout",proc.stdout),("commit.stderr",proc.stderr)]:
 with (log/n).open("xb") as f:f.write(data)
need(proc.returncode==0,"commit failed; original logs preserved")
need(git("status","--porcelain=v1","--untracked-files=all")==b"","post-commit dirty")
result={"status":"PASS_DOCUMENTATION_CHECKPOINT","head":git("rev-parse","HEAD").decode().strip(),"base":EXPECTED,"checkpoint_sha256":sha(raw),"count":len(rows),"bytes":receipt["bytes"],"changed_paths":len(changed),"tests_run":0,"free_bytes":shutil.disk_usage(R).free}
with (log/"result.json").open("x") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
print(json.dumps(result))

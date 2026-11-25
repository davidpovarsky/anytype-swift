from pathlib import Path
import hashlib,json,os,stat,tarfile
ROOT=Path("/Users/m1/builds/pinkha-c-native-type-order-20261125/native-attempt2")
OUT=Path("/Users/m1/builds/pinkha-c-native-type-order-20261125/native-attempt2-seal")
EXPECTED="6d2930308be5a45e3bb52e9dea467b872f1347b693a08d5c480006ee84b53ae4"
os.umask(0o077)
def sha(p):
    with p.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def identity(p):
    s=p.lstat();return [s.st_dev,s.st_ino,stat.S_IMODE(s.st_mode)]
assert ROOT.resolve()==ROOT and not ROOT.is_symlink()
root_identity=identity(ROOT)
original=ROOT/"controller-result.json"
assert sha(original)==EXPECTED
r=json.loads(original.read_bytes())
assert r["result"]=="PROCESS_LIFECYCLE_PASS" and len(r["processes"])==2
assert len({x["pid"] for x in r["processes"]})==2
assert all(x["exitCode"]==0 and x["groupPositivelyAbsent"] and not x["forcedKill"] for x in r["processes"])
def inventory():
    assert identity(ROOT)==root_identity and sha(original)==EXPECTED
    items={}
    for p in sorted(ROOT.rglob("*")):
        key=str(p.relative_to(ROOT));s=p.lstat()
        if stat.S_ISDIR(s.st_mode):value={"kind":"directory","mode":stat.S_IMODE(s.st_mode)}
        elif stat.S_ISREG(s.st_mode):value={"kind":"file","mode":stat.S_IMODE(s.st_mode),"bytes":s.st_size,"sha256":sha(p)}
        else:raise ValueError("Unexpected private account filesystem entry")
        items[key]=value
    assert identity(ROOT)==root_identity and sha(original)==EXPECTED
    return items
before=inventory()
OUT.mkdir(mode=0o700,exist_ok=False)
archive=OUT/"native-account-and-original-evidence.tar.gz"
with tarfile.open(archive,"w:gz") as output:
    for relative in before:output.add(ROOT/relative,arcname=relative,recursive=False)
after=inventory()
assert before==after
with tarfile.open(archive,"r:gz") as source:
    members=source.getmembers()
    assert len(members)==len(before) and len({x.name for x in members})==len(before)
    for member in members:
        expected=before[member.name]
        assert member.mode==expected["mode"]
        if expected["kind"]=="file":
            assert member.isfile() and member.size==expected["bytes"]
            stream=source.extractfile(member)
            assert hashlib.file_digest(stream,"sha256").hexdigest()==expected["sha256"]
        else:assert member.isdir()
assert inventory()==before
(OUT/"private-inventory.json").write_text(json.dumps(before,sort_keys=True,indent=2)+"\n")
receipt={"protocol":"pinkha-native-type-order-private-retention-v1","status":"PASS",
 "nativeAcceptanceReceiptSHA256":EXPECTED,"nativeProcessExitCodes":[x["exitCode"] for x in r["processes"]],
 "ownedRootIdentity":root_identity,"entries":len(before),
 "sourceBytes":sum(x.get("bytes",0) for x in before.values()),
 "archiveBytes":archive.stat().st_size,"archiveSHA256":sha(archive),
 "privateInventorySHA256":sha(OUT/"private-inventory.json"),
 "fullOriginalAccountAndLogs":True,"newNativeCalls":0,"wholeSpaceMigration":False}
(OUT/"retention.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print(json.dumps(receipt))

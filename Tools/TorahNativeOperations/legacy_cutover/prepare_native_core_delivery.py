#!/usr/bin/env python3
"""Package the exact accepted native core overlay; no new build or account writes."""
import difflib, hashlib, json, os, shutil, subprocess, tarfile, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
WORKTREE=HERE.parents[2]
RUN=Path("/var/tmp/pinkha-e-cutover-current8ac-20261127")
ARCHIVE=Path("/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/native-source-8ac407e75a4b.tar.gz")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p): return {"bytes":p.stat().st_size,"sha256":sha(p)}
def save(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def main():
    original=json.loads((HERE/"native-core-current8ac-candidate.json").read_text())
    delta=json.loads((RUN/"attempt6/source-delta.json").read_text())
    receipt=json.loads((RUN/"attempt6/receipt.json").read_text())
    assert receipt["status"]=="PASS_ACTUAL_CORE_REGISTRY_NOT_RPC_PEER_OR_APPLE"
    assert receipt["retainedSourceUnchanged"] is True
    assert sha(ARCHIVE)==original["baseArchiveSHA256"]
    outputs={}
    for rel,expected in original["sourceFiles"].items():
        actual=row(HERE/"overlay"/rel)
        required=delta[rel]["afterSHA256"] if rel in delta else expected["sha256"]
        assert actual["sha256"]==required,rel
        outputs[rel]=actual
    evidence=WORKTREE/"docs/architecture/20261127-heart-cutover-native-core"
    evidence.mkdir(parents=True,exist_ok=True)
    copies={
      "original-receipt.json":RUN/"attempt6/receipt.json",
      "original-proof.json":RUN/"attempt6/private/TestPinkhaTorahCutoverActualCoreRegistryAndReopen/core-cutover-proof.json",
      "attempt2-original-failure.json":RUN/"attempt2/receipt.json",
      "attempt4-original-failure.json":RUN/"attempt4/receipt.json",
      "attempt5-original-failure.json":RUN/"attempt5/receipt.json",
      "source-delta.json":RUN/"attempt6/source-delta.json",
      "cache-reclaim-receipt.json":RUN/"cache-reclaim/receipt.json",
    }
    for name,p in copies.items(): shutil.copyfile(p,evidence/name)
    patch=[]
    with tempfile.TemporaryDirectory(prefix="cutover-patch-admission-",dir=RUN) as scratch:
        scratch=Path(scratch)
        with tarfile.open(ARCHIVE) as tar:
            for rel in sorted(outputs):
                oldName="heart/"+rel
                try: old=tar.extractfile(oldName).read()
                except KeyError: old=None
                new=(HERE/"overlay"/rel).read_bytes()
                if old==new: continue
                if old is not None:
                    assert hashlib.sha256(old).hexdigest()==original["originalReplacements"][rel]["sha256"],rel
                    p=scratch/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(old)
                patch.extend(difflib.unified_diff(
                    [] if old is None else old.decode().splitlines(keepends=True),
                    new.decode().splitlines(keepends=True),
                    fromfile="/dev/null" if old is None else "a/"+rel,
                    tofile="b/"+rel))
        patchPath=evidence/"current8ac-native-core.patch"
        patchPath.write_text("".join(patch))
        checked=subprocess.run(["git","apply","--check",str(patchPath)],cwd=scratch,capture_output=True,text=True)
        assert checked.returncode==0,checked.stdout+checked.stderr
        applied=subprocess.run(["git","apply",str(patchPath)],cwd=scratch,capture_output=True,text=True)
        assert applied.returncode==0,applied.stdout+applied.stderr
        assert {rel:row(scratch/rel) for rel in outputs}==outputs,"applied patch differs from tested overlay"
    manifest={
      "protocol":"pinkha-current8ac-cutover-core-qualified-v1",
      "status":receipt["status"],
      "baseManifestSHA256":original["baseManifestSHA256"],
      "baseArchiveSHA256":original["baseArchiveSHA256"],
      "baseSourcePins":original["baseSourcePins"],"baseFiles":original["baseFiles"],
      "retainedCandidateSHA256":sha(HERE/"native-core-current8ac-candidate.json"),
      "sourceFiles":outputs,"originalReplacements":original["originalReplacements"],
      "newFiles":original["newFiles"],"patch":row(patchPath),
      "exactPatchAppliedAndHashVerified":True,
      "nativeReceipt":row(evidence/"original-receipt.json"),
      "nativeProof":row(evidence/"original-proof.json"),
      "binarySHA256":receipt["binarySHA256"],
      "sourceManifestBeforeSHA256":sha(RUN/"attempt6/source-before.json"),
      "sourceManifestAfterSHA256":sha(RUN/"attempt6/source-after.json"),
      "sourceUnchanged":receipt["retainedSourceUnchanged"],
      "librarySHA256":"eb659a16cf763a47b41c837eeeb10d8743ed5bb96eb4b675582b6ca7c5ebb5f7",
      "goWorkSumSHA256":"0ce118248f3e2580833e915dbd3ef14925d3a71a1601e4c7d679b9217a368586",
      "sharedFixtureSHA256":"6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7",
      "originalRunRoot":str(RUN/"attempt6"),
      "generatedRPC":False,"peerTransport":False,"newProcessReopen":False,"appleUI":False,
      "appBuilds":0,"nativeSliceBuilds":0
    }
    save(HERE/"native-core-current8ac-qualified.json",manifest)
    save(evidence/"evidence-index.json",{
      "originalArtifacts":{name:{"path":str(p),**row(p)} for name,p in copies.items()},
      "originalLogs":{
        "nativeCore":{"path":str(RUN/"attempt6/commands/core/original.log"),**row(RUN/"attempt6/commands/core/original.log")},
        "originalFactoryPanic":{"path":str(RUN/"attempt4/commands/core/original.log"),**row(RUN/"attempt4/commands/core/original.log")},
        "originalDivergedRetryFailure":{"path":str(RUN/"attempt5/commands/core/original.log"),**row(RUN/"attempt5/commands/core/original.log")}
      },
      "manifest":{"path":str(HERE/"native-core-current8ac-qualified.json"),**row(HERE/"native-core-current8ac-qualified.json")},
      "patch":row(patchPath)
    })
    print(json.dumps({"files":len(outputs),"manifest":row(HERE/"native-core-current8ac-qualified.json"),"patch":row(patchPath),"receipt":row(evidence/"original-receipt.json"),"path":str(evidence)}))
if __name__=="__main__":main()

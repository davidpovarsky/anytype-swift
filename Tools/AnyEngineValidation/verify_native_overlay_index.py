#!/usr/bin/env python3
"""Verify a complete native overlay with disposable Git indexes, leaving worktrees untouched."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,tempfile
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--any-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    manifest_path=args.manifest.resolve();manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    summary={}
    with tempfile.TemporaryDirectory(prefix="pinkha-overlay-index-") as stage:
        for name,path in (("any",args.any_root),("sdk",args.any_root/".runtime-artifacts/sdk-source")):
            spec=manifest[name]
            patch=manifest_path.parent/spec["patch"]
            assert hashlib.sha256(patch.read_bytes()).hexdigest()==spec["patchSHA256"]
            env=dict(os.environ,GIT_INDEX_FILE=str(Path(stage)/(name+".index")))
            def git(*parts):
                return subprocess.check_output(["git","-C",str(path),*parts],env=env,text=True).strip()
            git("read-tree",spec["upstreamCommit"])
            git("apply","--check","--cached",str(patch))
            git("apply","--cached",str(patch))
            changed=set(git("diff","--cached","--name-only",spec["upstreamCommit"]).splitlines())
            assert changed=={entry["path"] for entry in spec["files"]}
            for entry in spec["files"]:
                assert git("ls-files","--stage","--",entry["path"]).split()[1]==entry["gitBlob"],entry["path"]
            summary[name]={"upstreamCommit":spec["upstreamCommit"],"patchSHA256":spec["patchSHA256"],
                           "verifiedFiles":len(changed)}
    receipt={"status":"PASS_EXACT_PATCH_APPLY_TO_CLEAN_INDEX",
        "sourceManifestSHA256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "createdAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope":"Separate temporary Git indexes from exact upstream commits; complete path/blob verification. Worktrees and ordinary indexes untouched; no Apple build/runtime claim.",
        "sources":summary}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt))
if __name__=="__main__":main()

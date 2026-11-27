#!/usr/bin/env python3
"""Materialize only Go vet's required empty directory for an additive overlay."""
import json,os,time
from pathlib import Path
import qualify_current8ac_core as base
import continue_current8ac_core as retained
EXPECTED_RPC="75f44277c8c5b3f89c5f9e1ed28e443658dd38a72bd573edc18a95f61e42dd48"
def main():
 os.umask(0o077)
 out=retained.BASE.parent/"rpc-overlay-topology2"
 assert not out.exists();out.mkdir(mode=0o700)
 source=retained.BASE/"source";target=source/"heart/pb/cutoverpb"
 expected=json.loads(base.pinned(retained.BASE/"source-before.json",retained.SOURCE_MANIFEST).read_text())
 base.pinned(base.HERE/"rpc-source-candidate.json",EXPECTED_RPC)
 def inventory():return {str(p.relative_to(source)):base.row(p) for p in sorted(source.rglob("*")) if p.is_file()}
 assert inventory()==expected
 assert not target.exists() and target.parent.is_dir() and target.parent.resolve()==target.parent
 receipt={"status":"PREPARING_EMPTY_OVERLAY_DIRECTORY_NOT_ACCEPTANCE","candidateSHA256":EXPECTED_RPC,
  "sourceFileManifestSHA256":retained.SOURCE_MANIFEST,"sourceFiles":len(expected),"directory":str(target),
  "originalDirectoryPresent":False,"sourceFilesWritten":0,"vetDisabled":False,
  "reason":"Go vet changes working directory to additive overlay package; virtual files alone do not provide a physical cwd"}
 base.save(out/"started.json",receipt)
 target.mkdir(mode=0o700)
 assert target.is_dir() and not target.is_symlink() and not list(target.iterdir())
 assert inventory()==expected
 receipt.update(status="PREPARED_EMPTY_OVERLAY_DIRECTORY_NOT_ACCEPTANCE",
  originalSourceFileBytesUnchanged=True,emptyDirectoryMode=oct(target.stat().st_mode & 0o777),
  completedUTC=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()))
 base.save(out/"receipt.json",receipt)
 print(json.dumps(receipt))
if __name__=="__main__":main()

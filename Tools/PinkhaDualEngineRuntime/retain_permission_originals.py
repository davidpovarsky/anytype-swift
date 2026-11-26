"""Stream exact completed 8ac source, dependencies, products and evidence offhost."""
from pathlib import Path
import argparse,hashlib,json,os,stat,sys,tarfile,time

BASE=Path("/Users/m1/development/anytype-d-active-20261125/native-permission8ac")
MANIFEST="8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
EXCLUDED={"tmp","go-state","swift-module-cache"}
def require(ok,why):
    if not ok: raise ValueError(why)
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024**2),b""): h.update(b)
    return h.hexdigest()
def write(p,v):
    with p.open("x") as f:
        os.chmod(p,0o600);json.dump(v,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
def row(p):
    a=p.lstat()
    require(not stat.S_ISLNK(a.st_mode),"unexpected_original_symlink:"+str(p))
    v={"mode":stat.S_IMODE(a.st_mode),"kind":"directory" if stat.S_ISDIR(a.st_mode) else "file"}
    require(stat.S_ISDIR(a.st_mode) or stat.S_ISREG(a.st_mode),"unexpected_original_kind")
    if v["kind"]=="file":v.update(bytes=a.st_size,sha256=digest(p))
    z=p.lstat()
    require((a.st_dev,a.st_ino,a.st_mode,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_mode,z.st_size,z.st_mtime_ns),"original_changed_while_reading")
    return v
def inventory(roots):
    result={}
    for prefix,root,exclude in roots:
        for p in sorted(root.rglob("*")):
            rel=p.relative_to(root)
            if rel.parts[0] in exclude:continue
            key=prefix+"/"+rel.as_posix()
            require(key not in result,"duplicate_archive_member")
            result[key]=row(p)
    return result
class HashedStream:
    def __init__(self,raw):self.raw=raw;self.h=hashlib.sha256();self.bytes=0
    def write(self,b):
        n=self.raw.write(b);require(n==len(b),"short_archive_write")
        self.h.update(b);self.bytes+=n;return n
    def flush(self):self.raw.flush()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=["simulator","device"],required=True)
    p.add_argument("--receipt-sha",required=True)
    p.add_argument("--evidence",choices=["evidence","evidence-gateway-invocation-resume-1"],required=True)
    p.add_argument("--control",choices=["control","control-gateway-e993"],required=True)
    a=p.parse_args()
    root=BASE/("pinkha-dual-native-v1-"+MANIFEST[:12]+"-"+a.phase)
    control=BASE/a.control
    target=BASE/(a.phase+"-original-retention1")
    require(root.resolve()==root and control.resolve()==control and not target.exists(),"exact_fresh_owned_paths_required")
    raw=(root/a.evidence/"receipt.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest()==a.receipt_sha,"original_terminal_receipt_changed")
    receipt=json.loads(raw)
    require(receipt["status"]=="SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
            and receipt["sourceManifestSHA256"]==MANIFEST and receipt["sourceUnchanged"] is True
            and receipt["sourceFilesVerified"]==4868,"qualified_original_phase_required")
    require(digest(control/"source-permission-manifest.json")==MANIFEST,"original_control_manifest_changed")
    source=json.loads((control/"source-permission-manifest.json").read_bytes())
    for relative,expected in source["files"].items():
        actual=root/"source"/relative
        require(actual.resolve()==actual and actual.is_file() and actual.stat().st_size==expected["bytes"]
                and digest(actual)==expected["sha256"],"original_source_changed:"+relative)
    controller=control/("build_apple_permission.py" if a.control=="control" else "build_apple_permission_gateway_continuation.py")
    require(digest(controller)==receipt["controllerSHA256"],"actual_controller_bytes_changed")
    target.mkdir(mode=0o700)
    roots=[("original",root,EXCLUDED),("producer-control",control,set())]
    result={"protocol":"pinkha8ac-original-offhost-stream-v1","status":"FAIL","phase":a.phase,
            "originalReceiptSHA256":a.receipt_sha,"sourceManifestSHA256":MANIFEST,"sourceFiles":4868,
            "sourceRoot":str(root),"controlRoot":str(control),"excludedReproducibleCaches":sorted(EXCLUDED),
            "nativeBuildsNow":0,"testsNow":0,"appleApplicationAcceptance":False,"started":time.time()}
    stream=HashedStream(sys.stdout.buffer)
    try:
        before=inventory(roots);write(target/"members-before.json",before)
        result.update(members=len(before),memberInventorySHA256=digest(target/"members-before.json"))
        with tarfile.open(fileobj=stream,mode="w|gz",compresslevel=1,format=tarfile.PAX_FORMAT) as archive:
            for name,expected in before.items():
                prefix,relative=name.split("/",1)
                original=(root if prefix=="original" else control)/relative
                info=tarfile.TarInfo(name);info.mode=expected["mode"];info.mtime=original.lstat().st_mtime
                if expected["kind"]=="directory":
                    info.type=tarfile.DIRTYPE;archive.addfile(info)
                else:
                    info.size=expected["bytes"]
                    with original.open("rb") as f:archive.addfile(info,f)
        stream.flush()
        after=inventory(roots);write(target/"members-after.json",after)
        require(before==after and digest(root/a.evidence/"receipt.json")==a.receipt_sha,"originals_changed_after_stream")
        result.update(status="PASS_ORIGINAL_STREAM_AND_SOURCE_UNCHANGED",
                      allOriginalsUnchanged=True,archiveBytes=stream.bytes,archiveSHA256=stream.h.hexdigest())
    except BaseException as e:
        result["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        result["finished"]=time.time();write(target/"retention.json",result)
if __name__=="__main__":main()

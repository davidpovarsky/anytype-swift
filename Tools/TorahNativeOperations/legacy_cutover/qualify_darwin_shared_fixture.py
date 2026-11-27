#!/usr/bin/env python3
"""Compile the unchanged qualified shared codec for the actual Darwin host test."""
import argparse,hashlib,importlib.util,json,os,shutil,stat,sys
from pathlib import Path
ORIGINAL_SOURCE_SHA="5f5567c7b3c996e48892c849e5658bf86731f860269f4f9b9650f090e901822c"
ORIGINAL_QUALIFICATION_SHA="db5b5a4682a474730a78c2a2637fbd38f1ee8a3079ec5bd5a6a56a444571809c"
HELPER_SHA="64b4310f7b1db57df0236074d4c7a9058041f6c06e6667797ceafe0099360a21"
GENERATOR_SHA="2afb93590e7b44353bc8ab3d6b67c80e3179ae34ab8a3d9e37a80a243c98a49d"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--inputs",type=Path,required=True);ap.add_argument("--root",type=Path,required=True);a=ap.parse_args()
    directory=Path(__file__).resolve().parent
    helper=directory/"darwin_owned_commands.py"
    if helper.is_symlink() or hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:raise ValueError("owned command helper changed")
    spec=importlib.util.spec_from_file_location("cutover_darwin_commands",directory/"darwin_owned_commands.py")
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    os.umask(0o077);root=a.root.absolute()
    if root.parent.resolve()!=root.parent or not str(root).startswith("/Users/m1/development/anytype-e-active-20261125/"):raise ValueError("protected canonical E component root")
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    result={"status":"FAIL","appBuilds":0,"nativeCalls":0,"testsExecuted":0,"scope":"actual shared-codec Darwin executable only"}
    commands=c.Commands(root,2<<30);expected={};package=None
    try:
        inputs=a.inputs.resolve(strict=True)
        if c.digest(inputs/"source-before.json")!=ORIGINAL_SOURCE_SHA or c.digest(inputs/"original-qualification.json")!=ORIGINAL_QUALIFICATION_SHA:raise ValueError("qualified original source pins")
        original=json.loads((inputs/"source-before.json").read_text())
        if len(original)!=71 or shutil.disk_usage(root).free<(3<<30):raise ValueError("source census or measured component phase allowance")
        result["initialFreeBytes"]=shutil.disk_usage(root).free
        package=root/"package";package.mkdir()
        for rel,row in original.items():
            name=Path(rel)
            if name.is_absolute() or ".." in name.parts:raise ValueError("source path")
            donor=inputs/"package"/name
            if donor.stat().st_size!=row["bytes"] or c.digest(donor)!=row["sha256"]:raise ValueError("original source changed: "+rel)
            dest=package/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest);expected[rel]=dict(row)
        text=(package/"Package.swift").read_text()
        before='defaultLocalization: "en",\n'
        after='defaultLocalization: "en", platforms: [.macOS(.v14)],\n'
        if text.count(before)!=1:raise ValueError("original package format")
        updated=text.replace(before,after)
        if updated.replace(after,before)!=text:raise ValueError("whole package inverse")
        (package/"Package.swift").write_text(updated)
        expected["Package.swift"]={"bytes":(package/"Package.swift").stat().st_size,"sha256":c.digest(package/"Package.swift")}
        if c.digest(package/"Fixture/CutoverSharedFixture.swift")!=GENERATOR_SHA:raise ValueError("actual shared generator")
        def inventory():
            paths=sorted(p for p in package.rglob("*") if p.is_file())
            return {str(p.relative_to(package)):{"bytes":p.stat().st_size,"sha256":c.digest(p)} for p in paths}
        if inventory()!=expected:raise ValueError("complete compiler source")
        c.save(root/"source-before.json",expected)
        c.save(root/"package-inverse.json",{"originalSourceSHA256":ORIGINAL_SOURCE_SHA,"originalQualificationSHA256":ORIGINAL_QUALIFICATION_SHA,
            "originalPackageSHA256":original["Package.swift"]["sha256"],"modifiedPackageSHA256":expected["Package.swift"]["sha256"],
            "replacement":{"before":before,"after":after},"unrelatedSourceFilesUnchanged":70})
        temporary=root/"temporary";temporary.mkdir()
        env=dict(os.environ,TMPDIR=str(temporary),SWIFTPM_MODULECACHE_OVERRIDE=str(root/"module-cache"))
        commands.run("swift-version",["/usr/bin/xcrun","swift","--version"],root,env,30)
        commands.run("build",["/usr/bin/xcrun","swift","build","--package-path",str(package),
            "--scratch-path",str(root/"swift-build"),"--jobs","2","--product","CutoverSharedFixture"],root,env,600)
        binaries=[p for p in (root/"swift-build").rglob("CutoverSharedFixture") if p.is_file() and not p.is_symlink() and stat.S_IMODE(p.stat().st_mode)&0o111]
        if len(binaries)!=1:raise ValueError("one actual Darwin executable required")
        binary=binaries[0]
        if binary.read_bytes()[:4] not in (b"\xcf\xfa\xed\xfe",b"\xfe\xed\xfa\xcf"):raise ValueError("Mach-O executable required")
        after_inventory=inventory();c.save(root/"source-after.json",after_inventory)
        if after_inventory!=expected or c.digest(inputs/"source-before.json")!=ORIGINAL_SOURCE_SHA:raise ValueError("source changed")
        result.update(status="PASS_COMPILED_SHARED_DARWIN_FIXTURE_NOT_NATIVE_ACCEPTANCE",binary=str(binary),
            binaryBytes=binary.stat().st_size,binarySHA256=c.digest(binary),sourceSHA256=c.digest(root/"source-before.json"),
            generatorSHA256=GENERATOR_SHA,sourceUnchanged=True)
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    finally:
        failures=commands.cleanup();result["commands"]=commands.rows;result["cleanupFailures"]=failures
        if hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:result.update(status="FAIL",controlError="owned helper changed")
        if failures:result["status"]="FAIL"
        if package is not None:
            try:
                final={str(p.relative_to(package)):{"bytes":p.stat().st_size,"sha256":c.digest(p)} for p in sorted(package.rglob("*")) if p.is_file()}
                c.save(root/"source-final.json",final)
                if final!=expected:result.update(status="FAIL",sourceError="final source differs")
            except Exception as error:result.update(status="FAIL",sourceError=str(error))
        c.save(root/"receipt.json",result)
    print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""Qualify the shared JSON parser with exact production source and original Any controls."""
import argparse, hashlib, json, os, pathlib, shutil, signal, subprocess, time, traceback
import xml.etree.ElementTree as ET

BASE = "643c7d8b7091f010b5b5a00bab050e54b123648b"
TORAH = "9058b489e9acc271b4f8ef69e2ed24648f93b4ed"
PINS = {
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahSourceJSONGuard.swift": "ad856a6ed49f645ec2d5cb6a0bc3c7b6e7566c5cd7ad2a3081ccd748849ab9f6",
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift": "2b1f9cc73fd50f591c78aab44d65645f45bbde3edff0b7a43157d14bc0c827a8",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Storage/TorahSourceJSONGuardTests.swift": "763a09cdcfa366984e7e8a1454d7baf3b9f76e014c70913cb88a7253258a2223",
}
EXPECTED = {
    "equivalentDecimalSpellingsPreserveExactValues",
    "changedPrecisionKeepsExactJSONPointer",
    "escapedDuplicateKeysRefuseEitherInput",
    "canonicalUnknownNumbersCannotLosePrecision",
    "canonicalNumbersRemainSafeAcrossCodecAndGuard",
    "malformedJSONNeverBecomesAValidEmptyComparison",
    "exactDecimalGuardAcceptsEquivalentNotationAndIgnoresNumericStrings",
    "ambiguousDuplicateJSONKeysCannotBeImported",
}
PKG = """// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "SharedTorahJSONGuardQualification", defaultLocalization: "en",
    products: [],
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"],
                resources: [.process("Editor/Resources")]),
        .target(name: "AnyJSONCompatibility", dependencies: ["PinkhaKit"]),
        .testTarget(name: "JSONGuardTests", dependencies: ["PinkhaKit", "AnyJSONCompatibility"])
    ], swiftLanguageModes: [.v6])
"""
def sha(b): return hashlib.sha256(b).hexdigest()
def save(p, value):
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")
    os.replace(tmp,p)
def git(tree,*args):
    return subprocess.check_output(["git","-c","safe.directory="+str(tree),"-C",str(tree),*args],timeout=30)
def snapshot(root):
    rows=[]
    for p in sorted(root.rglob("*")):
        if p.is_symlink(): raise RuntimeError("symlink:"+str(p))
        if p.is_file():
            b=p.read_bytes(); rows.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":sha(b)})
    return rows
def group_present(group):
    # Linux own-group observation, bounded to the current process table.
    rows=[]
    for path in pathlib.Path("/proc").iterdir():
        if not path.name.isdigit(): continue
        try:
            raw=(path/"stat").read_text()
            fields=raw[raw.rfind(")")+2:].split()
            if int(fields[2]) == group:
                rows.append({"pid":int(path.name),"state":fields[0]})
        except FileNotFoundError: pass
    return rows
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source-tree",type=pathlib.Path,required=True)
    ap.add_argument("--torah-tree",type=pathlib.Path,required=True)
    ap.add_argument("--root",type=pathlib.Path,required=True); a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False)
    result={"status":"FAIL","baseCommit":BASE,"torahCoreCommit":TORAH,"appBuilds":0,"nativeCalls":0,
            "scope":"Shared PinkhaKit JSON guard and Any compatibility surface; not full Any integration or Apple acceptance"}
    process=None; absent=False; cleanup=[]
    begin=time.monotonic()
    try:
        if shutil.disk_usage(a.root).free < 3*1024**3: raise RuntimeError("admission-capacity")
        if git(a.source_tree,"rev-parse","HEAD").decode().strip()!=BASE: raise RuntimeError("source-head-changed")
        originals={}
        for name,digest in PINS.items():
            p=a.source_tree/name
            if p.is_symlink(): raise RuntimeError("source-symlink")
            b=p.read_bytes()
            if sha(b)!=digest: raise RuntimeError("source-pin:"+name)
            originals[name]=b
        old=git(a.source_tree,"show",BASE+":Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift").decode()
        shared=originals["Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahSourceJSONGuard.swift"].decode()
        marker="    private struct Scanner {"
        if shared[shared.index(marker):].replace("TorahSourceJSONGuardError","AnyTorahMigrationError") != old[old.index(marker):]:
            raise RuntimeError("scanner-extraction-diff")
        package=a.root/"package"; (package/"Sources").mkdir(parents=True)
        prefix="Modules/PinkhaKit/Sources/PinkhaKit/"
        tracked=git(a.source_tree,"ls-tree","-r","--name-only",BASE,prefix).decode().splitlines()
        actual=sorted(p.relative_to(a.source_tree).as_posix() for p in (a.source_tree/prefix).rglob("*") if p.is_file())
        new=prefix+"Torah/TorahSourceJSONGuard.swift"
        if actual!=sorted(tracked+[new]): raise RuntimeError("complete-PinkhaKit-source-set")
        for name in tracked:
            if (a.source_tree/name).read_bytes()!=git(a.source_tree,"show",BASE+":"+name):
                raise RuntimeError("unreviewed-PinkhaKit-source:"+name)
        shutil.copytree(a.source_tree/prefix,package/"Sources/PinkhaKit",symlinks=True)
        torahFiles=git(a.torah_tree,"ls-tree","-r","--name-only",TORAH,"Sources/TorahInspectorCore").decode().splitlines()
        if len(torahFiles)!=8: raise RuntimeError("TorahCore-source-set")
        for name in torahFiles:
            dst=package/name; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(git(a.torah_tree,"show",TORAH+":"+name))
        compat=package/"Sources/AnyJSONCompatibility"; compat.mkdir()
        (compat/"AnyTorahSourceJSONGuard.swift").write_bytes(originals["Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift"])
        tests=package/"Tests/JSONGuardTests"; tests.mkdir(parents=True)
        (tests/"TorahSourceJSONGuardTests.swift").write_bytes(originals["Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Storage/TorahSourceJSONGuardTests.swift"])
        originalTests=git(a.source_tree,"show",BASE+":Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AssociationBridgeTests.swift").decode()
        names=["exactDecimalGuardAcceptsEquivalentNotationAndIgnoresNumericStrings","ambiguousDuplicateJSONKeysCannotBeImported"]
        methods=[]
        for name in names:
            start=originalTests.index("    @Test func "+name+"(")
            end=min(x for x in [originalTests.find("\n    @Test ",start+1),originalTests.find("\n    private func ",start+1)] if x>=0)
            methods.append(originalTests[start:end].rstrip()+"\n")
        wrapper="import Foundation\nimport Testing\n@testable import AnyJSONCompatibility\n\nstruct AnyOriginalSourceJSONGuardControls {\n"+"\n".join(methods)+"}\n"
        (tests/"AnyOriginalSourceJSONGuardControls.swift").write_text(wrapper)
        (package/"Package.swift").write_text(PKG)
        sourceBefore=snapshot(package); save(a.root/"source-before.json",sourceBefore)
        save(a.root/"extraction.json",{"scannerExactInverse":True,"originalAnyMethods":[{"name":n,"sha256":sha(m.encode())} for n,m in zip(names,methods)],"wholePinkhaKitProductionFiles":len(actual),"wholeTorahCoreProductionFiles":len(torahFiles),"pins":PINS})
        cmd=["/usr/local/bin/swift","test","--package-path",str(package),"--scratch-path",str(a.root/"build"),"--jobs","2","--xunit-output",str(a.root/"original.xml"),"--filter","TorahSourceJSONGuardTests|AnyOriginalSourceJSONGuardControls"]
        with (a.root/"original.log").open("wb") as log:
            process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            result.update({"command":cmd,"pid":process.pid,"pgid":process.pid,"started":time.time()})
            save(a.root/"started.json",result)
            while process.poll() is None:
                if time.monotonic()-begin>900: raise RuntimeError("deadline")
                if shutil.disk_usage(a.root).free<2*1024**3: raise RuntimeError("capacity-floor")
                time.sleep(1)
            result["exitCode"]=process.wait()
        rows=group_present(process.pid); absent=not rows
        if rows: raise RuntimeError("owned-group-remains:"+str(rows))
        result["ownedGroupAbsent"]=True
        after=snapshot(package); save(a.root/"source-after.json",after)
        if sourceBefore!=after: raise RuntimeError("materialized-source-changed")
        for name,b in originals.items():
            if (a.source_tree/name).read_bytes()!=b: raise RuntimeError("original-source-changed")
        if result["exitCode"]!=0: raise RuntimeError("swift-tests-failed")
        tree=ET.parse(a.root/"original.xml")
        cases=tree.findall(".//testcase")
        names={x.attrib["name"].split("(")[0] for x in cases}
        if names!=EXPECTED or len(cases)!=8 or any(list(x) for x in cases):
            raise RuntimeError("original-exact-method-results")
        result.update({"status":"PASS_COMPONENT_ONLY","tests":8,"failures":0,"skips":0,"methods":sorted(names),"sourceManifestSHA256":sha((a.root/"source-before.json").read_bytes()),"originalLogSHA256":sha((a.root/"original.log").read_bytes()),"originalXMLSHA256":sha((a.root/"original.xml").read_bytes())})
    except Exception as e:
        result.update({"error":repr(e),"traceback":traceback.format_exc()})
    finally:
        if process is not None and not absent:
            try:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=10)
                rows=group_present(process.pid); absent=not rows
                cleanup.append({"group":process.pid,"absent":absent,"members":rows})
                if not absent: result["status"]="FAIL"; result["cleanupError"]="owned-group-remains"
            except Exception as e: result["status"]="FAIL"; cleanup.append({"error":repr(e)})
        result["cleanup"]=cleanup; result["elapsed"]=time.monotonic()-begin
        save(a.root/"result.json",result)
    print(json.dumps({k:result.get(k) for k in ["status","tests","failures","skips","error","elapsed"]}))
    return 0 if result["status"]=="PASS_COMPONENT_ONLY" else 1
if __name__=="__main__": raise SystemExit(main())

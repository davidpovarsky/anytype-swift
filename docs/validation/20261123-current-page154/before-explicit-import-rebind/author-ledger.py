"""Author the additive Page154 fixed source ledger without importing repository code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path("/run/anytapy-wave15-source-overlay-20261123/editor")
BASE = "0a80bf7b3c4a77e0048af192d04cf4881ebf0137"
DONOR = "2c9e5152966cdd185b3ceb454bb3a879f244ddf6"
HERE = ROOT / "docs/validation/20261123-current-page154"
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"}
def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], env=ENV)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
def raw(path, origin=BASE): return git("show", origin + ":" + path)
def write(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    with path.open("xb") as output: output.write(data)
    return {"bytes":len(data),"sha256":sha(data)}
def guard(extra):
    used=sum(p.lstat().st_blocks*512 for p in ROOT.rglob("*"))
    available=int(next(v.split()[1] for v in Path("/proc/meminfo").read_text().splitlines()
                       if v.startswith("MemAvailable:")))*1024
    assert used+extra<=8*1024**2 and available>=2*1024**3,(used,available)
    return {"allocated":used,"MemAvailable":available}
before=guard(1024**2)
assert git("rev-parse","HEAD").decode().strip()==BASE
common_path="Tools/CurrentAppleValidation/source-inputs.json"
common_raw=raw(common_path);common=json.loads(common_raw)
assert sha(common_raw)=="b26a0355f040b8a582df7d48c9f22bb7c47cbe33d23760d4e520a569b63d6191"
trees=dict(common["productTrees"]["release-return-rtl"])
for name, expected in trees.items():
    assert git("rev-parse",BASE+":"+name).decode().strip()==expected
overlay_pins={
"Modules/ProtobufMessages/Sources/PinkhaHeartSemanticAnchorApplyObservation.swift":"5d9bc8cad1c6097d73f0aa0b558126ed3782f9c30981bec3b097c6eff10532a9",
"Modules/ProtobufMessages/Sources/PinkhaHeartSemanticAnchorClient.swift":"d0df6073ac0aecaebc421f90ee791c464f0e8cdceded6d7bc27bb8ed279c209d",
"Anytype/Sources/Pinkha/Diagnostics/PinkhaSemanticAnchorMountedObserver.swift":"2ee9939c9c965fbed09e838b6b69eff083902534a74576e21760b578af676d29",
"Anytype/Sources/Pinkha/Editor/PinkhaSemanticAnchorSelectionCoordinator.swift":"072eac6adc455aca045f225d0ac9c7d800cbebc1a0fc9da353ed2cbb2d8eb307",
}
overlays={}
origins={}
for name, expected in overlay_pins.items():
    value=raw(name,DONOR);assert sha(value)==expected
    overlays[name]=("100644",blob(value))
    old=git("ls-tree",BASE,"--",name)
    if old:
        assert raw(name)==raw(name,"b15cd58e376461b066df7fd1639946bb8dca5848")
    origins[name]={"originCommit":DONOR,"sha256":sha(value),"bytes":len(value),
                   "gitBlob":blob(value),"gitMode":"100644",
                   "baseSHA256":sha(raw(name)) if old else None}
fixture="Modules/ProtobufMessages/Tests/ProtobufMessagesTests/PinkhaHeartSemanticAnchorObservationTests.swift"
fixture_path=Path("/run/anytapy-wave15-source-overlay-20261123/sdk-peer-packets/PinkhaHeartSemanticAnchorObservationTests.swift")
fixture_raw=fixture_path.read_bytes()
assert len(fixture_raw)==11311 and sha(fixture_raw)=="12582a1736660f75d0a62820920bfc3095cf2ad8b60ac24412004703bacdd412"
overlays[fixture]=("100644",blob(fixture_raw))
origins[fixture]={"originCommit":DONOR,"baseSHA256":None,
    "donorSHA256":sha(raw(fixture,DONOR)),"sha256":sha(fixture_raw),"bytes":len(fixture_raw),
    "gitBlob":blob(fixture_raw),"gitMode":"100644",
    "reviewedInitializerPatchSHA256":"6c2bd2ba35346d6606cab6189a815ad87c5a53bffe7c995c9dd55a14f18ea9cb",
    "fixtureMethodExecuted":False}
def entries(tree):
    answer={}
    for row in git("ls-tree","-r","-z",BASE+":"+tree).split(b"\0"):
        if not row:continue
        fields,name=row.split(b"\t",1);mode,kind,oid=fields.decode().split()
        assert kind=="blob"
        answer[name.decode()]=(mode,oid)
    return answer
def tree_hash(rows):
    node={}
    for relative,pair in rows.items():
        parts=relative.split("/");at=node
        for name in parts[:-1]:at=at.setdefault(name,{})
        assert parts[-1] not in at
        at[parts[-1]]=pair
    def encode(at):
        output=[]
        for name,value in at.items():
            if isinstance(value,dict):
                mode,oid="40000",encode(value);order=name.encode()+b"/"
            else:
                mode,oid=value;order=name.encode()
            output.append((order,mode.encode()+b" "+name.encode()+b"\0"+bytes.fromhex(oid)))
        data=b"".join(v for _,v in sorted(output))
        return hashlib.sha1(b"tree "+str(len(data)).encode()+b"\0"+data).hexdigest()
    return encode(node)
projection={}
for name in ("Anytype","Modules"):
    rows=entries(name);before_oid=tree_hash(rows);assert before_oid==trees[name]
    selected={p:v for p,v in overlays.items() if p.startswith(name+"/")}
    for path,pair in selected.items(): rows[path[len(name)+1:]]=pair
    after_oid=tree_hash(rows)
    projection[name]={"baseTree":before_oid,"projectedTree":after_oid,"overlayPaths":sorted(selected),
                      "entryCount":len(rows),"algorithm":"Canonical Git tree SHA1, independently reproduces exact base"}
    trees[name]=after_oid
helper_trees=dict(common["helperTrees"])
for p in ("Tools/PinkhaSemanticAnchorWire","docs/validation/20261123-semantic-page-native/attempt6-page-pass"):
    helper_trees[p]=git("rev-parse",BASE+":"+p).decode().strip()
inputs=dict(common["helperInputs"])
def row(path, content=None):
    if content is None:
        content=raw(path)
        meta=git("ls-tree",BASE,"--",path).split(b"\t",1)[0].decode().split()
        assert len(meta)==3 and meta[1]=="blob"
        mode,oid=meta[0],meta[2]
        assert blob(content)==oid
    else:
        mode,oid="100644",blob(content)
    return {"gitMode":mode,"gitBlob":oid,"sha256":sha(content)}
native=json.loads(raw("Tools/PinkhaSemanticAnchorWire/page-source.json"))
extra=[native["qualified139_patch"]]+[v["control_source"] for v in native["files"].values() if "control_source" in v]
extra+=["Tools/PinkhaSimulatorGate/validate_release.py","Tools/PinkhaSimulatorGate/simulator_identity.py",
        "Tools/PinkhaSimulatorGate/compiled_products.py",common_path]
for path in sorted(set(extra)):inputs[path]=row(path)
for path in ("Tools/CurrentAppleValidation/contracts.py","Tools/CurrentAppleValidation/current_execution.py",
             "Tools/CurrentAppleValidation/cleanup_policy.py","Tools/CurrentAppleValidation/native_ui_failed.py",
             "Tools/CurrentAppleValidation/release_return_rtl.py"):
    inputs[path]=row(path)
new_paths=["Tools/CurrentAppleValidation/page154_contract.py","Tools/CurrentAppleValidation/page154_current.py",
           ".github/workflows/pinkha-current-page154-mounted.yml"]
for path in new_paths:inputs[path]=row(path,(ROOT/path).read_bytes())
module_origins=dict(common["moduleOrigins"])
module_origins.update({
"page154_contract":"Tools/CurrentAppleValidation/page154_contract.py",
"page154_current":"Tools/CurrentAppleValidation/page154_current.py",
"consumer_contract":"Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_contract.py",
"consumer_simulator":"Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_simulator.py",
"mounted_contract":"Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_contract.py",
"warning_profile":"Tools/PinkhaSemanticAnchorWire/apple_mounted/warning_profile.py",
"current_page_native_producer":"Tools/PinkhaSemanticAnchorWire/apple_runtime/contract.py",
"rerun_original_ui":"Tools/PinkhaNativeDerived/rerun_original_ui.py",
"run_ui27":"Tools/PinkhaSimulatorGate/run_ui27.py",
})
known=git("ls-tree","-r","--name-only",BASE,"--","Tools").decode().splitlines()
known_set=set(known)|set(new_paths)
directories=["Tools/CurrentAppleValidation","Tools/PinkhaSemanticAnchorWire/apple_mounted",
 "Tools/PinkhaSemanticAnchorWire/apple_consumer","Tools/PinkhaSimulatorGate","Tools/AnyEnginePort",
 "Tools/Hanlin","Tools/PinkhaNativeDerived"]
def imported(nodes):
    result=[]
    for node in nodes:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
        if isinstance(node,ast.If) and ast.unparse(node.test) == "__name__ == '__main__'":continue
        if isinstance(node,ast.Import):result += [item.name.split(".")[0] for item in node.names]
        elif isinstance(node,ast.ImportFrom) and node.level==0:result.append((node.module or "").split(".")[0])
        for key in ("body","orelse","finalbody","handlers"):
            for child in getattr(node,key,[]):
                result+=imported(child.body if isinstance(child,ast.ExceptHandler) else [child])
    return result
scanned={}
pending=list(module_origins)
while pending:
    name=pending.pop(0)
    if name in scanned:continue
    path=module_origins[name]
    content=(ROOT/path).read_bytes() if path in new_paths else raw(path)
    eager=imported(ast.parse(content).body);local={}
    for dependency in eager:
        choices=[folder+"/"+dependency+".py" for folder in directories if folder+"/"+dependency+".py" in known_set]
        if not choices:continue
        target=module_origins.get(dependency,choices[0])
        assert target in choices,(dependency,target,choices)
        if dependency not in module_origins:module_origins[dependency]=target;pending.append(dependency)
        local[dependency]=target
    scanned[name]={"path":path,"sha256":sha(content),"eagerRepositoryImports":local}
for path in set(module_origins.values()):
    if path not in inputs and not any(path==tree or path.startswith(tree+"/") for tree in helper_trees):
        inputs[path]=row(path)
old_ui=json.loads(raw("Tools/PinkhaSemanticAnchorWire/apple_mounted/warning-ui-inputs.json"))
ui_files={}
for path in old_ui["files"]:
    value=raw(path)
    assert sha(value)==old_ui["files"][path]["sha256"]
    ui_files[path]={"bytes":len(value),"sha256":sha(value),"origin":"current-pinned-compiled-tree"}
ui_plan={"schema":"current-page154-ui-copy-v1","files":ui_files,"candidate_ui_sha256":old_ui["candidate_ui_sha256"],
         "generator_path":old_ui["generator_path"],"generator_sha256":old_ui["generator_sha256"],
         "originalImmutableAppReused":False,"originalUIJourneyBytesRetained":True,
         "originalPlanSHA256":sha(raw("Tools/PinkhaSemanticAnchorWire/apple_mounted/warning-ui-inputs.json"))}
preparation="AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
journey="PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
factory="AnytypeTests/SemanticAnchorPage154NativeAcceptanceTests/testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument"
manifest={"schemaVersion":1,"profile":"current-page154-mounted","base":BASE,
 "commonManifestSHA256":sha(common_raw),"productTrees":trees,"helperTrees":helper_trees,
 "inputs":dict(sorted(inputs.items())),"moduleOrigins":dict(sorted(module_origins.items())),
 "selectors":[preparation,journey],"excludedFactory":factory,"freshSetupAcceptanceCredit":0,
 "workflow":new_paths[-1],"projectionOrigins":origins,"uiPlan":ui_plan,
 "native":{"sourceCount":154,"producerRun":"45098093058","producerCommit":"70c6aa3447baae2d8e2681228fb50236c4c60b3b",
  "sourceManifestSHA256":"2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38",
  "runtimeArtifact":14785215179,"runtimeBytes":88589034,
  "runtimeSHA256":"e9b53214ed51e89f55f8bec0a6a53451340e8b974a58a07adbf15a8723152d44",
  "proofArtifact":14784363888,"proofBytes":3058487,
  "proofSHA256":"f5bc7c200e5b9d35f61cc5781877370a135ebb73bccdb5a39349033ea457390d",
  "archiveBytes":88588818,"archiveSHA256":"f698266c8c3cf26a3e2d5939248e2b799623cf9ef5ef944909e98648d1191144",
  "receiptSHA256":"2fe5f2e16d083c1b05ec8297762788edf5d603f95293e87942731693d518cb93"},
 "limits":{"productBuildsExecutedDuringAuthoring":0,"testsExecutedDuringAuthoring":0,
  "runtimeNativeBuilds":0,"runtimeAppBuildsMaximum":1,"runtimeUIBuildsMaximum":1,
  "factoryTests":0,"diagnosticPackageTests":0,"freshSetupNewCredit":0,
  "existingFourMethodPoliciesChanged":False,"currentAppSourceRequired":True,
  "centralWorkflow":"Root-owned inline-job composition, outside this fixed source manifest"}}
guard(512*1024)
written={}
written["manifest"]=write(ROOT/"Tools/CurrentAppleValidation/page154-inputs.json",manifest)
written["projection"]=write(HERE/"source-projection.json",{"base":BASE,"donor":DONOR,"trees":projection,
 "overlays":origins,"treeProjectionOnly":True,"productFilesWrittenOrCompiled":0,
 "commonRuntimeSHA256":inputs["Tools/CurrentAppleValidation/current_execution.py"]["sha256"]})
written["closure"]=write(HERE/"eager-module-closure.json",{"scope":"AST-only static closure; no import/load claim",
 "moduleCount":len(module_origins),"modules":dict(sorted(scanned.items())),
 "helperTrees":helper_trees,"inputRows":len(inputs),"productionImported":False,
 "testModulesImported":False,"fixedCommonRuntime":"f59fbf2bed1f2766111f9103e7b8af4022fb69161afd6d34d1202102228fed7c"})
written["authoring"]=write(HERE/"ledger-authoring.json",{"status":"SOURCE_LEDGER_WRITTEN_NOT_EXECUTED",
 "base":BASE,"outputs":written,"allocationBefore":before,"allocationAfter":guard(0),
 "floorBytes":2*1024**3,"writerCapBytes":8*1024**2,"sourceObjectsWrittenToMnt":0,
 "repositoryImports":0,"hostTests":0,"AppleBuilds":0,"nativeBuilds":0,
 "retainedSourceOnlyRefusals":["JavaScript template syntax refusal before remote execution",
 "read-only SSH BatchMode=yes=yes option refusal before remote execution"],
 "protectedCommonFilesUnchanged":True})
print(json.dumps({"status":"SOURCE_LEDGER_WRITTEN","outputs":written,"inputRows":len(inputs),
 "moduleOrigins":len(module_origins),"projectedTrees":projection,"allocation":guard(0)}))

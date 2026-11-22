import json, hashlib, subprocess, io, zipfile, re, xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter

R=Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
C=R/"docs/pinkha/torah-integration/production-native-metadata-20261122/controls"
E=C/"validation/windows-swift-testing-26"
T=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122")
OUT=T/"metadata26_root_review.json"
B="b854e7f3f59690134bcabdef88527b61517d5ab5"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift"
PRODUCT_SHA="21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5"
PIN="c6fe6442e6a64250495669325044052e113e990c"
def sha(b): return hashlib.sha256(b).hexdigest()
def digest_file(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def git(repo,*args,input=None):
    p=subprocess.run(["git","-c","core.autocrlf=false","-C",str(repo),*args],input=input,capture_output=True,timeout=90)
    if p.returncode: raise RuntimeError((args,p.returncode,p.stderr.decode("utf-8","replace")))
    return p.stdout
def gt(repo,*args): return git(repo,*args).decode("utf-8").strip()
def batch(repo,refs):
    response=git(repo,"cat-file","--batch",input=("\n".join(refs)+"\n").encode())
    stream=io.BytesIO(response); out={}
    for ref in refs:
        header=stream.readline().decode("ascii").strip().split()
        assert len(header)==3 and header[1]=="blob",(ref,header)
        size=int(header[2]); body=stream.read(size)
        assert len(body)==size and stream.read(1)==b"\n"
        out[ref]=(header[0],body)
    assert not stream.read()
    return out
def readj(p): return json.loads(Path(p).read_bytes())
def safe(rel):
    p=PurePosixPath(rel)
    assert not p.is_absolute() and ".." not in p.parts and "\\" not in rel and ":" not in rel
    return p
def check_entry(p,item):
    assert Path(p).is_file() and not Path(p).is_symlink()
    assert Path(p).stat().st_size==item["bytes"] and digest_file(p)==item["sha256"],str(p)

assert not OUT.exists(),"Existing root review must be inspected, not overwritten"
assert gt(R,"rev-parse","HEAD")==B
assert not gt(R,"diff","--name-only") and not gt(R,"diff","--cached","--name-only")
idxraw=(C/"FILE_INDEX.json").read_bytes()
assert sha(idxraw)=="ffac49d17c87592d13594aa6574ae7d8e09609751dac90dfca17d951de8c9d92"
idx=json.loads(idxraw); files=idx["files"]
assert len(files)==69 and sum(x["bytes"] for x in files)==6238298
expected=set()
for row in files:
    safe(row["path"]); assert row["path"] not in expected
    expected.add(row["path"]); check_entry(C/row["path"],row)
actual={p.relative_to(C).as_posix() for p in C.rglob("*") if p.is_file()}
assert actual==expected|{"FILE_INDEX.json"}
product=(R/PRODUCT).read_bytes()
assert len(product)==8112 and sha(product)==PRODUCT_SHA and product.count(b"\r\n")==180
inputs=readj(C/"INPUTS.json"); prep=readj(C/"provenance/DEPENDENCY_PREPARATION.json")
dep=Path(prep["dependency_path"]); used=Path(inputs["execution_harness"])
assert gt(dep,"rev-parse","HEAD")==PIN and gt(dep,"rev-parse","HEAD^{tree}")==prep["dependency_tree"]
assert not gt(dep,"status","--porcelain","--untracked-files=all")
original=[x for x in inputs["source_inputs"] if x["kind"]=="complete_unmodified_original_git_source"]
assert len(original)==3 and len(inputs["source_inputs"])==6
refs=[x["base"]+":"+x["path"] for x in original]+[B+":"+prep["lock_path"]]
blobs=batch(R,refs)
for row in original:
    blob,b=blobs[row["base"]+":"+row["path"]]
    assert blob==row["git_blob"] and len(b)==row["bytes"] and sha(b)==row["sha256"]
    assert b==(C/"harness"/row["retained"]).read_bytes()
lock=blobs[B+":"+prep["lock_path"]][1]
assert sha(lock)==prep["lock_sha256"]=="86546dd98acc5d0414c4c10c0b79f82bda02b06c3687d64481547d9ad0368e5a"
assert lock==(C/"provenance/original-lock.stdout").read_bytes()
pin=[x for x in json.loads(lock)["pins"] if x["identity"]=="swift-protobuf"]
assert pin==[prep["pin_entry"]] and pin[0]["state"]["revision"]==PIN
for row in inputs["source_inputs"]:
    check_entry(C/"harness"/row["retained"],row)
    check_entry(used/row["retained"],row)
assert product==(used/"tests/OriginalAnnotationNativeMetadata.swift").read_bytes()
runtime=readj(C/"provenance/SWIFTPROTOBUF_SOURCE_MANIFEST.json")
assert len(runtime["files"])==100
for row in runtime["files"]: check_entry(dep/row["path"],row)
closure=readj(E/"ACTUAL_BUILD_CLOSURE.json")
rows=closure["files"]
assert len(rows)==162 and len({x["path"].casefold() for x in rows})==162
assert Counter(x["kind"] for x in rows)==Counter({"exact_original_swift_protobuf_dependency":149,"frozen_harness_input":6,"standard_swiftpm_generated_source":7})
deprows=[x for x in rows if x["kind"]=="exact_original_swift_protobuf_dependency"]
deprefs=[PIN+":"+x["relative"] for x in deprows]
depblobs=batch(dep,deprefs)
with zipfile.ZipFile(E/"ACTUAL_BUILD_SOURCE_CLOSURE.zip") as z:
    names=z.namelist()
    assert len(names)==162 and len(set(x.casefold() for x in names))==162 and z.testzip() is None
    assert set(names)=={x["archive_entry"] for x in rows}
    for row in rows:
        safe(row["archive_entry"]); check_entry(row["path"],row)
        b=z.read(row["archive_entry"])
        assert len(b)==row["bytes"] and sha(b)==row["sha256"]
        if row["kind"]=="exact_original_swift_protobuf_dependency":
            blob,original=depblobs[PIN+":"+row["relative"]]
            assert blob==row["git_blob"] and original==b and row["dependency_commit"]==PIN
        elif row["kind"]=="frozen_harness_input":
            assert b==(C/"harness"/row["relative"]).read_bytes()
        else:
            assert Path(row["path"]).is_relative_to(Path(inputs["scratch_path"]))
assert digest_file(E/"ACTUAL_BUILD_SOURCE_CLOSURE.zip")==closure["archive_sha256"]=="9a575832927c1877afdd656d7877053ba9c040e9455d2e44c688a86734a23e08"
desc=readj(E/"build-metadata/x86_64-unknown-windows-msvc/debug/description.json")
assert len(desc["swiftCommands"])==len(closure["swift_compile_commands"])==11
paths={x["path"].casefold() for x in rows}
for command in closure["swift_compile_commands"]:
    actual=desc["swiftCommands"][command["command_key"]]
    assert actual["moduleName"]==command["module_name"] and actual["executable"]==command["executable"]
    assert actual["sources"]==command["sources"] and len(actual["sources"])==command["source_count"]
    assert {s.casefold() for s in actual["sources"]}<=paths
assert desc["pluginDescriptions"]==closure["plugin_descriptions"]
for plugin in desc["pluginDescriptions"]:
    for rel in plugin["sources"]["relativePaths"]:
        assert str(Path(plugin["sources"]["root"])/rel).casefold() in paths
for command in desc.get("copyCommands",{}).values():
    for item in command.get("inputs",[]):
        name=item["name"] if isinstance(item,dict) else item
        if Path(name).is_relative_to(dep) and Path(name).is_file(): assert name.casefold() in paths
execution=readj(E/"EXECUTION.json"); result=readj(E/"RESULT.json")
assert result["status"]=="PASS" and result["actual_swift_test_exit_code"]==0 and not result["timed_out"]
assert execution["exit_code"]==0 and not execution["timed_out"] and execution["source_after_exact"]
assert execution["source_manifest_sha256"]==sha((C/"INPUTS.json").read_bytes())
assert execution["runner_sha256"]==sha((C/"run_controls.py").read_bytes())
for stem in ["stdout","stderr"]: assert digest_file(E/("swift-test."+stem))==execution[stem+"_sha256"]
before=readj(E/"SOURCE_BEFORE.json"); after=readj(E/"SOURCE_AFTER.json")
assert after["exact"] and after["inputs"]==before and after["error"] is None
tests=(C/"harness/tests/MetadataTests.swift").read_text(encoding="utf-8")
names=re.findall(r"@Test\s+func\s+(test\w+)\s*\(",tests)
assert len(names)==len(set(names))==26 and set(names)==set(inputs["test_methods"])
xml=(E/"swift-testing-26.xml").read_bytes()
assert sha(xml)=="ebbd7ebe550e11a433757f477aea8e222e9a3f77459ea52a3e8500972839a041"
cases=ET.fromstring(xml).findall(".//testcase")
assert len(cases)==26
observed=[]
for case in cases:
    matched=[n for n in names if re.search(r"\b"+re.escape(n)+r"\b",case.attrib["name"])]
    assert len(matched)==1 and case.find("failure") is None and case.find("error") is None and case.find("skipped") is None
    observed+=matched
assert Counter(observed)==Counter(names)
rawlog=(E/"swift-test.stdout").read_text(encoding="utf-8")
assert all(re.search(r"\bTest\s+"+re.escape(n)+r"\(\).*?\bpassed\b",rawlog) for n in names)
assert "26 tests in 1 suite passed after 0.113 seconds" in rawlog
binary=readj(E/"BINARY.json")
assert len(binary["files"])==1
br=binary["files"][0];check_entry(br["path"],br)
assert br["sha256"]=="f23a7a5821a9c313f3a5378dd8dede82d35bffd93ca5408d5cc309e384e77b69" and br["bytes"]==11915776
with zipfile.ZipFile(E/"ACTUAL_TEST_BINARY.zip") as z:
    assert len(z.namelist())==1 and z.testzip() is None
    bb=z.read(z.namelist()[0])
    assert bb[:2]==b"MZ" and len(bb)==br["bytes"] and sha(bb)==br["sha256"]
assert digest_file(E/"ACTUAL_TEST_BINARY.zip")==binary["archive_sha256"]
toolchain=readj(E/"TOOLCHAIN_FILES.json")["files"]
assert len(toolchain)==15
for row in toolchain: check_entry(row["path"],row)
assert digest_file(execution["args"][0])==execution["compiler_sha256"]
diagnostics=readj(E/"DIAGNOSTIC_AND_TIMING_REVIEW.json")
assert not diagnostics["errors"] and not diagnostics["production_source_diagnostics"]
assert len(diagnostics["source_diagnostics"])==1 and "MetadataTests.swift:384:50:" in diagnostics["source_diagnostics"][0]
assert diagnostics["source_diagnostics"][0] in (E/"swift-test.stderr").read_text(encoding="utf-8")
assert not gt(dep,"status","--porcelain","--untracked-files=all")
script=Path(__file__).read_bytes();(T/"metadata26_root_review.py").write_bytes(script)
receipt={"schema_version":1,"status":"PASS_INDEPENDENT_SOURCE_ARTIFACT_REVIEW_NO_TEST_RERUN","at":datetime.now(timezone.utc).isoformat(),
"source_base":B,"product_path":PRODUCT,"product_sha256":PRODUCT_SHA,"product_bytes":len(product),"product_line_endings_preserved":"CRLF",
"controls_index_sha256":sha(idxraw),"indexed_payloads_verified":69,"payload_bytes":6238298,"indexes_also_verified":1,
"canonical_original_Git_blobs_verified":4,"original_full_source_files":3,"frozen_harness_inputs_verified":6,"actual_harness_copies_verified":6,
"dependency_revision":PIN,"dependency_Git_blobs_verified":149,"initial_runtime_manifest_files_verified":100,"actual_build_closure_files_verified":162,
"actual_build_swift_commands_verified":11,"plugin_descriptions_verified":1,"toolchain_files_verified":15,
"actual_tests":26,"failures":0,"skipped":0,"xunit_sha256":sha(xml),"binary_sha256":br["sha256"],
"result_sha256":digest_file(E/"RESULT.json"),"execution_sha256":digest_file(E/"EXECUTION.json"),"root_review_script_sha256":sha(script),
"actual_swift_testing_seconds":0.113,"old_tests_reexecuted":0,"new_tests_executed_by_review":0,
"fixture_warning_retained":True,"production_diagnostics":0,
"scope":["Exact portable metadata decoding using genuine SwiftProtobuf and original selected DTOs/generated enum.","No full Apple app or complete PinkhaKit/ProtobufMessages package qualification.","No native schema registration, ObjectShow integration, identity/body receipt, mapping writer or ACK."]}
OUT.write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
print(json.dumps({"review":str(OUT),"sha256":digest_file(OUT),**receipt}),flush=True)

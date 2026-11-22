from pathlib import Path
import json,hashlib,zipfile,struct,re,datetime,shutil
p=Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122\evidence-ready-v2")
execution_root=p.parent
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-actual-root-review")
out.mkdir(parents=True,exist_ok=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def check_file(rel,digest,size=None):
 raw=(p/rel).read_bytes()
 assert sha(raw)==digest,(rel,"sha256")
 if size is not None:assert len(raw)==size,(rel,"bytes")
 return raw
indexraw=check_file("INDEX.json","1c4bc8643d8f32556a87edcb88f8fec9a73804cce64e2dc0b3459e99312f39f6")
idx=json.loads(indexraw);rows=idx["files"]
assert len(rows)==idx["count"]==91
paths=[x["path"] for x in rows]
assert len(set(paths))==91
assert sorted(paths)==sorted(x.relative_to(p).as_posix() for x in p.rglob("*") if x.is_file() and x.name!="INDEX.json")
for item in rows:
 assert not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts
 check_file(item["path"],item["sha256"],item["bytes"])
oldraw=check_file("history/INDEX-88127b17.json","88127b17608f0e877f9f33f8e2fed9a9f25329d47f7902bb56e80b5c721473bb")
old=json.loads(oldraw);assert len(old["files"])==85
for item in old["files"]:
 check_file(item["path"],item["sha256"],item["bytes"])
 assert (p.parent/"evidence-ready"/item["path"]).read_bytes()==(p/item["path"]).read_bytes()
assert (p.parent/"evidence-ready"/"INDEX.json").read_bytes()==oldraw
corrected=json.loads(check_file("CORRECTED_RESULT.json","1299b391644755a586e9481398ff303a464d82f60f88dabe7354f338c3d67cb7"))
inputs=json.loads(check_file("INPUTS.json","ef6b5d2758ad78da46e6c152f16d41f050ff478832b41e0cb4db618ed53b0f69"))
check_file("root-final-controls-review.json","86fe254ec7f4aac95b54c40e1a9df61f8a0e29f2a1947366248faad2d4fe2e97")
runner=check_file("run_controls.py","fa38adc2e3a99268b83341070812a1bc5bf21ed3f0c17a87084b28010c78747d").decode("utf-8")
assert 'assert not (out/"EXECUTION.json").exists()' in runner
assert 'assert binary.name in (out/"swift-testing-selected-space.stdout.log")' in runner
assert len(inputs["compiled_inputs"])==17 and len(inputs["original_inputs"])==23
for item in inputs["compiled_inputs"]:check_file(item["path"],item["sha256"],item["bytes"])
for item in inputs["original_inputs"]:check_file(item["saved_path"],item["sha256"],item["bytes"])
for key in ["package","projection_map","preparation","fixture_revision"]:
 x=inputs[key];check_file(x["path"],x["sha256"],x["bytes"])
candidates=inputs["product_candidates"]
assert [x["canonical_sha256"] for x in candidates]==["bf33794809bff676321ae0265e0caf6539fd7feaa69edaf4d14829753c131ac1","284c09888c8cf75b2fa54a0f529e0ac6401fbc9ba9c9a923973edaaace061c21"]
for x in candidates:check_file(x["saved_path"],x["canonical_sha256"],x["canonical_bytes"])
generated=json.loads((p/"GENERATED_SWIFTPM_INPUTS.json").read_bytes())
assert len(generated)==3
for x in generated:check_file(x["path"],x["sha256"],x["bytes"])
e=json.loads((p/"EXECUTION.json").read_bytes());start=json.loads((p/"ACTUAL_STARTED.json").read_bytes())
assert e["input_sha256"]==start["input_sha256"]==sha((p/"INPUTS.json").read_bytes())
assert e["runner_sha256"]==start["runner_sha256"]==sha((p/"run_controls.py").read_bytes())
assert start["root_review_sha256"]=="86fe254ec7f4aac95b54c40e1a9df61f8a0e29f2a1947366248faad2d4fe2e97"
assert len(e["commands"])==4
assert [c["label"] for c in e["commands"]]==["swift-version","actual-manager-syntax","actual-service-syntax","swift-testing-selected-space"]
for c in e["commands"]:
 assert c["phase"]=="TERMINAL" and c["returncode"]==0 and not c["timed_out"] and c["child_pid"]>0 and c["all_inputs_unchanged"]
 assert datetime.datetime.fromisoformat(c["finished_at"])>=datetime.datetime.fromisoformat(c["started_at"])
 for stream in ["stdout","stderr"]:check_file(c["label"]+"."+stream+".log",c[stream+"_sha256"],c[stream+"_bytes"])
for x in e["toolchain"]:
 raw=Path(x["path"]).read_bytes();assert sha(raw)==x["sha256"] and len(raw)==x["bytes"]
cmd=e["commands"][-1]
assert cmd["command"][1:3]==["test","--verbose"]
assert "--enable-swift-testing" in cmd["command"] and "--disable-xctest" in cmd["command"]
assert cmd["command"][cmd["command"].index("--xunit-output")+1]==str(execution_root/"TEST_RESULTS.xml")
assert cmd["command"][-2:]==["-Xswiftc","-strict-concurrency=complete"]
xml=check_file("TEST_RESULTS.xml","008d5489b07d8be7e4634ca3b8f945fd0686e24ff43f4289eb13cdcce19d44d5",1870)
assert (execution_root/"TEST_RESULTS.xml").read_bytes()==xml
observed_xml_mtime=datetime.datetime.fromtimestamp((execution_root/"TEST_RESULTS.xml").stat().st_mtime,datetime.timezone.utc)
assert datetime.datetime.fromisoformat(cmd["started_at"])<=observed_xml_mtime<=datetime.datetime.fromisoformat(cmd["finished_at"])
import xml.etree.ElementTree as ET
tree=ET.fromstring(xml);cases=tree.findall(".//testcase")
names=sorted(x.attrib["name"].removesuffix("()") for x in cases)
assert len(cases)==10 and names==sorted(inputs["expected_tests"])
assert not any(tree.findall(".//"+kind) for kind in ["failure","error","skipped"])
suite=tree.find("testsuite")
assert suite.attrib["tests"]=="10" and all(suite.attrib[x]=="0" for x in ["failures","errors","skipped"])
stdout=(p/"swift-testing-selected-space.stdout.log").read_text(encoding="utf-8")
assert sorted(re.findall(r"Test (\w+)\(\) passed after",stdout))==names
assert "Test run with 10 tests in 1 suite passed" in stdout
stderr=(p/"swift-testing-selected-space.stderr.log").read_text(encoding="utf-8")
assert "Build complete!" in stderr
assert all(Path(x["path"]).name in stderr for x in inputs["compiled_inputs"])
with zipfile.ZipFile(p/"emitted-linked-test-binary.zip") as z:
 assert z.testzip() is None and z.namelist()==["OriginalSelectedSpacePackageTests.xctest"]
 binary=z.read(z.namelist()[0])
assert sha(binary)=="456cde35061b5f6e3d5fcdad9fe403133affc8b08b255ba091495fd8cda23a05" and len(binary)==3975168
assert binary[:2]==b"MZ"
pe=struct.unpack_from("<I",binary,0x3c)[0]
assert binary[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",binary,pe+4)[0]==0x8664
assert corrected["emitted_linked_binary"]["independent_os_child_process_identity_observed"] is False
first=(p/"SENTINEL_FIRST_WRAPPER_RESULT.json").read_text(encoding="utf-8")
assert "AssertionError" in first and "assert binary.name" in first
assert corrected["evidence_continuation"]["compilers_or_tests_invoked"]==0
assert corrected["evidence_continuation"]["prior_tests_replayed"] is False
shutil.copyfile(__file__,out/"root_review.py")
result={"schema":"otzaria.selected-space-actual-root-review/1","status":"PASS_FOR_CANONICAL_SOURCE_INTEGRATION","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "packet":str(p),"packet_index_sha256":sha(indexraw),"payloads_verified":len(rows),"total_payload_bytes":sum(x["bytes"] for x in rows),
 "prior85_payloads_and_index_unchanged":True,"root_control_review_sha256":start["root_review_sha256"],
 "input_sha256":e["input_sha256"],"runner_sha256":e["runner_sha256"],"compiled_inputs_verified":17,"original_inputs_retained_matching_prior_root_git_review":23,"generated_swiftpm_inputs_verified":3,
 "commands":[{"label":c["label"],"child_pid":c["child_pid"],"returncode":c["returncode"],"timed_out":c["timed_out"],"started_at":c["started_at"],"finished_at":c["finished_at"]} for c in e["commands"]],
 "actual_named_tests_passed":names,"xunit_sha256":sha(xml),"observed_original_xunit_mtime_utc":observed_xml_mtime.isoformat(),"exact_fresh_xml_and_stdout_agree":True,
 "first_post_test_wrapper_failure_preserved":True,"original_red_runner_unchanged":True,"evidence_only_addition":True,"compiled_or_tests_reexecuted_by_root":0,
 "emitted_linked_binary":{"sha256":sha(binary),"bytes":len(binary),"format":"PE32+ x86_64","independent_child_process_identity_observed":False},
 "canonical_product_candidates":[{"path":x["product_path"],"sha256":x["canonical_sha256"],"bytes":x["canonical_bytes"]} for x in candidates],
 "limits":corrected["limits"]}
raw=(json.dumps(result,ensure_ascii=True,indent=2)+"\n").encode("utf-8");(out/"ROOT_REVIEW.json").write_bytes(raw)
print(json.dumps({"status":result["status"],"path":str(out/"ROOT_REVIEW.json"),"sha256":sha(raw),"payloads":91,"prior_payloads":85,"actual_commands":4,"actual_tests":10,"no_execution_replayed":True,"observed_at":result["observed_at"]}))

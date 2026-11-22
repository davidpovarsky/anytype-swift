import pathlib,json,hashlib,zipfile,shutil,datetime,xml.etree.ElementTree as ET,struct
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
proof=out/"evidence-ready"
assert not proof.exists(),"Review packet already prepared"
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(data.encode() if isinstance(data,str) else data)
def rec(path,base=out):
 raw=path.read_bytes();return {"path":path.relative_to(base).as_posix(),"bytes":len(raw),"sha256":sha(raw)}
inputs=json.loads((out/"INPUTS.json").read_bytes())
assert sha((out/"INPUTS.json").read_bytes())=="ef6b5d2758ad78da46e6c152f16d41f050ff478832b41e0cb4db618ed53b0f69"
execution=json.loads((out/"EXECUTION.json").read_bytes())
assert execution["runner_sha256"]=="fa38adc2e3a99268b83341070812a1bc5bf21ed3f0c17a87084b28010c78747d"
assert [x["label"] for x in execution["commands"]]==["swift-version","actual-manager-syntax","actual-service-syntax","swift-testing-selected-space"]
assert all(x["returncode"]==0 and x["timed_out"] is False and x["all_inputs_unchanged"] is True for x in execution["commands"])
for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"]
for item in inputs["original_inputs"]:assert sha((out/item["saved_path"]).read_bytes())==item["sha256"]
for item in inputs["product_candidates"]:assert sha((out/item["saved_path"]).read_bytes())==item["canonical_sha256"]
for command in execution["commands"]:
 for stream in ("stdout","stderr"):assert sha((out/(command["label"]+"."+stream+".log")).read_bytes())==command[stream+"_sha256"]
job={"ok":True,"job":{"id":"job_5c9fd5c1bbf1","type":"job_result","source":"script_run@host_7ec8382e82747448","severity":"warning","tool":"script_run","host":"host_7ec8382e82747448","status":"failed","exit_code":1,"created_at":1795342303.853993,"started_at":"2026-11-22T10:11:43.896064+00:00","finished_at":"2026-11-22T10:16:39.010249+00:00","duration_s":295.11,"error":None,"output_truncated":False,"timeout_s":1500,"read":False,"notified":{"telegram":None,"resend":None},"notify_spec":{},"output":"Traceback (most recent call last):\r\n  File \"C:\\ProgramData\\SentinelX\\uploads\\.sentinelx_uploads\\script_job_fd1b6a84998e4aa6af6d255031ef9116\\script.py\", line 10, in <module>\r\n    runpy.run_path(str(out/\"run_controls.py\"),run_name=\"__main__\")\r\n  File \"<frozen runpy>\", line 286, in run_path\r\n  File \"<frozen runpy>\", line 98, in _run_module_code\r\n  File \"<frozen runpy>\", line 88, in _run_code\r\n  File \"C:\\Users\\DAVID\\AppData\\Local\\Temp\\oe-selected-final-20261122\\run_controls.py\", line 86, in <module>\r\n    assert binary.name in (out/\"swift-testing-selected-space.stdout.log\").read_text(encoding=\"utf-8\",errors=\"replace\")\r\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\r\nAssertionError"}}
assert job["job"]["id"]=="job_5c9fd5c1bbf1" and job["job"]["status"]=="failed" and job["job"]["exit_code"]==1
assert "assert binary.name in" in job["job"]["output"] and "AssertionError" in job["job"]["output"]
xml=out/"TEST_RESULTS.xml"
cases=ET.parse(xml).findall(".//testcase")
assert len(cases)==10
assert sorted(x.attrib["name"].removesuffix("()") for x in cases)==sorted(inputs["expected_tests"])
assert all(not x.findall("failure") and not x.findall("error") and not x.findall("skipped") for x in cases)
native=next(x for x in execution["commands"] if x["label"]=="swift-testing-selected-space")
started=datetime.datetime.fromisoformat(native["started_at"]).timestamp()
finished=datetime.datetime.fromisoformat(native["finished_at"]).timestamp()
assert int(started)-1<=xml.stat().st_mtime<=finished+1
stdout=(out/"swift-testing-selected-space.stdout.log").read_text(encoding="utf-8")
assert "Test run with 10 tests in 1 suite passed" in stdout
for name in inputs["expected_tests"]:assert "Test "+name+"() passed" in stdout
binaries=list((out/".build").rglob("OriginalSelectedSpacePackageTests.xctest"));assert len(binaries)==1
binary=binaries[0];raw=binary.read_bytes()
assert sha(raw)=="456cde35061b5f6e3d5fcdad9fe403133affc8b08b255ba091495fd8cda23a05" and len(raw)==3975168
pe=struct.unpack_from("<I",raw,0x3c)[0]
assert raw[:2]==b"MZ" and raw[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",raw,pe+4)[0]==0x8664
assert binary.name not in stdout
stderr=(out/"swift-testing-selected-space.stderr.log").read_text(encoding="utf-8")
assert binary.name in stderr and "-emit-executable" in stderr
assert "--testing-library" not in stdout+stderr
report={
 "schema":"original-selected-space-corrected-report/v1",
 "status":"ACTUAL_SWIFT_TEST_TEN_PASS_WITH_PRESERVED_REPORTING_WRAPPER_FAILURE",
 "actual_child_command_count":4,"all_actual_child_commands_exit_zero_without_timeout":True,
 "tests_run":10,"tests":[x.attrib for x in cases],"fresh_xunit":rec(xml),
 "input_manifest":rec(out/"INPUTS.json"),"actual_runner":rec(out/"run_controls.py"),
 "all17_compiled_inputs_unchanged":True,"canonical_candidates":inputs["product_candidates"],
 "emitted_linked_binary":{**rec(binary),"format":"PE32+ x86_64","independent_os_child_process_identity_observed":False},
 "wrapper_failure":{"stage":"Post-test report assertion","condition":"binary basename was expected in stdout","actual":"SwiftPM placed emitted binary/link commands in stderr; no separately printed child executable invocation or child PID was observed","original_runner_and_traceback_preserved":True},
 "evidence_continuation":{"compilers_or_tests_invoked":0,"prior_tests_replayed":False,"basis":"Existing exact swift test argv/exit, fresh named XML and matching Swift Testing stdout, immutable source inputs and emitted linked PE; linker text is not OS execution proof"},
 "product_applied":False,"native_calls":0,"limits":inputs["limits"]
}
write(out/"CORRECTED_RESULT.json",json.dumps(report,indent=2)+"\n")
write(out/"SENTINEL_FIRST_WRAPPER_RESULT.json",json.dumps(job,indent=2)+"\n")
write(out/"report_existing_results.py",pathlib.Path(__file__).read_bytes())
proof.mkdir();write(proof/".gitattributes","* -text\n")
for path in out.iterdir():
 if path.is_file() and path.suffix.lower() in (".json",".py",".patch",".md",".txt",".log"):
  shutil.copyfile(path,proof/path.name)
for dirname in ("Tests","original-inputs","product-inputs"):
 shutil.copytree(out/dirname,proof/dirname)
generated=[]
for path in sorted((out/".build").rglob("*.swift")):
 if ".derived" in str(path.parent):
  target=proof/"generated-swiftpm"/path.relative_to(out/".build")
  write(target,path.read_bytes());generated.append(rec(target,proof))
write(proof/"GENERATED_SWIFTPM_INPUTS.json",json.dumps(generated,indent=2)+"\n")
with zipfile.ZipFile(proof/"emitted-linked-test-binary.zip","x",compression=zipfile.ZIP_DEFLATED) as z:z.write(binary,binary.name)
for label,path in [("v1-unexecuted",pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-20261122")),("counter-only-v2-unexecuted",pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-v2-20261122"))]:
 assert not (path/"EXECUTION.json").exists() and not (path/".build").exists()
 with zipfile.ZipFile(proof/(label+".zip"),"x",compression=zipfile.ZIP_DEFLATED) as z:
  for member in sorted(path.rglob("*")):
   if member.is_file():z.write(member,member.relative_to(path).as_posix())
reviews=[
 (pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-final-controls-review\ROOT_REVIEW.json"),"root-final-controls-review.json","86fe254ec7f4aac95b54c40e1a9df61f8a0e29f2a1947366248faad2d4fe2e97"),
 (pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-selected-space-queued-rpc-independent-review-20261122.json"),"native-queued-rpc-review.json","67ff1ce6f57470d7b0a3de7c9a682b55f74612d1550faf82fe1bce37e3b4052b"),
 (pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-space-lifecycle-independent-review-20261122.json"),"native-manager-lifecycle-review.json","158852694614d18bb888b9c28ab8a7a5b8ed7089a94b5f0e89ba5d19c1eb3cbb"),
 (pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-space-dependency-lifecycle-independent-review-20261122.json"),"native-dependency-lifecycle-review.json","3346ec0d9f61075aa9a69447024939368f5621fce4e5b7af2e1dce4853a22bf6")
]
for path,name,expected in reviews:
 assert sha(path.read_bytes())==expected
 shutil.copyfile(path,proof/name)
readme="# Original selected-Space prerequisite — actual portable component evidence\n\nThe exact canonical manager bf337948 and closed Services boundary 284c0988 were independently reviewed and have not yet been applied to product source. This packet binds 23 immutable original files and 17 compiled inputs. It retains the full original AccountInfo model/decoder, original owner/account/lifetime/operation/dispatch bodies and original SpaceViews callback actor through the explicitly mapped portable closure.\n\nThe actual first execution ran four commands, all exit0 without timeout: toolchain version, full manager parse, full Services parse and one genuine serialized Swift Testing suite. The ten new named groups passed; the fresh xUnit and matching stdout are retained. No old assertion suite was replayed.\n\nThe outer reporting wrapper then failed because it required the emitted binary basename in stdout. SwiftPM printed compilation/link information in stderr and did not separately print a child executable invocation or PID. The unchanged original runner and complete Sentinel traceback remain RED. The evidence-only continuation invokes no compiler/test: it binds the actual swift test argv/exit, fresh XML/named stdout results, immutable source closure and emitted/linked PE artifact. The PE hash is not presented as independent OS child-process identity proof.\n\nThe manager projection removes four imports, adds five read-only test accessors and one counter at the actual duplicate-stop branch before its original await. Exact inversion recovers canonical product bytes. The counter proves the second stop reached that branch before the first clear is released. Fixture cleanup checks all recorded assertions after manager/Space teardown; no fixture erases them. The two earlier unexecuted fixture revisions are retained.\n\nThe closed Services projection retains the original final class, exact original workspaceOpen method and new static extension/error, with unrelated methods omitted. ClientCommands/native values, Combine/DI/subscription/decoded values and shared provider operations are explicit probes. Original permit preparation/admission/completion code executes on the queued boundary, including held completion. The tests do not execute original native Invocation, Go, protobuf decoding, actual Apple frameworks or native UI. They do not prove widget/type/property readiness or native child shutdown. No destination factory, annotation receipt, create/schema operation, identity writer or ACK is enabled.\n\nThe original b19 proposal's protocol-returned DTO gap was rejected before execution. The reviewed closed final service boundary is the only selected source candidate in these controls. Production account bootstrap and AuthService ordering remain separate required work; fixture account opening is not such a bootstrap.\n"
write(proof/"README.md",readme)
files=[rec(p,proof) for p in sorted(proof.rglob("*")) if p.is_file()]
write(proof/"INDEX.json",json.dumps({"schema":1,"files":files,"count":len(files),"index_excludes_itself":True},indent=2)+"\n")
print(json.dumps({"status":"FROZEN_CORRECTED_EVIDENCE_NO_REEXECUTION","proof":str(proof),"corrected_result_sha256":sha((proof/"CORRECTED_RESULT.json").read_bytes()),"index_sha256":sha((proof/"INDEX.json").read_bytes()),"payload_count":len(files),"actual_swift_testing_passed":10,"actual_wrapper_status":"FAILED_REPORT_ASSERTION_PRESERVED","new_execution_count":0,"source_applied":False}))

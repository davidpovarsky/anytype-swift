import pathlib,json,hashlib,struct,xml.etree.ElementTree as ET
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-space-bind-20261122")
def sha(data):return hashlib.sha256(data).hexdigest()
assert not (out/"RESULT.json").exists()
inputs=json.loads((out/"INPUTS.json").read_bytes())
assert sha((out/"INPUTS.json").read_bytes())=="74a0bf1c732e7d579814c4658d1f718e3c476b0d817fbf1871c481fc490f3d07"
execution=json.loads((out/"EXECUTION.json").read_bytes())
assert all(x["phase"]=="TERMINAL" and x["returncode"]==0 and not x["timed_out"] and x["all_inputs_unchanged"] for x in execution["commands"])
for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"]
for item in inputs["original_inputs"]:assert sha((out/"original"/item["path"]).read_bytes())==item["sha256"]
assert sha((out/"Package.swift").read_bytes())==inputs["package_sha256"]
for cmd in execution["commands"]:
 for stream in ("stdout","stderr"):
  assert sha((out/(cmd["label"]+"."+stream+".log")).read_bytes())==cmd[stream+"_sha256"]
xml=out/"TEST_RESULTS.xml";cases=ET.parse(xml).findall(".//testcase")
assert len(cases)==10
assert sorted(c.attrib["name"].removesuffix("()") for c in cases)==sorted(inputs["expected_tests"])
assert all(not list(c) for c in cases)
binaries=list((out/".build").rglob("OriginalSpaceEditCompositionPackageTests.xctest"));assert len(binaries)==1
binary=binaries[0];data=binary.read_bytes();assert data[:2]==b"MZ"
offset=struct.unpack_from("<I",data,0x3c)[0];assert data[offset:offset+4]==b"PE\0\0";assert struct.unpack_from("<H",data,offset+4)[0]==0x8664
stdout=(out/"swift-testing-composition.stdout.log").read_text(encoding="utf-8",errors="replace")
stderr=(out/"swift-testing-composition.stderr.log").read_text(encoding="utf-8",errors="replace")
assert binary.name not in stdout and binary.name in stderr
assert str(binary) in stderr and "-o "+str(binary) in stderr
assert "Test run with 10 tests in 1 suite passed" in stdout
assert "Testing Library Version: 6.3.3" in stdout
receipt=json.loads("{\"id\":\"job_3dac0ed96ee4\",\"type\":\"job_result\",\"source\":\"script_run@host_7ec8382e82747448\",\"severity\":\"warning\",\"tool\":\"script_run\",\"host\":\"host_7ec8382e82747448\",\"status\":\"failed\",\"exit_code\":1,\"created_at\":1795332997.205468,\"started_at\":\"2026-11-22T07:36:37.308712+00:00\",\"finished_at\":\"2026-11-22T07:41:33.921638+00:00\",\"duration_s\":296.61,\"error\":null,\"output_truncated\":false,\"timeout_s\":1000,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_f5f863be96ab4356a7d17068104c8153\\\\script.py\\\", line 55, in <module>\\r\\n    assert binary.name in (out/\\\"swift-testing-composition.stdout.log\\\").read_text(encoding=\\\"utf-8\\\",errors=\\\"replace\\\")\\r\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\nAssertionError\"}")
(out/"ORIGINAL_TOOL_RED.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
erratum={"schema":1,"original_job":"job_3dac0ed96ee4","original_tool_status":"failed","actual_process_exit":0,"actual_tests":10,"actual_failures":0,"packaging_assertion":"binary.name in swift-testing-composition.stdout.log","observed":"SwiftPM emitted the actual Windows .xctest link command to stderr; stdout contains genuine Swift Testing case results.","correction":"Read the existing immutable stderr link command as well as stdout and verify exact PE x86_64 binary/path. No compiler, test, source, input or assertion rerun.","reexecuted_commands":0}
(out/"EVIDENCE_STREAM_ERRATUM.json").write_text(json.dumps(erratum,indent=2)+"\n",encoding="utf-8")
result={"schema":1,"status":"PASS_TEN_NEW_COMPOSED_BOUNDARY_GROUPS","tests_run":10,"tests":[c.attrib for c in cases],"toolchain":(out/"swift-version.stdout.log").read_text(),"inputs_sha256":sha((out/"INPUTS.json").read_bytes()),"candidate_sha256":inputs["candidate_sha256"],"xunit_sha256":sha(xml.read_bytes()),"binary":{"path":str(binary.relative_to(out)),"sha256":sha(data),"bytes":len(data),"format":"PE32+ x86_64 Windows test runner with .xctest filename"},"all_inputs_unchanged":True,"evidence_stream_erratum_sha256":sha((out/"EVIDENCE_STREAM_ERRATUM.json").read_bytes()),"limits":inputs["limits"]}
(out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
(out/"complete_evidence_without_execution.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({"status":result["status"],"result_sha256":sha((out/"RESULT.json").read_bytes()),"tests_run":10,"xunit_sha256":result["xunit_sha256"],"binary":result["binary"],"erratum_sha256":result["evidence_stream_erratum_sha256"],"no_commands_reexecuted":True,"warning_count":stderr.count("warning:")}))

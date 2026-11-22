import pathlib,json,hashlib,struct,xml.etree.ElementTree as ET
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
assert not (out/"VALIDATION_RESULT.json").exists()
commands=json.loads((out/"VALIDATION_EXECUTION.json").read_bytes())
assert len(commands)==3 and all(x["phase"]=="TERMINAL" and x["returncode"]==0 and not x["timed_out"] for x in commands)
for command in commands:
 for stream in ["stdout","stderr"]:
  assert hashlib.sha256((out/(command["label"]+"."+stream+".log")).read_bytes()).hexdigest()==command[stream+"_sha256"]
inputs=json.loads((out/"BOUNDARY_INPUTS.json").read_bytes())
for item in inputs["candidates"]:assert hashlib.sha256((out/(pathlib.Path(item["path"]).stem+".candidate.swift")).read_bytes()).hexdigest()==item["candidate_sha256"]
probe=out/"boundary-package/Tests/OriginalBoundaryProbes/BoundaryProbes.swift"
assert hashlib.sha256(probe.read_bytes()).hexdigest()==inputs["probe_sha256"]
assert hashlib.sha256((out/"CANDIDATE_PROVENANCE.json").read_bytes()).hexdigest()==inputs["candidate_provenance_sha256"]
xml=out/"BOUNDARY_TEST_RESULTS.xml";root=ET.parse(xml)
cases=root.findall(".//testcase")
expected={"exactMovePrefixUsesCapturedScopeOnMainActor()","exactPublicationTypeRetainsDeferredGateAndThrow()","deferredPreparationAtExactlyFiveSites()"}
assert len(cases)==3 and {x.attrib["name"] for x in cases}==expected
assert all(not c.findall("failure") and not c.findall("error") and not c.findall("skipped") for c in cases)
suite=root.find(".//testsuite");assert suite.attrib["tests"]=="3" and suite.attrib["failures"]=="0" and suite.attrib["errors"]=="0" and suite.attrib["skipped"]=="0"
binary=out/"boundary-package/.build/x86_64-unknown-windows-msvc/debug/OriginalSettingsMoveBoundaryPackageTests.xctest"
data=binary.read_bytes()
assert data[:2]==b"MZ"
offset=struct.unpack_from("<I",data,0x3c)[0]
assert data[offset:offset+4]==b"PE\0\0" and struct.unpack_from("<H",data,offset+4)[0]==0x8664
verbose=(out/"swift-testing-boundaries.stderr.log").read_text(encoding="utf-8")
assert binary.name in verbose
assert "Testing-6.3.3" in verbose and "TestingMacros" in verbose or "SwiftInProcPluginServer" in verbose
first=json.loads("{\"id\":\"job_f2a2a022aeae\",\"type\":\"job_result\",\"source\":\"script_run@host_7ec8382e82747448\",\"severity\":\"warning\",\"tool\":\"script_run\",\"host\":\"host_7ec8382e82747448\",\"status\":\"failed\",\"exit_code\":1,\"created_at\":1795331603.6217675,\"started_at\":\"2026-11-22T07:13:23.709464+00:00\",\"finished_at\":\"2026-11-22T07:18:06.800221+00:00\",\"duration_s\":283.09,\"error\":null,\"output_truncated\":false,\"timeout_s\":900,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_fc5777b80f3f4754bb66e8476f60b3f4\\\\script.py\\\", line 57, in <module>\\r\\n    assert binary_records,\\\"Missing actual generated test runner\\\"\\r\\n           ^^^^^^^^^^^^^^\\r\\nAssertionError: Missing actual generated test runner\"}")
assert first["status"]=="failed" and first["exit_code"]==1 and "Missing actual generated test runner" in first["output"]
(out/"FIRST_VALIDATION_TOOL_RESULT.json").write_text(json.dumps(first,indent=2)+"\n",encoding="utf-8")
erratum={"schema":1,"status":"EVIDENCE_GLOB_CORRECTION_WITHOUT_REPLAY","original_tool_job":first["id"],"original_tool_exit":1,"all_original_commands_terminal_exit_zero":True,"original_parse_invocations":1,"original_swift_testing_invocations":1,"test_replays":0,"cause":"The original evidence-only glob selected *.exe, but SwiftPM emitted a PE x86_64 executable with .xctest extension.","actual_runner":str(binary.relative_to(out)),"pe_machine":"x86_64","runner_sha256":hashlib.sha256(data).hexdigest(),"unchanged_candidate_and_probe_inputs":True}
(out/"EVIDENCE_GLOB_ERRATUM.json").write_text(json.dumps(erratum,indent=2)+"\n",encoding="utf-8")
result={"schema":1,"status":"PASS_THREE_CHANGED_SYNTAX_AND_THREE_EXTRACTED_SWIFT_TESTING_BOUNDARIES","tests_run":3,"tests":[c.attrib for c in cases],"toolchain":(out/"swift-version.stdout.log").read_text(encoding="utf-8"),"testing_runtime_output":(out/"swift-testing-boundaries.stdout.log").read_text(encoding="utf-8"),"probe_sha256":inputs["probe_sha256"],"candidate_provenance_sha256":inputs["candidate_provenance_sha256"],"xunit_sha256":hashlib.sha256(xml.read_bytes()).hexdigest(),"binaries":[{"path":str(binary.relative_to(out)),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}],"limits":inputs["limits"],"postprocessing_erratum":erratum}
(out/"VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":result["status"],"tests_run":3,"xunit_sha256":result["xunit_sha256"],"binaries":result["binaries"],"result_sha256":hashlib.sha256((out/"VALIDATION_RESULT.json").read_bytes()).hexdigest(),"erratum":erratum}))

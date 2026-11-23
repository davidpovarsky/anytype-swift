#!/usr/bin/env python3
"""Offline collector regression using the authenticated, unchanged native artifact."""
import ast, hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, textwrap, zipfile
sys.dont_write_bytecode=True
PACKET="docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
# Locate this packet without depending on a caller working directory.
PACKET_ROOT=pathlib.Path(__file__).resolve().parents[2]
DRIVER=PACKET_ROOT/"slice-a/run_native_archive.py"
EVIDENCE=PACKET_ROOT/"slice-a/run-45139622096"
BASE="2da5419fa8b3e90ecca248ee9c83fd5055d8bca6"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value,reason):
    if not value: raise AssertionError(reason)
raw=(EVIDENCE/"original-native-archive.zip").read_bytes()
require(sha(raw)=="428f7c124649d7d40067b31704b63742a9da17e35425a9f8a3b1ab89839c9df9","Native artifact bytes differ")
spec=importlib.util.spec_from_file_location("owned_collector_candidate",DRIVER)
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
original=subprocess.run(["git","--git-dir=/mnt/development/projects/git-mirrors/anytype-swift.git","show",BASE+":"+PACKET+"/slice-a/run_native_archive.py"],check=True,capture_output=True).stdout.decode()
old_start=original.index("        expected_fixtures = {kind + suffix for kind in SPECIMENS")
old_end=original.index("\n        for entry in closure",old_start)
old_body=original[old_start:old_end]
namespace={"SPECIMENS":candidate.SPECIMENS,"require":candidate.require}
exec("def original_inventory(fixtures):\n"+textwrap.indent(textwrap.dedent(old_body),"    ")+"\n",namespace)
manifest=json.loads((PACKET_ROOT/"slice-a/EXECUTION_INPUTS.json").read_text())
results=[]
def expect_refusal(name,call,reason):
    try: call()
    except RuntimeError as e:
        require(str(e)==reason,"Unexpected refusal for "+name+": "+str(e))
        results.append({"case":name,"outcome":"EXPECTED_REFUSAL","reason":str(e)})
    else: raise AssertionError("Expected refusal did not occur: "+name)
with tempfile.TemporaryDirectory(prefix="otzaria-collector-offline-") as tmp:
    fixtures=pathlib.Path(tmp)
    with zipfile.ZipFile(EVIDENCE/"original-native-archive.zip") as z:
        members=[n for n in z.namelist() if n.startswith("fixtures/")]
        for n in members:
            suffix=n.removeprefix("fixtures/")
            require("/" not in suffix and "\\" not in suffix,"Unexpected fixture path")
            (fixtures/suffix).write_bytes(z.read(n))
        frozen={n:sha(z.read(n)) for n in members}
    expect_refusal("unchanged_original_collector_reproduces_actual_failure",
        lambda:namespace["original_inventory"](fixtures),"Unexpected specimen evidence files")
    candidate.verify_fixture_inventory(fixtures)
    specimens,cleanup=candidate.verify_specimens(fixtures)
    rejection=candidate.verify_rejections(fixtures,manifest,specimens)
    require(len(specimens)==4 and rejection["cases"]==26,"Authenticated evidence checks differ")
    results.append({"case":"candidate_accepts_all_authentic_fixture_evidence","outcome":"PASS",
        "fixture_files":len(members),"native_exports_reexecuted":False,"archive_controls_reexecuted":False})
    extra=fixtures/"unexpected-evidence.json";extra.write_text("{}\n")
    try:
        expect_refusal("unexpected_file_remains_rejected",lambda:candidate.verify_fixture_inventory(fixtures),
            "Unexpected specimen evidence files")
    finally: extra.unlink()
    summary=fixtures/"schema-registration.json";summary_raw=summary.read_bytes()
    derivative=json.loads(summary_raw);derivative["registration_calls"]=22
    summary.write_text(json.dumps(derivative))
    try:
        expect_refusal("out_of_bound_phase_inventory_rejected",lambda:candidate.verify_fixture_inventory(fixtures),
            "Native schema history has no bounded completed registration inventory")
    finally: summary.write_bytes(summary_raw)
    require({p.name for p in fixtures.iterdir()}=={n.removeprefix("fixtures/") for n in members},"Offline test changed inventory")
    for n,digest in frozen.items(): require(sha((fixtures/n.removeprefix("fixtures/")).read_bytes())==digest,"Offline test changed authentic bytes")
report={"status":"OFFLINE_COLLECTOR_ONLY_CONTROLS_PASS","cases":results,
    "driver_sha256":sha(DRIVER.read_bytes()),"artifact_sha256":sha(raw),
    "source_native_run":45139622096,"actual_original_registration_phases_retained":2,
    "phase_history_trimmed":False,"native_cases_replayed":0,
    "workflow_conclusion_unchanged":"failure","unreached_global_source_stability_gate_remains_unreached":True,
    "original_specimen_and_rejection_verifiers_reused_without_changes":True}
output=pathlib.Path(__file__).with_name("OFFLINE_VALIDATION.json")
output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":report["status"],"cases":len(results),"sha256":sha(output.read_bytes()),
    "native_cases_replayed":0,"workflow_conclusion":"failure"}))

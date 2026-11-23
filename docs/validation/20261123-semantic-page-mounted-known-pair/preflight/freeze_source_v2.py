from pathlib import Path
import ast,subprocess,json,hashlib,shutil,difflib
w=Path("/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123")
m="/mnt/development/projects/git-mirrors/anytype-swift.git"
base="8a6d64ba152ba3aa4bb4376d070f63f5c9daceca";origin="68148339c275268795360d71d519a5baf003adf8"
d=w/"docs/validation/20261123-semantic-page-mounted-known-pair"
assert d.is_dir() and not list(d.iterdir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(s,n):return subprocess.check_output(["git","--git-dir",m,"show",s+":"+n])
def save(p,v):
 with p.open("x") as f:f.write(json.dumps(v,sort_keys=True,indent=2)+"\n")
component=json.loads(Path("/mnt/development/projects/diagnostics/semantic-page-mounted-known-pair-20261123/exact-original-component.json").read_text())
for row in component["files"]:
 p=w/row["path"];assert sha(p)==row["sha256"]==hashlib.sha256(blob(origin,row["path"])).hexdigest()
mounted="Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py"
raw=(w/mounted).read_bytes();before=blob(base,mounted)
old=component["new_mounted_call"]["before"].encode();new=component["new_mounted_call"]["after"].encode()
assert raw.count(new)==1 and raw.replace(new,old)==before
consumer="Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py"
candidate=(w/consumer).read_text();original=blob(base,consumer).decode()
assert candidate.replace("import consumer_simulator","import simulator_selection").replace("pair = consumer_simulator.choose_pair(runtimes, devices)",'pair = simulator_selection.choose_pair(runtimes, devices, product_family="iPad", major=27, architecture="arm64")')==original
tp="Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_known_pair.py"
test=ast.parse((w/tp).read_text())
methods=[n.name for n in ast.walk(test) if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")]
assert methods==["test_mounted_import_and_owned_region_use_qualified_pair_without_fallback"]
inputs={}
for directory in ["Tools/PinkhaSemanticAnchorWire/apple_mounted","Tools/PinkhaSemanticAnchorWire/apple_consumer","Tools/PinkhaSemanticAnchorWire/apple_runtime","Tools/PinkhaSimulatorGate","Tools/PinkhaNativeDerived","Tools/AnyEngineValidation/prepared_inline_file_apple"]:
 for p in (w/directory).glob("*.py"):
  assert p.is_file() and not p.is_symlink()
  inputs[p.relative_to(w).as_posix()]=sha(p)
for name in ["Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json","Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json","docs/validation/20261123-page154-known-simulator/original-page-available-runtimes.log","docs/validation/20261123-page154-known-simulator/original-page-available-device-types.log"]:
 inputs[name]=sha(w/name)
known=w/"docs/validation/20261123-page154-known-simulator"
old_inputs=json.loads((known/"attempt1/source-before.json").read_text())
assert (known/"attempt1/source-before.json").read_bytes()==(known/"attempt1/source-after.json").read_bytes()
qualified=[]
for name,expected in old_inputs.items():
 prior=blob("ebabf8dc7d91592ac957414c10cff0daad3f3e3d",name)
 assert hashlib.sha256(prior).hexdigest()==expected
 current=(w/name).read_bytes()
 same=hashlib.sha256(current).hexdigest()==expected
 if not same:
  assert name=="docs/validation/20261123-page154-known-simulator/README.md"
  assert expected=="f3d787c4bdd1f2b031fd48a58366b6a115dfea5fb11b7b55411048d96030519b"
  assert hashlib.sha256(current).hexdigest()=="5d7439ccacb334e8fcd35fd6f6ca95d163306c0ce1d24742a7fda82dd9c6d06b"
  assert prior.splitlines(True)[:32]==current.splitlines(True)[:32]
  (d/"retained-original-readme.md").write_bytes(prior)
  (d/"retained-readme-exact.diff").write_text("".join(difflib.unified_diff(prior.decode().splitlines(True),current.decode().splitlines(True),fromfile="original-frozen-readme",tofile="qualified681-readme")))
 qualified.append({"path":name,"original_qualified_sha256":expected,"current_sha256":hashlib.sha256(current).hexdigest(),"byte_identical":same,"allowed_difference":None if same else "Exact original final status paragraph replaced and evidence-result appendix added; both README bytes and full difference retained"})
receipt=json.loads((known/"attempt1/receipt.json").read_text())
assert receipt["pass"]==4 and receipt["fail"]==0
for n,h in receipt["files"].items():assert sha(known/"attempt1"/n)==h
events=[json.loads(v) for v in (known/"attempt1/events.jsonl").read_text().splitlines()]
starts=[v["method"] for v in events if v["event"]=="START"];passes=[v["method"] for v in events if v["event"]=="PASS"]
assert starts==passes and len(starts)==len(set(starts))==4
save(d/"retained-component.json",dict(component,qualified_original_inputs=qualified,retained_four_method_names=starts,retained_receipt_sha256=sha(known/"attempt1/receipt.json"),retained_events_sha256=sha(known/"attempt1/events.jsonl"),old_tests_rerun=0))
old_admission=w/"docs/validation/20261123-semantic-page-mounted-admission"
retained_admission={}
for p in old_admission.rglob("*"):
 if p.is_file():
  name=p.relative_to(w).as_posix();assert p.read_bytes()==blob(base,name)
  retained_admission[name]=sha(p)
plan="Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json";admission="Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json"
assert sha(w/plan)=="19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f"
assert sha(w/admission)=="17c37d842009b23d50ab2222383c1f025242aa2e61f1828cf1bc1a346b5ed7e5"
save(d/"source-review.json",{"status":"FROZEN_SOURCE_ONE_NEW_MOUNTED_ADAPTER_CONTROL_NOT_RUN","base_sha":base,"qualified_component_origin":origin,"mounted_original_sha256":hashlib.sha256(before).hexdigest(),"mounted_current_sha256":sha(w/mounted),"mounted_exact_one_call_inverse_equal":True,"mounted_call_inverse":component["new_mounted_call"],"qualified_consumer_sha256":sha(w/consumer),"qualified_consumer_exact_two_line_inverse_equal":True,"helper_source_sha256":sha(w/"Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_simulator.py"),"shared_selector_source_sha256":sha(w/"Tools/PinkhaSimulatorGate/simulator_selection.py"),"import_contract":"Mounted dynamically loads its own repository-relative apple_consumer/run.py as page154_original_consumer_helpers; the exact qualified consumer imports consumer_simulator; actual loaded repo modules remain bound by unchanged checkout_inputs guard","source_sha256":inputs,"declared_frozen_source_and_fixture_count":len(inputs),"actual_loaded_source_set":"To be recorded by the single new control runner","new_selector":"test_mounted_known_pair.MountedKnownPairAdapterControl.test_mounted_import_and_owned_region_use_qualified_pair_without_fallback","new_method_count":1,"retained_policy_methods":4,"retained_policy_reruns":0,"original_admission_files":retained_admission,"mounted_source_plan_sha256":sha(w/plan),"fixed_admission_sha256":sha(w/admission),"new_tests_executed":0,"product_tests_executed":0,"builds":0,"fallback_allowed":False,"owned_command_budgets_seconds":{"inventory":60,"create":60,"boot":90,"bootstatus":180,"cleanup_total":60},"physical_device":"NOT_RUN","mounted_acceptance":"NOT_RUN","freeze_auditor_sha256":sha(Path(__file__))})
readme="""# Mounted Page154 known-pair caller integration

This source checkpoint restores the exact qualified consumer component from 68148339c275268795360d71d519a5baf003adf8 and connects the mounted controller to it. The original helper, original consumer import/call, original four-method source, and original evidence are byte-for-byte copies. Their four recorded passes are retained without rerun.

The mounted controller changes exactly one call from the generic selector with latest-runtime eligibility to consumer.consumer_simulator.choose_pair(runtimes, types). Reversing that call reproduces the entire prior run.py byte-for-byte. Restoring the previously qualified two-line consumer import/call also has an exact inverse to the prior consumer. There is no new simulator policy or import system.

The mounted controller loads its sibling consumer through the existing explicit repository-relative import spec. That exact qualified consumer exposes the approved helper, whose shared selector dependency is unchanged. The existing checkout_inputs guard verifies every loaded repository module against its committed input bytes. The new control imports the real mounted module and exercises that guard, including refusal of an incorrect helper hash.

Exactly one new composed control is prepared. It executes the actual mounted inventory/create/boot region with a controlled external runner and the preserved original inventories. It verifies the approved 27.0/24A434/M5 pair, a newly returned owned UUID, unchanged command budgets, and refusal before any creation when the approved runtime is absent despite another installed 27.2 runtime. External process creation is forbidden in the control. This is an adapter check; no simulator or product method executes.

All original admission files, artifact pins, source-plan bytes and product inputs remain unchanged. The exact current source/fixture ledger and inverse map are in source-review.json. The prior four-method input comparison is in retained-component.json: eight original inputs are identical; the only ninth difference is the original README's final status paragraph and added evidence-result appendix. Its original pre-control bytes and exact difference are retained separately. The first freeze audit incorrectly assumed this was purely an append and stopped before creating a source ledger or running any control; that diagnostic outcome is preserved in the separate evidence follow-up.

At this source freeze the new method is NOT_RUN. An evidence-only follow-up will preserve its first actual outcome. Mounted preparation, editor selection/Cancel/Create, Apple cold reopen, physical device and shipping acceptance remain open. Root owns review, shared integration, workflow dispatch and Asana.
"""
with (d/"README.md").open("x") as f:f.write(readme)
print(json.dumps({"source_review_sha256":sha(d/"source-review.json"),"retained_component_sha256":sha(d/"retained-component.json"),"declared_inputs":len(inputs),"test_sha256":sha(w/tp),"mounted_sha256":sha(w/mounted),"free":shutil.disk_usage("/mnt/development").free}))

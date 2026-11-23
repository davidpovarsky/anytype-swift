#!/usr/bin/env python3
"""Audit original source hashes and descriptors against the frozen mounted origin; no product execution."""
from pathlib import Path
import hashlib,json,os,plistlib,subprocess,time
ROOT=Path("/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit")
OUT=ROOT/"mounted-products-inventory"
MIRROR="/mnt/development/projects/git-mirrors/anytype-swift.git"
ORIGIN="68148339c275268795360d71d519a5baf003adf8"
FROZEN="5a6a05d9152553b1bee661eadc7b539b25b10ae1"
TOKEN="/var/run/com.apple.security.cryptexd/mnt/com.apple.iPhoneOS.SimulatorRuntime-v24.1.434.0.p5Mt7T/Library/Developer/CoreSimulator/Profiles/Runtimes/iOS 27.0.simruntime/Contents/Resources/RuntimeRoot/usr/lib/libMainThreadChecker.dylib"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open("x") as f:f.write(json.dumps(v,sort_keys=True,indent=2)+"\n")
def git(*a):return subprocess.check_output(["git","--git-dir",MIRROR,*a])
def tree(commit):
 rows={}
 for row in filter(None,git("ls-tree","-rz",commit).split(b"\0")):
  meta,name=row.split(b"\t",1);mode,kind,oid=meta.decode().split()
  name=name.decode("utf8")
  assert mode in ("100644","100755","120000") and kind=="blob" and name not in rows
  rows[name]={"mode":mode,"oid":oid}
 return rows
def product(name):return not name.startswith(("Tools/",".github/","docs/"))
started=time.time()
original=read(ROOT/"native-selected/source-before.json")
assert (ROOT/"native-selected/source-before.json").read_bytes()==(ROOT/"native-selected/source-after.json").read_bytes()
assert sha((ROOT/"native-selected/source-before.json").read_bytes())=="533bb8ad8eed3607521bef3517ff3a7cd53728956872180209cd9280d48e365d"
trees={ORIGIN:tree(ORIGIN),FROZEN:tree(FROZEN)}
assert set(original)==set(trees[ORIGIN])
hashes={};sizes={};total_bytes=0
proc=subprocess.Popen(["git","--git-dir",MIRROR,"cat-file","--batch"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
try:
 for rows in trees.values():
  for row in rows.values():
   oid=row["oid"]
   if oid in hashes:continue
   proc.stdin.write((oid+"\n").encode());proc.stdin.flush()
   header=proc.stdout.readline().decode().strip().split()
   assert len(header)==3 and header[:2]==[oid,"blob"]
   size=int(header[2]);assert 0<=size<1024**3
   remain=size;h=hashlib.sha256()
   while remain:
    b=proc.stdout.read(min(remain,1024**2));assert b;remain-=len(b);h.update(b)
   assert proc.stdout.read(1)==b"\n"
   hashes[oid]=h.hexdigest();sizes[oid]=size;total_bytes+=size
finally:
 proc.stdin.close();assert proc.wait(timeout=10)==0
maps={commit:{name:hashes[row["oid"]] for name,row in rows.items()} for commit,rows in trees.items()}
assert maps[ORIGIN]==original
before_products={n:h for n,h in original.items() if product(n)}
after_products={n:h for n,h in maps[FROZEN].items() if product(n)}
assert before_products==after_products
assert {n:r for n,r in trees[ORIGIN].items() if product(n)}=={n:r for n,r in trees[FROZEN].items() if product(n)}
delta={}
for n in sorted(set(maps[ORIGIN])|set(maps[FROZEN])):
 if maps[ORIGIN].get(n)!=maps[FROZEN].get(n) or trees[ORIGIN].get(n)!=trees[FROZEN].get(n):
  assert not product(n)
  delta[n]={"original_sha256":maps[ORIGIN].get(n),"frozen_sha256":maps[FROZEN].get(n),"original_git":trees[ORIGIN].get(n),"frozen_git":trees[FROZEN].get(n)}
assert len(delta)==18
embedded_path=OUT/"native-source-inputs-original.json"
embedded=read(embedded_path)
assert embedded["source_sha"]==ORIGIN
assert all(type(v["mtime_ns"]) is int and isinstance(v["sha256"],str) for v in embedded["inputs"].values())
embedded_hashes={n:v["sha256"] for n,v in embedded["inputs"].items()}
assert all(embedded_hashes.get(n)==h for n,h in original.items())
extra={n:h for n,h in embedded_hashes.items() if n not in original}
fp="Tools/PinkhaSemanticAnchorWire/apple_consumer/framework-files.json"
framework=json.loads(git("show",FROZEN+":"+fp))
assert maps[ORIGIN][fp]==maps[FROZEN][fp]
assert extra=={"Dependencies/Middleware/Lib.xcframework/"+n:h for n,h in framework.items()} and len(extra)==9
plan_path="Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json"
plan_raw=git("show",FROZEN+":"+plan_path)
assert sha(plan_raw)=="19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f"
plan=json.loads(plan_raw)
assert all(maps[ORIGIN].get(n)==maps[FROZEN].get(n)==v["sha256"] for n,v in plan["files"].items())
native=read(OUT/"native-inventory.json");ui=read(OUT/"ui-inventory.json")
descriptors={}
for name,expected,kind in [("original.xctestrun","b44dbf6c0619f1187ba6167245418c8f0870a3f6c4dac427bea99c870d0b89e7","native"),("ui-runner/original.xctestrun","55fe94261dc5360fd9c5e3b90532e393d273070b8ade7655c6695666eac9e165","ui")]:
 raw=(OUT/name).read_bytes();assert sha(raw)==expected;v=plistlib.loads(raw)
 version=v["__xctestrun_metadata__"]["FormatVersion"]
 if kind=="native":
  assert version==2 and len(v["TestConfigurations"])==1
  ts=v["TestConfigurations"][0]["TestTargets"]
  matching=[t for t in ts if t["BlueprintName"]=="AnytypeTests"];assert len(matching)==1
  target=matching[0];plan_policy="EXACT_NATIVE_NAMED_PLAN_ANYTYPETESTS";target_count=len(ts)
 else:
  assert version==1 and set(v)=={"__xctestrun_metadata__","PinkhaStage1AcceptanceUITests"}
  target=v["PinkhaStage1AcceptanceUITests"];assert target.get("IsUITestBundle") is True
  def unnamed(node):
   if isinstance(node,dict):
    for k,item in node.items():
     k=k.replace("_","").lower()
     assert "testplan" not in k and "testconfiguration" not in k and k!="configurationname"
     unnamed(item)
   elif isinstance(node,list):
    for item in node:unnamed(item)
  unnamed(v);plan_policy="OBSERVED_METADATA_FOR_EXACT_UNNAMED_V1_UI";target_count=1
 assert target.get("IsEnabled",True) is True
 env=target.get("EnvironmentVariables",{})
 assert isinstance(env,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in env.items())
 assert not any(k.startswith(("PINKHA_","TEST_RUNNER_PINKHA_")) for k in env)
 full=target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"];parts=full.split(":")
 assert parts.count(TOKEN)==1 and [t for t in parts if "libMainThreadChecker" in t]==[TOKEN]
 inv=native if kind=="native" else ui
 assert len(inv["root_descriptors"])==1 and inv["root_descriptors"][0]["sha256"]==expected
 saved=Path(inv["root_descriptors"][0]["saved_path"]);assert saved.read_bytes()==raw
 descriptors[kind]={"sha256":expected,"bytes":len(raw),"format_version":version,"original_target_count":target_count,"selected_blueprint":"AnytypeTests" if kind=="native" else "PinkhaStage1AcceptanceUITests","main_thread_checker_token":TOKEN,"complete_original_dyld_insert_libraries":full,"unmodified_other_tokens":[v for v in parts if v!=TOKEN],"test_host_path":target["TestHostPath"],"test_bundle_path":target["TestBundlePath"],"plan_policy":plan_policy,"archive_path":inv["root_descriptors"][0]["archive_path"],"original_bytes_preserved":True,"relocation_executed":False}
execution=read(ROOT/"native-selected/execution.json")
selected=read(ROOT/"native-selected-proof.json")
e=[r for r in selected["members"] if r["name"]=="execution.json"];assert len(e)==1
assert sha((ROOT/"native-selected/execution.json").read_bytes())==e[0]["sha256"]
ub=execution["ui_runner_build"];assert ub==read(OUT/"ui-runner/build-only.json") or all(ub.get(k)==v for k,v in read(OUT/"ui-runner/build-only.json").items())
assert ub["preparation_executions"]==ub["ui_executions"]==0 and ub["acceptance"]=="NOT_RUN"
assert ub["source_plan_sha256"]==sha(plan_raw)
for rel,expected in ub["original_project_files_sha256"].items():
 assert maps[ORIGIN]["PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/"+rel]==expected
assert ub["descriptor"]["executable_sha256"]==read(OUT/"ui-verified-entries.json")["Build/Products/Debug-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app/PlugIns/PinkhaStage1AcceptanceUITests.xctest/PinkhaStage1AcceptanceUITests"]["sha256"]
save(OUT/"frozen-git-inputs.json",{"source_sha":FROZEN,"inputs":maps[FROZEN],"git":trees[FROZEN]})
save(OUT/"source-comparison.json",{"status":"PASS_ALL_ORIGINAL_TRACKED_INPUTS_AND_FROZEN_PRODUCT_INPUTS_EXACT","original_source_sha":ORIGIN,"frozen_mounted_origin_sha":FROZEN,"original_entries":len(original),"frozen_entries":len(maps[FROZEN]),"product_entries":len(before_products),"original_source_map_sha256":sha((ROOT/"native-selected/source-before.json").read_bytes()),"source_before_after_byte_identical":True,"all_original_git_blobs_hashed":True,"all_frozen_git_blobs_hashed":True,"unique_git_blobs_read":len(hashes),"unique_git_blob_bytes_read":total_bytes,"all_product_modes_and_git_objects_equal":True,"controller_documentation_only_delta":delta,"embedded_native_source_inputs_sha256":sha(embedded_path.read_bytes()),"embedded_native_source_inputs_count":len(embedded_hashes),"exact_approved_framework_extras":extra,"framework_manifest_sha256":maps[FROZEN][fp],"frozen_source_plan_sha256":sha(plan_raw),"frozen_source_plan_files":plan["files"],"ui_embedded_source_inputs_present":False,"ui_source_binding":"Original whole-checkout before/after, exact mounted source-plan, original/generated project hashes and actual UI-only build receipt; no separate Build/PinkhaSourceInputs claimed","original_ui_project_files_sha256":ub["original_project_files_sha256"],"recorded_generated_ui_project_files_sha256":ub["generated_project_files_sha256"],"native_boundary_audit_owner":"/root/sdk_ci","native_boundary_audit_sha256":sha((ROOT/"INDEPENDENT_NATIVE_AUDIT.json").read_bytes()),"frozen_git_input_proof_sha256":sha((OUT/"frozen-git-inputs.json").read_bytes()),"product_tests_executed":0,"builds_executed":0,"elapsed_seconds":time.time()-started,"auditor_sha256":sha(Path(__file__).read_bytes())})
save(OUT/"descriptor-admission-proof.json",{"status":"PASS_EXACT_ORIGINAL_NATIVE_V2_AND_UI_V1","native":descriptors["native"],"ui":descriptors["ui"],"native_enumeration_required_plan":"AnytypeTests","ui_enumeration_plan":"Record actual unnamed-v1 plan label; require exact one selected method","preparation_selector":plan["selectors"]["preparation"],"ui_selector":plan["selectors"]["journey"],"relocation_executed":False,"enumeration_executed":False,"mounted_methods_executed":0})
print(json.dumps({"status":"PASS_SOURCE_AND_DESCRIPTOR_AUDIT","product_inputs":len(before_products),"all_original_inputs":len(original),"git_blobs_read":len(hashes),"unique_git_bytes_read":total_bytes,"source_comparison_sha256":sha((OUT/"source-comparison.json").read_bytes()),"descriptor_proof_sha256":sha((OUT/"descriptor-admission-proof.json").read_bytes()),"elapsed_seconds":time.time()-started}),flush=True)

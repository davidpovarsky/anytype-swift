import pathlib, subprocess, json, hashlib, tempfile, re, difflib, pwd, os, zipfile
SWIFT="/mnt/development/projects/git-mirrors/anytype-swift.git"
HEART="/mnt/development/projects/git-mirrors/anytype-heart.git"
HEART_REV="d98420b1113536afd08cde6de9a5816f6d27ffff"
BASE="79b9662f1b184409a32f838e5ad5e902b5eecafa"
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-otzaria-native-import-closed-20261123")
PREFIX="docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
PACKET=ROOT/PREFIX/"bc-candidate-20261123"
USER=pwd.getpwnam("ubuntu")
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def git(repo,rev,path,optional=False):
    r=subprocess.run(["runuser","-u","ubuntu","--","git","--git-dir="+repo,"show",rev+":"+path],capture_output=True)
    if optional and r.returncode==128: return None
    if r.returncode: raise RuntimeError(r.stderr.decode())
    return r.stdout
def write(name,data):
    p=PACKET/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    return sha(p.read_bytes())
def own(root):
    os.chown(root,USER.pw_uid,USER.pw_gid)
    for p in root.rglob("*"): os.chown(p,USER.pw_uid,USER.pw_gid)
def command(args,cwd):
    r=subprocess.run(["runuser","-u","ubuntu","--"]+args,cwd=cwd,capture_output=True,text=True)
    if r.returncode: raise RuntimeError(json.dumps({"args":args,"exit":r.returncode,"stdout":r.stdout,"stderr":r.stderr}))
    return r.stdout
lifetime_rev="cfc71a30498bba772aaf33f1ac08fdf65d1e0e3a"
lifetime_path="docs/pinkha/torah-integration/native-heart-lifetime-repair-20261123/EXECUTION_INPUTS.json"
life_raw=git(SWIFT,lifetime_rev,lifetime_path);life=json.loads(life_raw)
slice_rev="2da5419fa8b3e90ecca248ee9c83fd5055d8bca6"
slice_path=PREFIX+"/slice-a/EXECUTION_INPUTS.json"
slice_raw=git(SWIFT,slice_rev,slice_path);archive_manifest=json.loads(slice_raw)
r14=next(r for r in life["source_inputs"] if r["destination"]=="r14/native-heart-integration.patch")
patch=git(SWIFT,r14["revision"],r14["source_path"])
assert sha(patch)=="fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
input_rows=[]
def retain(stage,row,native_path):
    raw=git(SWIFT,row["revision"],row["source_path"])
    assert sha(raw)==row["sha256"] and len(raw)==row["bytes"]
    if "git_blob" in row: assert blob(raw)==row["git_blob"]
    input_rows.append({"stage":stage,"native_path":native_path,"repository":"davidpovarsky/anytype-swift",
        "revision":row["revision"],"source_path":row["source_path"],"bytes":len(raw),"sha256":sha(raw),"git_blob":blob(raw)})
    return raw
overlays=[]
for row in life["source_inputs"]:
    if "/native/" not in row["destination"]: continue
    native=row["destination"].split("/native/",1)[1]
    stage=row["destination"].split("/",1)[0]
    overlays.append((stage,native,retain(stage,row,native)))
mapping_path="docs/pinkha/torah-integration/native-heart-lifetime-repair-20261123/native/core/block/import/mapping_observation.go"
mapping=git(SWIFT,lifetime_rev,mapping_path)
assert sha(mapping)=="7634efc97506c1b1f4f67ecfdbd7fab919b5843986261a445e258ef39b8a3fa6"
input_rows.append({"stage":"qualified-no-progress-mapping-repair","native_path":"core/block/import/mapping_observation.go",
    "repository":"davidpovarsky/anytype-swift","revision":lifetime_rev,"source_path":mapping_path,
    "bytes":len(mapping),"sha256":sha(mapping),"git_blob":blob(mapping)})
overlays.append(("qualified-no-progress-mapping-repair","core/block/import/mapping_observation.go",mapping))
for row in archive_manifest["source_inputs"]:
    if row.get("role")=="native-product":
        overlays.append(("original-fixed-schema",row["heart_path"],retain("original-fixed-schema",row,row["heart_path"])))
archive_row=next(r for r in archive_manifest["new_native_inputs"] if r["heart_path"]=="core/block/import/owned_annotation_archive.go")
araw=git(SWIFT,slice_rev,PREFIX+"/"+archive_row["path"])
assert sha(araw)==archive_row["sha256"]
input_rows.append({"stage":"qualified-annotation-byte-preparation","native_path":archive_row["heart_path"],
    "repository":"davidpovarsky/anytype-swift","revision":slice_rev,"source_path":PREFIX+"/"+archive_row["path"],
    "bytes":len(araw),"sha256":sha(araw),"git_blob":blob(araw)})
overlays.append(("qualified-annotation-byte-preparation",archive_row["heart_path"],araw))
# Source-only composition in an exclusive temporary tree. No native compilation.
order=[];preimages={};source_before={};final={};r14_preimages=[]
with tempfile.TemporaryDirectory(prefix="otzaria-bc-source-compose-") as t:
    temp=pathlib.Path(t);patchfile=temp/"r14.patch";patchfile.write_bytes(patch)
    paths=[a for a,b in re.findall(r"^diff --git a/(.+) b/(.+)$",patch.decode(),re.M)]
    assert len(paths)==35 and len(set(paths))==35
    for name in paths:
        raw=git(HEART,HEART_REV,name,optional=True)
        r14_preimages.append({"native_path":name,"sha256":None if raw is None else sha(raw),
            "git_blob":None if raw is None else blob(raw),"bytes":0 if raw is None else len(raw)})
        if raw is not None:
            p=temp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    own(temp)
    command(["git","apply","--check",str(patchfile)],temp)
    command(["git","apply",str(patchfile)],temp)
    for name in paths:
        after=(temp/name).read_bytes()
        order.append({"stage":"r14","native_path":name,"before_sha256":next(r["sha256"] for r in r14_preimages if r["native_path"]==name),
            "after_sha256":sha(after)})
        final[name]=after
    for stage,name,raw in overlays:
        p=temp/name
        if p.exists(): before=p.read_bytes()
        else: before=git(HEART,HEART_REV,name,optional=True)
        order.append({"stage":stage,"native_path":name,"before_sha256":None if before is None else sha(before),"after_sha256":sha(raw)})
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);final[name]=raw
    candidate_rows=[];patches=[]
    for p in sorted((PACKET/"native").rglob("*.go")):
        name=p.relative_to(PACKET/"native").as_posix();after=p.read_bytes()
        native=temp/name
        if native.exists(): before=native.read_bytes()
        else: before=git(HEART,HEART_REV,name,optional=True)
        preimages[name]=before
        source_before[name]=None if before is None else sha(before)
        newpatch="".join(difflib.unified_diff([] if before is None else before.decode().splitlines(True),
            after.decode().splitlines(True),fromfile="/dev/null" if before is None else "a/"+name,tofile="b/"+name))
        assert newpatch
        patches.append(newpatch)
        candidate_rows.append({"path":p.relative_to(PACKET).as_posix(),"native_path":name,"bytes":len(after),
            "sha256":sha(after),"git_blob":blob(after),"before_sha256":None if before is None else sha(before),
            "change":"additive-file" if before is None else "scoped-existing-afterimage"})
        native.parent.mkdir(parents=True,exist_ok=True);native.write_bytes(after);final[name]=after
        order.append({"stage":"uncompiled-B1-C-candidate","native_path":name,"before_sha256":source_before[name],"after_sha256":sha(after)})
    fullpatch="".join(patches);(PACKET/"B1C_SOURCE.patch").write_text(fullpatch)
    patchpath=temp/"candidate.patch";patchpath.write_text(fullpatch);own(temp)
    command(["git","apply","--reverse","--check",str(patchpath)],temp)
    command(["git","apply","--reverse",str(patchpath)],temp)
    for name,before in preimages.items():
        p=temp/name
        assert (not p.exists()) if before is None else (p.read_bytes()==before),name
    # Exact source-only inverse; not a behavior or runtime proof.
    inverse={"all_candidate_afterimages_reverse_to_exact_preimage_or_absence":True,"files":len(candidate_rows),
        "native_tests_executed":0,"compiler_invoked":False,"original_r14_patch_applies_to_exact_35_preimages":True}
# Regenerate all four reviewed narrow deltas from the completed final files.
patch_names={
 "core/block/import/processor.go":"PROCESSOR_ADMISSION.patch",
 "core/block/import/owned_import_dependencies.go":"CLOSED_CONSTRUCTOR.patch",
 "core/block/import/owned_import_operation.go":"SAME_OPERATION_READBACK.patch",
 "core/block/import/common/objectcreator/objectcreator.go":"CREATOR_DISPOSITION.patch",
 "core/pinkha/annotationschema/definition.go":"DEFINITION_FORWARDER.patch",
}
for name,out in patch_names.items():
    before=preimages[name];after=(PACKET/"native"/name).read_bytes()
    (PACKET/out).write_text("".join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),
        fromfile="a/"+name,tofile="b/"+name)))
formatting=command(["/usr/local/bin/gofmt","-l"]+[str(PACKET/r["path"]) for r in candidate_rows],ROOT)
assert not formatting.strip()
# Include exact actual native policy; do not silently infer a Host/SDK grant.
policy_path=PREFIX+"/bc-original-import-design/ANNOTATION_PAYLOAD_POLICY.json"
policy=git(SWIFT,"c067f5c5d5afc5d2679bdc371163d3018cc71a7b",policy_path)
assert sha(policy)=="818bd440374cd49072f018065d300209bd2dafc506ec16d8c2c686736bde7077"
(PACKET/"ANNOTATION_PAYLOAD_POLICY.json").write_bytes(policy)
# Actual Apple baseline normal-package graph plus exact retained source imports.
artifact=pathlib.Path("/mnt/development/projects/diagnostics/otzaria-native-annotation-budget-20261123/45139622096/original-native-archive.zip")
with zipfile.ZipFile(artifact) as z: rawlist=z.read("08-declared-native-inputs.stdout")
text=rawlist.decode();decoder=json.JSONDecoder();pos=0;records=[]
while pos<len(text):
    while pos<len(text) and text[pos].isspace():pos+=1
    if pos==len(text):break
    o,pos=decoder.raw_decode(text,pos);records.append(o)
graph={r["ImportPath"]:set(r.get("Imports",[])) for r in records if "[" not in r.get("ImportPath","") and not r.get("ImportPath","").endswith(".test")}
module="github.com/anyproto/anytype-heart/"
def imports(raw):
    text=raw.decode();out=[]
    for block in re.findall(r"(?m)^import\s*\((.*?)^\)",text,re.S):out+=re.findall(r'"([^"]+)"',block)
    out+=re.findall(r'(?m)^import\s+(?:\w+\s+)?"([^"]+)"',text)
    return out
for name,body in final.items():
    if not name.endswith(".go") or name.endswith("_test.go"):continue
    graph.setdefault(module+str(pathlib.PurePosixPath(name).parent),set()).update(imports(body))
def reach(start,goal,seen=None):
    if start==goal:return [start]
    seen=set() if seen is None else seen
    if start in seen:return None
    seen.add(start)
    for dest in sorted(graph.get(start,[])):
        p=reach(dest,goal,seen)
        if p:return [start]+p
    return None
new_edges=[]
for row in candidate_rows:
    package=module+str(pathlib.PurePosixPath(row["native_path"]).parent)
    for imp in imports((PACKET/row["path"]).read_bytes()):
        new_edges.append({"from":package,"to":imp,"candidate_path":row["path"]})
cycles=[]
for edge in new_edges:
    back=reach(edge["to"],edge["from"])
    if back:cycles.append([edge["from"]]+back)
assert not cycles,cycles
parent=module+"core/pinkha/annotationschema";importer=module+"core/block/import";leaf=parent+"/definition";creator=module+"core/block/object/objectcreator"
bad=reach(parent,importer);assert bad and len(bad)>1,bad
assert reach(creator,leaf) is None
dag={"status":"STATIC_SOURCE_DAG_NO_NEW_CYCLE_NOT_A_COMPILE","baseline_run":45139622096,
    "raw_actual_go_list_sha256":sha(rawlist),"baseline_records":len(records),
    "candidate_cycles":cycles,"old_bad_import_would_form_cycle":[importer]+bad,
    "objectcreator_to_leaf_back_edge":None,"candidate_import_edges":new_edges,
    "exact_retained_native_source_imports_included":True,"test_variants_not_used_as_production_edges":True,
    "limitations":"This checks package source dependency paths over actual retained Apple baseline package imports and exact composed native sources; no candidate typecheck, link or runtime acceptance is inferred."}
dagsha=write("IMPORT_DAG_PROOF.json",dag)
manifest={"schema":1,"status":"REVIEWABLE_NATIVE_SOURCE_COMPOSITION_NOT_AN_EXECUTION_GATE",
    "control_base":BASE,"heart_base":HEART_REV,"native_tests_executed":0,"production_activation":False,
    "r14":{"revision":r14["revision"],"path":r14["source_path"],"sha256":sha(patch),"preimages":r14_preimages},
    "reused_manifests":[{"revision":lifetime_rev,"path":lifetime_path,"sha256":sha(life_raw)},
        {"revision":slice_rev,"path":slice_path,"sha256":sha(slice_raw)}],
    "original_input_rows":input_rows,"ordered_afterimages":order,
    "candidate_inputs":candidate_rows,
    "final_composed_changed_native_files":[{"path":name,"bytes":len(body),"sha256":sha(body)} for name,body in sorted(final.items())],
    "original_module_hashes":archive_manifest["original_module_hashes"],
    "annotation_payload_policy_sha256":sha(policy),"new_generated_or_proto_inputs":[],
    "native_import_RPC_names_generated_or_activated":False,"source_inverse":inverse,
    "gofmt_parse_and_format_clean":True,"import_dag_proof_sha256":dagsha,
    "prior_test_results_replayed":False,
    "collector_for_future_gate":{"revision":"e1bd8d4db565b2f87b75504060538a669135c522",
        "path":PREFIX+"/slice-a/run_native_archive.py",
        "sha256":"afc154c797582a2d5e61ac549afd9b959ffcef0ff6869375915d4308e0506238"},
    "remaining_required_work":["genuine native B1/C fixture and exact compiler/runtime gate",
        "generated production RPC boundary and genuine Swift Invocation",
        "Host saved-revision/selected-Space authority and final acknowledgement"]}
manifestsha=write("SOURCE_COMPOSITION.json",manifest)
# Refresh stale phase metadata rather than leaving old hashes/old remaining work.
write("PREPARATION_PHASE.json",{"status":"COHESIVE_SOURCE_PREPARATION_NOT_COMPILED_NOT_ACTIVATED",
    "base":BASE,"files":candidate_rows,"whole_source_composition_sha256":manifestsha,
    "remaining_code":manifest["remaining_required_work"],"source_policy_bound":True,
    "actual_current_writer_with_historical_effects_contract":True,
    "no_atomic_zero_storage_promise":True,"no_original_import_engine_replacement":True})
obs=PACKET/"native/core/block/object/objectcreator/owned_annotation_observer.go"
proof=json.loads((PACKET/"BUNDLED_OBSERVER_SOURCE.json").read_text());proof.update(sha256=sha(obs.read_bytes()),bytes=obs.stat().st_size)
write("BUNDLED_OBSERVER_SOURCE.json",proof)
write("FULL_SOURCE_INVERSE.json",{"status":"SOURCE_ONLY_INVERSE_PASS_NOT_COMPILED",**inverse,
    "full_patch_sha256":sha((PACKET/"B1C_SOURCE.patch").read_bytes()),"candidate_inputs":candidate_rows})
own(PACKET)
print(json.dumps({"files":len(candidate_rows),"original_inputs":len(input_rows),"ordered_entries":len(order),
    "final_changed_native_files":len(final),"manifest_sha256":manifestsha,"dag_sha256":dagsha,
    "inverse":inverse,"old_bad_cycle":[importer]+bad,"new_cycles":cycles,"native_execution":False}))

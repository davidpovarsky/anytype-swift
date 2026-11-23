"""Source-only Page154 validation: AST/Git/YAML/shell, no repository imports."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
sys.dont_write_bytecode=True
import yaml

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE="c0c2ddb31e5488435b0bd1c7ede5666b03dae5ea"
ENV={**os.environ,"GIT_OPTIONAL_LOCKS":"0","PYTHONDONTWRITEBYTECODE":"1"}
NEW=("Tools/CurrentAppleValidation/page154_contract.py",
     "Tools/CurrentAppleValidation/page154_current.py",
     "Tools/CurrentAppleValidation/page154-inputs.json",
     ".github/workflows/pinkha-current-page154-mounted.yml")
EXPECTED=("0b6d2cf343ae802c27426c1f2ca4bf14cac995090d8abe08646f72fdf2650eaa",
          "53f440265e048f3bb17d89eac7cd37e96b02814f1fe0421da42fa5f45b5db968",
          "6743e29ab5162d669cfce2527f24746f4090efec8ffb0d10789309789ae8068f",
          "419f942971e900de94a17b86b97abbc675885003174180b1440bd200f60f65ce")
def require(value, label):
    if not value:raise ValueError(label)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(["git","-C",str(ROOT),*args],env=ENV,timeout=15)
def original(path):return git("show",BASE+":"+path)
def json_read(path):return json.loads(path.read_bytes())
def sources():
    result={}
    for name in NEW:
        path=ROOT/name;s=path.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and path.resolve()==path,"source_type")
        result[name]={"sha256":sha(path.read_bytes()),"bytes":s.st_size,
                     "mode":stat.S_IMODE(s.st_mode),"inode":str(s.st_ino),"device":str(s.st_dev)}
    return result
def value_constants(tree):
    result={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try:result[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    return result
def call_name(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return call_name(node.value)+"."+node.attr
    return ""
def main():
    started=time.monotonic()
    before=sources()
    for path,expected in zip(NEW,EXPECTED):require(before[path]["sha256"]==expected,"frozen_source_changed")
    require(git("rev-parse","HEAD").decode().strip()==BASE,"unexpected_source_parent")
    policy=ast.parse((ROOT/NEW[0]).read_bytes())
    driver=ast.parse((ROOT/NEW[1]).read_bytes())
    constant=value_constants(policy)
    fixed=json_read(ROOT/NEW[2])
    require(constant["PROFILE"]==fixed["profile"]=="current-page154-mounted","profile")
    require(fixed["selectors"]==[constant["PREPARATION"],constant["JOURNEY"]]
            and fixed["excludedFactory"]==constant["EXCLUDED_FACTORY"]
            and fixed["excludedFactory"] not in fixed["selectors"],"exact_two_stage_scope")
    require(fixed["freshSetupAcceptanceCredit"]==0,"setup_credit")
    require(constant["UI_SHA256"]==fixed["uiPlan"]["candidate_ui_sha256"],"ui_source_pin")
    require(len(fixed["inputs"])==51 and len(fixed["moduleOrigins"])==37,"fixed_closure_count")
    require(len(fixed["productTrees"])==12 and len(fixed["helperTrees"])==5,"tree_scope")
    require(sha(original("Tools/CurrentAppleValidation/source-inputs.json"))==fixed["commonManifestSHA256"],
            "common_manifest_changed")
    direct=[]
    for name,row in fixed["inputs"].items():
        if name in NEW:
            data=(ROOT/name).read_bytes();mode="100644";kind="RAM_CURRENT_NEW_SOURCE"
        else:
            data=original(name)
            metadata=git("ls-tree",BASE,"--",name).split(b"\t",1)[0].decode().split()
            require(len(metadata)==3 and metadata[1]=="blob","declared_git_blob")
            mode=metadata[0];kind="IMMUTABLE_GIT_OBJECT"
            if (ROOT/name).is_file():
                require((ROOT/name).read_bytes()==data,"materialized_input_changed")
                kind="RAM_PHYSICAL_AND_IMMUTABLE_GIT"
        oid=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        require(row=={"gitMode":mode,"gitBlob":oid,"sha256":sha(data)},"fixed_input_changed:"+name)
        direct.append({"path":name,"scope":kind,"bytes":len(data),**row})
    trees=fixed["productTrees"]
    projection=json_read(HERE/"source-projection.json")
    require(trees["Anytype"]=="078147cfbfc8c8b839c7058bdf90d7744c61e3d8"
            and trees["Modules"]=="0867b93e1a96a9da8a285463094f7b61b5363774","projected_trees")
    for name,tree in trees.items():
        expected=projection["trees"][name]["baseTree"] if name in projection["trees"] else tree
        require(git("rev-parse",BASE+":"+name).decode().strip()==expected,"original_product_tree")
    for name,tree in fixed["helperTrees"].items():
        require(git("rev-parse",BASE+":"+name).decode().strip()==tree,"helper_tree")
    require(len(fixed["projectionOrigins"])==5 and
            fixed["projectionOrigins"]["Modules/ProtobufMessages/Tests/ProtobufMessagesTests/PinkhaHeartSemanticAnchorObservationTests.swift"]["fixtureMethodExecuted"] is False,
            "diagnostic_projection_scope")
    for path,row in fixed["uiPlan"]["files"].items():
        data=original(path)
        require(sha(data)==row["sha256"] and len(data)==row["bytes"],"retained_ui_copy_input")
    require(sha(original(constant["UI_PATH"]))==constant["UI_SHA256"],"full_ui_journey_changed")
    correction=json_read(HERE/"descriptor-peer-correction.json")
    corrected=(ROOT/NEW[0]).read_text();reversed_source=corrected
    for h in correction["wholeFileInverse"]:
        require(reversed_source.count(h["after"])==1,"descriptor_inverse_occurrence")
        reversed_source=reversed_source.replace(h["after"],h["before"])
    require(sha(corrected.encode())==correction["afterSHA256"]
            and sha(reversed_source.encode())==correction["beforeSHA256"],"descriptor_whole_inverse")
    functions={n.name:n for n in driver.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    execute=functions["execute"]
    stages=[node.args[1].value for node in ast.walk(execute)
            if isinstance(node,ast.Call) and call_name(node.func)=="run_stage"
            and len(node.args)>1 and isinstance(node.args[1],ast.Constant)]
    require(stages==["preparation","ui"],"exact_execute_stages")
    names=[call_name(n.func) for n in ast.walk(driver) if isinstance(n,ast.Call)]
    require(not any(name.startswith(("unittest.","pytest.")) for name in names),"no_host_test_runner")
    require("current.create_device" in names and "current.recover_owned" in names
            and "current.cleanup_devices" in names and "current.unfinished_groups" in names,
            "qualified_owned_primitives")
    require("subprocess.Popen" not in names and "subprocess.run" not in names,"no_unbounded_new_process_path")
    require(len([n for n in ast.walk(driver) if isinstance(n,ast.Call) and call_name(n.func)=="preserve_products"])==1,
            "common_build_preservation")
    workflow_raw=(ROOT/NEW[3]).read_bytes()
    workflow=yaml.load(workflow_raw,Loader=yaml.BaseLoader)
    job=workflow["jobs"]["current-page154-mounted"]
    require(len(workflow["jobs"])==1 and "uses" not in job
            and job["runs-on"]=="xcode-27" and job["timeout-minutes"]=="150","standalone_job")
    require(job["permissions"]=={"contents":"read","actions":"read"},"job_read_permissions")
    steps=job["steps"];runs=[s for s in steps if "run" in s]
    require(len(runs)==3 and len(steps)==7,"exact_finite_steps")
    checks=[]
    for index,step in enumerate(runs):
        result=subprocess.run(["bash","-n"],input=step["run"].encode(),capture_output=True,timeout=10,env=ENV)
        require(result.returncode==0,"bash_syntax:"+step["name"])
        checks.append({"index":index,"name":step["name"],"returnCode":result.returncode,
                       "stdout":result.stdout.decode(),"stderr":result.stderr.decode()})
    require(sum("page154_current.py execute" in s["run"] for s in runs)==1
            and sum("page154_current.py cleanup" in s["run"] for s in runs)==1,"exact_action_commands")
    require(next(s for s in steps if s.get("id")=="execute")["timeout-minutes"]=="130","execution_workflow_limit")
    upload=steps[-1]
    require(upload["uses"]=="actions/upload-artifact@v4" and upload["if"]=="always()"
            and upload["with"]["if-no-files-found"]=="error","original_evidence_always_upload")
    inline=json_read(HERE/"central-inline-job.json")
    rendered=workflow_raw.decode()
    require(inline["jobYAML"]==rendered[rendered.index("  current-page154-mounted:"):]
            and inline["standaloneWorkflowSHA256"]==sha(workflow_raw)
            and inline["newReusableWorkflowReferences"]==0,"exact_inline_job_data")
    protected=[
      "Tools/CurrentAppleValidation/current_execution.py","Tools/CurrentAppleValidation/contracts.py",
      "Tools/CurrentAppleValidation/cleanup_policy.py","Tools/CurrentAppleValidation/source-inputs.json",
      "Tools/CurrentAppleValidation/release_return_rtl.py","Tools/CurrentAppleValidation/native_ui_failed.py",
      ".github/workflows/pinkha-current-release-return-rtl.yml",".github/workflows/pinkha-current-native-ui-failed.yml"]
    retained={}
    for path in protected:
        require((ROOT/path).read_bytes()==original(path),"prior_two_routes_changed:"+path)
        retained[path]=sha(original(path))
    require(retained[protected[0]]=="eafc05a212751bb644a96a0ad73bff139f8eff26cdcc59e1057bbf569f374593","repaired_common_current")
    require(not git("diff","--name-only",BASE).strip(),"existing_tracked_source_mutation")
    after=sources();require(before==after,"static_check_changed_source")
    return {"status":"PASS_SOURCE_ONLY","scope":"AST, exact Git/input/tree bindings, YAML, bash -n and fixed route structure",
      "sourceParent":BASE,"sourceBefore":before,"sourceAfter":after,"fixedInputs":direct,
      "fixedInputCount":len(direct),"canonicalModuleOrigins":37,"projectedProductTrees":projection["trees"],
      "bashSyntax":checks,"retainedPriorFiles":retained,"newRepositoryModulesImported":0,
      "hostControlMethodsExecuted":0,"oldMethodsReplayed":0,"AppleBuilds":0,"nativeBuilds":0,"actualTestExecutions":0,
      "notProven":["Apple source compilation","runtime loaded closure","native/API artifact availability",
                   "actual generated descriptors","owned simulator execution","mounted UI success","Apple cleanup"],
      "elapsedSeconds":time.monotonic()-started}
if __name__=="__main__":
    result=main()
    print(json.dumps(result,sort_keys=True))

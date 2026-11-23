#!/usr/bin/env python3
"""Static Page menu source audit only. No product import, build or test method."""
import argparse, ast, hashlib, json, os, pathlib, stat, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[3]
N="docs/validation/20261123-semantic-page-menu-selector"
BASE="5180bc5fd4b1d45475ad068153257fce4ae0e169"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args):
 return subprocess.run(["git","-C",str(ROOT),*args],capture_output=True,check=True,
  timeout=20,env={**os.environ,"GIT_OPTIONAL_LOCKS":"0"}).stdout
def regular(relative):
 p=ROOT/relative;s=p.lstat()
 assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and p.resolve()==p and s.st_size<1024**2,relative
 return p.read_bytes(),s
def functions(raw):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--expected-head",required=True);args=parser.parse_args()
 head=git("rev-parse","HEAD").decode().strip()
 assert head==args.expected_head and len(head)==40
 assert not git("status","--porcelain=v1").strip()
 meta={}
 for name in ["source-check.py","source-inputs.json","source-inverse.json"]:
  relative=N+"/"+name;raw,_=regular(relative);assert raw==git("show",head+":"+relative)
  meta[relative]={"sha256":sha(raw),"bytes":len(raw)}
 manifest=json.loads(regular(N+"/source-inputs.json")[0]);inverse=json.loads(regular(N+"/source-inverse.json")[0])
 assert manifest["base"]==inverse["base"]==BASE
 assert len(manifest["inputs"])==19 and len({x["path"] for x in manifest["inputs"]})==19
 observed={}
 for row in manifest["inputs"]:
  raw,s=regular(row["path"]);assert raw==git("show",head+":"+row["path"])
  assert sha(raw)==row["sha256"] and len(raw)==row["bytes"] and stat.S_IMODE(s.st_mode)==row["physical_mode"]
  assert sha(git("show",BASE+":"+row["path"]))==row["git_base_sha256"]
  observed[row["path"]]={"sha256":sha(raw),"bytes":len(raw),"physical_mode":stat.S_IMODE(s.st_mode),
   "inode":str(s.st_ino),"git_mode":git("ls-tree",head,"--",row["path"]).split()[0].decode()}
 ui=inverse["ui"];current=regular(ui["path"])[0];prior=git("show",BASE+":"+ui["path"])
 assert sha(current)==ui["after_sha256"] and sha(prior)==ui["before_sha256"]
 assert current.decode().count(ui["after"])==1
 assert current.decode().replace(ui["after"],ui["before"],1).encode()==prior
 plan=inverse["plan"];raw=regular(plan["path"])[0];value=json.loads(raw)
 assert sha(raw)==plan["after_sha256"]
 restored=json.loads(raw);restored["candidate_ui_sha256"]=plan["before_ui_sha256"]
 restored["files"][ui["path"]]["sha256"]=plan["before_ui_sha256"]
 restored["files"][ui["path"]]["bytes"]=plan["before_ui_bytes"]
 assert (json.dumps(restored,sort_keys=True,indent=2)+"\n").encode()==git("show",BASE+":"+plan["path"])
 assert value["candidate_ui_sha256"]==sha(current)
 assert value["files"][ui["path"]]["sha256"]==sha(current) and value["files"][ui["path"]]["bytes"]==len(current)
 assert value["fresh_setup_new_acceptance_credit"]==0 and len(value["files"])==9
 app={}
 for name,row in value["files"].items():
  original=git("show",value["app_commit"]+":"+name)
  assert sha(original)==row["original_sha256"]
  if name!=ui["path"]: assert sha(regular(name)[0])==row["sha256"]==row["original_sha256"]
  app[name]={"original_sha256":sha(original),"original_bytes":len(original)}
 profile=inverse["profile"];praw=regular(profile["path"])[0];old=git("show",BASE+":"+profile["path"])
 assert sha(praw)==profile["after_sha256"] and sha(old)==profile["before_sha256"]
 restored_profile=praw.decode()
 for row in profile["constant_replacements"]:
  before=row["name"]+' = "'+row["before"]+'"';after=row["name"]+' = "'+row["after"]+'"'
  assert restored_profile.count(after)==1;restored_profile=restored_profile.replace(after,before,1)
 assert restored_profile.encode()==old and functions(praw)==functions(old)
 assignments={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(praw).body
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {"PLAN_SHA256","UI_SHA256"}}
 assert assignments=={"PLAN_SHA256":sha(raw),"UI_SHA256":sha(current)}
 changed=git("diff","--name-only",BASE,head).decode().splitlines()
 production=[x for x in changed if not x.startswith(N+"/")]
 assert set(production)=={ui["path"],plan["path"],profile["path"]}
 print(json.dumps({"schema":"pinkha-page154-menu-selector-static-source-check-v1","status":"PASS","head":head,
  "base":BASE,"source_inputs":observed,"metadata_inputs":meta,"original_app_plan_inputs":app,
  "whole_swift_inverse":True,"plan_three_field_inverse":True,"profile_two_constant_inverse":True,
  "profile_functions_unchanged":len(functions(praw)),"changed_source_paths":production,
  "unchanged_mounted_journey_and_other_helpers":True,"executed_product_imports":0,"test_methods":0,
  "builds":0,"apple_typecheck":"NOT_RUN","actual_menu_behavior":"NOT_RUN"},sort_keys=True))
if __name__=="__main__":main()

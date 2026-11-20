#!/usr/bin/env python3
"""Verify retained Apple evidence bytes and exact case identities; never execute Apple tests."""
from pathlib import Path
import argparse,gzip,hashlib,io,json,re,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[2]
REL="docs/cross-app-original-editor-apple-result-44722898086-20261120"
SOURCE="11bfb0db63d7d446be01d0b2b70ac9cadc471a7f"
p=argparse.ArgumentParser();p.add_argument("--git-ref");a=p.parse_args()
def blob(path,ref):
 return subprocess.run(["git","-C",str(ROOT),"show",ref+":"+path],capture_output=True,check=True).stdout
def local(path):
 return blob(REL+"/"+path,a.git_ref) if a.git_ref else (ROOT/REL/path).read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def js(path):return json.loads(local(path))
manifest=js("MANIFEST.json")
for f in manifest["files"]:
 b=local(f["path"]);assert len(b)==f["bytes"] and sha(b)==f["sha256"],f["path"]
archive=local("raw/github-artifact-14626073558.zip")
assert len(archive)==740218 and sha(archive)=="59ff3051e4036168d5c7d77475a8225d75ef71543e8ca9797fee2aaf6bc77a82"
with zipfile.ZipFile(io.BytesIO(archive)) as z:
 assert z.testzip() is None and z.namelist()==["Pinkha-Native-Derived-Evidence.zip"]
 inner=z.read(z.namelist()[0])
assert sha(inner)=="5cc72e5f02bb57c6e76a46c061cf582e2dfd90bbf615b95c06dd3dbe719faa8c"
with zipfile.ZipFile(io.BytesIO(inner)) as z:
 assert z.testzip() is None
 entries=js("DERIVED_ARCHIVE_VERIFIED.json")["files"]
 assert len(entries)==86
 assert {f["path"] for f in entries}=={i.filename for i in z.infolist() if not i.is_dir()}
 for f in entries:
  b=z.read(f["path"]);assert len(b)==f["bytes"] and sha(b)==f["sha256"]
 def raw(path):return json.loads(z.read(path))
 e=raw("execution.json");summary=raw("original-editor-summary.json");tests=raw("original-editor-tests.json")
 profile=json.loads(blob("Tools/Hanlin/original_editor_profile.json",SOURCE))
 required={s+"/"+m+"()" for s,v in profile["suites"].items() for m in v["methods"]}
 assert len(required)==profile["required_methods"]==16
 actual={}
 def walk(n):
  assert n["nodeType"] in ["Test Plan","Unit test bundle","Test Suite","Test Case"] and n["result"]=="Passed"
  if n["nodeType"]=="Test Case":
   key=n["nodeIdentifier"];assert key not in actual and not n.get("children");actual[key]=n["result"]
  else:
   assert n.get("children")
   for c in n["children"]:walk(c)
 for n in tests["testNodes"]:walk(n)
 assert set(actual)==required and actual==e["actual"]["actual_cases"]
 assert (summary["totalTestCount"],summary["passedTests"],summary["failedTests"],summary["skippedTests"],summary["expectedFailures"])==(16,16,0,0,0)
 assert e["source_sha"]==SOURCE and e["run_id"]=="44722898086" and e["run_attempt"]=="1"
 assert e["status"]=="ORIGINAL_EDITOR_COMPONENT_PASS" and e["build_succeeded"] and e["test_command_exit_code"]==0 and e["post_execution_source_verified"]
 assert sha(z.read("original-editor-summary.json"))==e["raw_summary_sha256"] and sha(z.read("original-editor-tests.json"))==e["raw_tests_sha256"]
 for v in profile["suites"].values():assert sha(blob(v["path"],SOURCE))==v["sha256"]==e["test_source_hashes"][v["path"]]
 for name,want in profile["application_trees"].items():
  for ref in (SOURCE,profile["application_base"]):
   got=subprocess.run(["git","-C",str(ROOT),"rev-parse",ref+":"+name],capture_output=True,check=True).stdout.decode().strip();assert got==want
 pins=json.loads(blob("Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",SOURCE))
 assert pins["pins"]==raw("actual-package-pins.json")["pins"] and len(pins["pins"])==44
 assert raw("heart-source/original-heart-download.json")["outer_zip_sha256"]==profile["heart"]["zip_sha256"]
 assert raw("heart/heart-installation.json")["status"]=="PASS"
 assert raw("heart/heart-installation.json")["archive_sha256"]==raw("heart-source/original-heart-download.json")["inner_archive_sha256"]
 assert all(raw("command-%02d.json"%i)["exit_code"]==0 for i in range(5))
log=gzip.decompress(local("raw/JOB.log.gz")).decode()
host=[l for l in log.splitlines() if re.search(r"\btest_\w+ \(",l)]
assert len(host)==74 and all(l.endswith(" ... ok") for l in host)
assert len([l for l in host if "SDKCommandProcessTests." in l])==2
run=json.loads(gzip.decompress(local("raw/RUN.json.gz")))
assert (run["id"],run["head_sha"],run["run_attempt"],run["conclusion"])==(44722898086,SOURCE,1,"success")
print(json.dumps({"status":"PASS_RETAINED_APPLE_COMPONENT_EVIDENCE_ONLY","source":SOURCE,"sealed_files":len(manifest["files"]),"raw_derived_files":86,"actual_component_tests_passed":16,"failed":0,"skipped":0,"host_controls_passed":74,"new_tests_executed_by_verifier":0,"ui_journeys":0,"git_ref":a.git_ref}))

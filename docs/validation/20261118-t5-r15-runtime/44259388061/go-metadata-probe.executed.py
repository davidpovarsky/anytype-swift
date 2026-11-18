import hashlib,io,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf8")
root=Path(r"C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118")
proof=root/"docs/validation/20261118-t5-r15-runtime/44259388061"
if shutil.disk_usage(root).free < 128*1024*1024: raise RuntimeError("Insufficient small-probe disk margin")
sys.path.insert(0,str(root/"Tools/PinkhaNativeDerived"))
import r15_runtime_go as launcher
go=Path(r"C:/Users/DAVID/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.5.windows-amd64/bin/go.exe")
if not go.is_file(): raise RuntimeError("Pinned cached Go executable is missing")
work=Path(r"C:/ProgramData/SentinelX/uploads/chatgpt-t5-20261118-probes/genproto-scope-44259388061")
work.mkdir(parents=True,exist_ok=False)
env=dict(os.environ,GOWORK="off",GOTOOLCHAIN="local",GOPROXY="off",GOSUMDB="off",
         GOFLAGS="-mod=readonly",GOMODCACHE=str(work/"modcache"),GOCACHE=str(work/"buildcache"))
commands=[]
def run(args,cwd,active=env):
 p=subprocess.run([str(go),*args],cwd=cwd,env=active,capture_output=True,timeout=30)
 commands.append(dict(argv=args,cwd=str(cwd.relative_to(work)),returncode=p.returncode,
                      stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()))
 if p.returncode: raise RuntimeError(p.stderr.decode("utf8","replace"))
 return p.stdout.decode("utf8")
version=run(["version"],work).strip()
if not version.startswith("go version go1.26.5 "): raise RuntimeError("Wrong metadata toolchain")
outer_path=Path(r"C:/Users/DAVID/Code/anytype-wave15-evidence-20261118/r15-44259388061/artifact-14410966676.zip")
outer_bytes=outer_path.read_bytes()
if hashlib.sha256(outer_bytes).hexdigest()!="30a3a032db1f753d229ea85d025ad5b1af816d0211a408d71eb6807120a1e368": raise RuntimeError("Original artifact changed")
outer=zipfile.ZipFile(io.BytesIO(outer_bytes))
inner_bytes=outer.read("Pinkha-Native-Derived-Evidence.zip")
inner=zipfile.ZipFile(io.BytesIO(inner_bytes))
captured=json.loads(inner.read("runtime/generated-original-input.json"))
captured_dir=work/"captured-generated-original"
captured_dir.mkdir()
captured_raw=captured["go_mod_text"].encode("utf8")
(captured_dir/"go.mod").write_bytes(captured_raw)
if hashlib.sha256(captured_raw).hexdigest()!=captured["initial_go_mod_sha256"]: raise RuntimeError("Captured original seed bytes differ")
manifest=json.loads(run(["mod","edit","-json"],captured_dir))
expected=json.loads(inner.read("runtime/generated-graph-original-manifest.log"))
if launcher.canonical_manifest(manifest)!=launcher.canonical_manifest(expected): raise RuntimeError("Captured original manifest did not reproduce")
actual_override=launcher.prepare_generated_genproto_override(go,env,captured_dir,manifest)
(proof/"captured-seed-metadata-override.json").write_text(json.dumps(actual_override,indent=2)+"\n",encoding="utf8",newline="\n")
# These are locally authored synthetic modules. Their hashes are NOT real genproto checksums.
old="v0.0.0-20240903143218-8af14fe29dc1"
reviewed=launcher.VERSION
raised="v0.0.0-20260128011058-8636f8732409"
proxy=work/"synthetic-file-proxy"
module_dir=proxy/"google.golang.org/genproto/@v"
module_dir.mkdir(parents=True)
module_text="module "+launcher.GENPROTO+"\n\ngo 1.26.5\n"
for v in [reviewed,raised]:
 (module_dir/(v+".mod")).write_text(module_text,encoding="utf8",newline="\n")
 (module_dir/(v+".info")).write_text(json.dumps(dict(Version=v,Time=("2024-10-21T21:41:15Z" if v==reviewed else "2026-01-28T01:10:58Z"))),encoding="utf8")
 with zipfile.ZipFile(module_dir/(v+".zip"),"w") as output:
  output.writestr(launcher.GENPROTO+"@"+v+"/go.mod",module_text)
  output.writestr(launcher.GENPROTO+"@"+v+"/fixture.go","package fixture\n")
(module_dir/"list").write_text(reviewed+"\n"+raised+"\n",encoding="utf8",newline="\n")
consumer=work/"consumer"
consumer.mkdir()
(consumer/"go.mod").write_text("module example.test/consumer\n\ngo 1.26.5\n\nrequire "+launcher.GENPROTO+" "+raised+"\n",encoding="utf8",newline="\n")
original=("module gobind\n\ngo 1.26.5\n\nrequire example.test/consumer v1.0.0\n\n"
          +"replace example.test/consumer => "+json.dumps(str(consumer))+"\n"
          +"replace "+launcher.GENPROTO+" "+old+" => "+launcher.GENPROTO+" "+reviewed+"\n")
active=dict(env,GOPROXY=proxy.as_uri())
phases={}
for phase in ["version-qualified","reviewed-versionless"]:
 cwd=work/phase
 cwd.mkdir()
 (cwd/"go.mod").write_text(original,encoding="utf8",newline="\n")
 original_manifest=json.loads(run(["mod","edit","-json"],cwd,active))
 if phase=="reviewed-versionless":
  receipt=launcher.prepare_generated_genproto_override(go,env,cwd,original_manifest)
  phases[phase]={"override":receipt}
 else:
  phases[phase]={}
 download=run(["mod","download","-json","all"],cwd,active)
 selected=launcher.module_records(run(["list","-m","-json","all"],cwd,active))
 genproto=next(item for item in selected if item["Path"]==launcher.GENPROTO)
 phases[phase].update(selected=genproto,download_records=launcher.module_records(download),
                      final_manifest=json.loads(run(["mod","edit","-json"],cwd,active)))
if phases["version-qualified"]["selected"].get("Version")!=raised or "Replace" in phases["version-qualified"]["selected"]:
 raise RuntimeError("Counterexample failed to reproduce the selected-version escape")
fixed=phases["reviewed-versionless"]["selected"]
if fixed.get("Version")!=raised or fixed.get("Replace",{}).get("Version")!=reviewed:
 raise RuntimeError("Versionless override failed to retain the reviewed effective revision")
receipt=dict(status="PASS_METADATA_ONLY",scope="SYNTHETIC_LOCAL_FILE_PROXY_NOT_NATIVE_DEPENDENCY_CHECKSUM_ACCEPTANCE",
             go_version=version,native_compiles=0,native_tests=0,network_downloads=0,
             captured_original_seed_sha256=captured["initial_go_mod_sha256"],
             captured_exact_original_manifest=True,captured_actual_go_edit_override="PASS",
             phases=phases,commands=commands,
             created_file_bytes=sum(p.stat().st_size for p in work.rglob("*") if p.is_file()))
(proof/"go-metadata-probe.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8",newline="\n")
print(json.dumps({k:receipt[k] for k in ["status","scope","go_version","native_compiles","native_tests","network_downloads","captured_exact_original_manifest","captured_actual_go_edit_override","created_file_bytes"]}))
print(json.dumps({"before_selected":phases["version-qualified"]["selected"]["Version"],"before_replace":phases["version-qualified"]["selected"].get("Replace"),"after_selected":fixed["Version"],"after_effective":fixed["Replace"]["Version"],"free_bytes":shutil.disk_usage(root).free}))

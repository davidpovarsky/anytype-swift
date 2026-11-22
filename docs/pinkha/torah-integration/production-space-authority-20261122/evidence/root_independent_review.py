import json,hashlib,subprocess,datetime,re
from pathlib import Path
R=Path(r"C:\Users\DAVID\Code\anytype-original-space-authority-20261122")
D=R/"docs/pinkha/torah-integration/production-space-authority-20261122/controls"
T=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-spaceview-authority-controls-20261122")
O=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\space22_root_review.json")
B="b854e7f3f59690134bcabdef88527b61517d5ab5"
S="37731bcfdfda320b3a58356b54719e904c399810"
def sha(b):return hashlib.sha256(b).hexdigest()
def g(*a):
 p=subprocess.run(["git","-c","core.autocrlf=false",*a],cwd=R,capture_output=True,timeout=120)
 assert p.returncode==0,p.stderr.decode("utf-8","replace")
 return p.stdout
def block(text,head):
 start=text.index(head);i=text.index("{",start);depth=0
 for end in range(i,len(text)):
  if text[end]=="{":depth+=1
  elif text[end]=="}":
   depth-=1
   if depth==0:return text[start:end+1]
 raise AssertionError(head)
manifest_raw=(D/"INPUTS.json").read_bytes();m=json.loads(manifest_raw)
execution_raw=(T/"EXECUTION.json").read_bytes();e=json.loads(execution_raw)
result_raw=(T/"RESULT.json").read_bytes();result=json.loads(result_raw)
assert sha(manifest_raw)==e["manifest_sha256"]=="ec5f6d491381c3835ccb4e4913ae14ae1cc8d253d238c8149f3819b9db3e38b8"
assert sha(execution_raw)=="2a010a4883b50de9b2a6dd54618990512916c2c1fdff00c872dee140c87a46e2"
assert sha(result_raw)==e["result_sha256"]=="17ce9bb5ba8402869aec112c7ad2d9dbe5d6044df47ed0ec6fcb9c6bfce00dee"
assert g("rev-parse",S+"^").decode().strip()==B
assert g("diff","--name-only",B,S).decode().splitlines()==[m["product_path"]]
source=g("show",S+":"+m["product_path"]);assert source==(R/m["product_path"]).read_bytes()
assert sha(source)==m["candidate_sha256"]==e["candidate_sha256"]==result["candidateSHA256"]=="f1570f8cff28d87152ea455ded6bc0bdfeb729e0beb3a70e3a47fb06b4710a57"
canonical={}
assert len(m["source_inputs"])==len(e["source_inputs"])==12
for row in m["source_inputs"]:
 raw=g("show",B+":"+row["path"])
 assert sha(raw)==row["sha256"]
 assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==row["git_blob"]
 canonical[row["path"]]=raw
compiled={}
assert len(m["swift_inputs"])==len(e["compiled_inputs"])==7
for row,actual in zip(m["swift_inputs"],e["compiled_inputs"]):
 assert all(actual[k]==v for k,v in row.items())
 raw=Path(actual["compiled_path"]).read_bytes()
 assert raw==(D/row["name"]).read_bytes() and sha(raw)==row["sha256"] and len(raw)==row["bytes"]
 compiled[row["name"]]=raw
def canonical_suffix(suffix):
 matches=[v for k,v in canonical.items() if k.endswith(suffix)]
 assert len(matches)==1
 return matches[0]
assert compiled["Lifetime.swift"]==canonical_suffix("EditorDocumentWriteLifetime.swift")
assert compiled["Binding.swift"]==canonical_suffix("InvocationDispatchBinding.swift")
owner=canonical_suffix("EditorDocumentWriteOwner.swift").decode()
for head in ["enum EditorDocumentWriteRejection:","enum EditorDocumentWriteError:","struct EditorDocumentWriteCapture:"]:
 assert block(compiled["Capture.swift"].decode(),head)==block(owner,head)
account=canonical_suffix("AccountManager.swift").decode()
for head in ["protocol AccountManagerProtocol:","extension AccountManagerProtocol {","final class AccountManager:"]:
 assert block(compiled["AccountManager.swift"].decode(),head)==block(account,head)
src=source.decode();projection=compiled["SpaceViewsStorageProjection.swift"].decode()
heads=["struct OriginalSpaceViewPermission:","private final class OriginalSpaceViewSubscriptionAttempt:","private final class OriginalSpaceViewStopAttempt:","private struct OriginalSpaceViewPermissionState {","private struct OriginalSpaceViewSubscriptionLifecycle {","protocol SpaceViewsStorageProtocol:","actor SpaceViewsStorage:"]
for head in heads:assert block(src,head)==block(projection,head),head
actor_declaration_sha256=sha(block(src,"actor SpaceViewsStorage:").encode())
native_view=canonical_suffix("Models/SpaceView.swift").decode();probe=compiled["PortableDependencyProbes.swift"].decode()
for name in ["isActive","isLegacyStream"]:
 fragment=block(native_view,"var "+name+":")
 assert fragment==block(probe,"var "+name+":")
assert e["selected_count"]==e["completed_controls"]==len(result["results"])==22 and e["all_passed"]
assert [x["name"] for x in result["results"]]==m["expected_controls"]==e["expected_controls"]
assert all(x["status"]=="PASS" for x in result["results"])
assert result["processID"]==31264 and not result["priorSuitesRerun"] and result["originalNativeCalls"]==0
for c in e["commands"]:
 assert c["exit_code"]==0 and not c["timeout"]
 for stream in ["stdout","stderr"]:assert sha((T/(c["name"]+"."+stream)).read_bytes())==c[stream+"_sha256"]
compiler=Path(e["compiler_path"]);assert sha(compiler.read_bytes())==e["compiler_sha256"]
binary=Path(next(x for x in e["commands"] if x["name"]=="execute")["command"][0])
assert sha(binary.read_bytes())==e["binary_sha256"]=="29bdcdcdcb18a71a490f8d79581bdb9c00ef4c473d847d5af07c52a8df626f04"
stdout=(T/"execute.stdout").read_text(encoding="utf-8")
assert stdout.splitlines()==["PASS "+name for name in m["expected_controls"]]
warnings=(T/"compile.stderr").read_text(encoding="utf-8")
warning_lines=[line for line in warnings.splitlines() if re.search(r":\d+:\d+: warning:",line)]
assert len(warning_lines)==22 and all("Controls.swift:" in line for line in warning_lines)
report={"status":"INDEPENDENT_ROOT_SOURCE_AND_EXECUTION_REVIEW_PASS","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":S,"base":B,
 "product_sha256":m["candidate_sha256"],"execution_sha256":sha(execution_raw),"result_sha256":sha(result_raw),
 "canonical_git_inputs_verified":12,"compiled_inputs_verified":7,"actual_actor_and_seven_declarations_exact":True,
 "actual_actor_declaration_sha256":actor_declaration_sha256,"actual_original_capture_enums_account_lifetime_binding_verified":True,"actual_space_predicate_fragments_verified":True,
 "cases":m["expected_controls"],"passed":22,"failed":0,"binary_sha256":e["binary_sha256"],"compiler_sha256":e["compiler_sha256"],
 "language_mode":"Swift 5 with strict-concurrency complete; Swift6.3.3 toolchain","fixture_warnings":22,
 "source_review":"All full assertion and probe bodies independently read; no fixture warning in product projection",
 "review_reexecuted_tests":False,"native_decoder_rpc_combine_apple_or_full_space_authority_qualified":False}
assert not O.exists();O.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(json.dumps({"status":report["status"],"path":str(O),"sha256":sha(O.read_bytes()),"cases":22,"source_inputs":12,"compiled":7}),flush=True)

from pathlib import Path
import ast,hashlib,json,re,subprocess,sys,datetime
root=Path.cwd()
evidence=root/"docs/any-engine-port/evidence/20261120/native-hosted-tests-harness-v3"
assert not evidence.exists(),"Use a new evidence receipt rather than overwrite one"
evidence.mkdir(parents=True)
source=root/"docs/any-engine-port/evidence/20261119/native-hosted-tests-harness-v1/verify_hosted_harness.py"
old_verifier=source.read_text(encoding="utf-8")
parser_text=old_verifier[old_verifier.index("token=re.compile"):old_verifier.index("def sha(")]
ns={"re":re,"json":json}
exec(parser_text,ns)
parse=ns["parse_openstep"]
base="57c116e02ee6dbce21f3bbffcc297841d2bd1235"
def gitblob(path):
 return subprocess.check_output(["git","show",base+":"+path],cwd=root)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
checks=[]
project_rel="NativeApp/AnyNative.xcodeproj/project.pbxproj"
current_path=root/project_rel
before=parse(gitblob(project_rel).decode("utf-8"))
after=parse(current_path.read_text(encoding="utf-8"))
check({k:v for k,v in before.items() if k!="objects"}=={k:v for k,v in after.items() if k!="objects"},"project root metadata unchanged")
a,b=before["objects"],after["objects"]
added={"B10000000000000000000005","B10000000000000000000006","B20000000000000000000008","B20000000000000000000009"}
changed={"B30000000000000000000002","B40000000000000000000004"}
check(set(b)-set(a)==added and not(set(a)-set(b)),"exactly four added file/build objects; none removed")
check({k for k in a if a[k]!=b[k]}==changed,"only hosted sources group and phase changed")
for ident,field,expected in [
("B30000000000000000000002","children",["B20000000000000000000008","B20000000000000000000009"]),
("B40000000000000000000004","files",["B10000000000000000000005","B10000000000000000000006"])]:
 check({k:v for k,v in a[ident].items() if k!=field}=={k:v for k,v in b[ident].items() if k!=field},ident+" metadata retained")
 check(b[ident][field]==a[ident][field]+expected,ident+" preserves original ordered references")
for build,file,name in [
("B10000000000000000000005","B20000000000000000000008","NativeDocumentPublicationTests.swift"),
("B10000000000000000000006","B20000000000000000000009","NativePropertyWorkflowTests.swift")]:
 check(b[build]=={"isa":"PBXBuildFile","fileRef":file},"correct build reference "+name)
 expected="../Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/"+name
 check(b[file]=={"isa":"PBXFileReference","lastKnownFileType":"sourcecode.swift","path":expected,"sourceTree":"<group>"},"correct file reference "+name)
 check((root/"NativeApp"/expected).is_file(),"source exists "+name)
sys.path.insert(0,str(root/"Tools/AnyEnginePort"))
from verify_native_test_execution import PROFILES,SOURCE_PATHS,expected_methods
check(len(expected_methods("application"))==9,"nine required hosted named methods")
check(len(expected_methods("ui-ios"))==18,"eighteen required UIKit/property methods")
expected_new={"NativeDocumentPublicationTests":3,"NativePropertyWorkflowTests":1}
for suite,count in expected_new.items():
 rel="Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/"+suite+".swift"
 text=(root/rel).read_text(encoding="utf-8")
 declared=re.findall(r"^\s+func\s+(test\w+)\s*\(",text,re.M)
 check(set(declared)==set(PROFILES["application"][suite]) and len(declared)==count,"exact named test registration "+suite)
 check(rel in SOURCE_PATHS["application"],"source bound by acceptance gate "+suite)
unchanged=[
"Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeApplicationTests.swift",
"Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeHanlinCreationTests.swift",
"Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeTorahWorkflowTests.swift",
"NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeHostedTests.xcscheme",
"NativeApp/TestHost/AnyNativeTestHostApp.swift",
"NativeApp/TestHost/NativeTestHost.entitlements",
"NativeApp/Info.plist"]
for rel in unchanged:
 check((root/rel).read_bytes().replace(b"\r\n",b"\n")==gitblob(rel).replace(b"\r\n",b"\n"),"baseline bytes retained "+rel)
for rel in ["Tools/AnyEnginePort/verify_native_test_execution.py","Tools/AnyEnginePort/test_native_execution_gate.py","Tools/AnyEnginePort/prepare_native_runtime.py"]:
 ast.parse((root/rel).read_text(encoding="utf-8"))
 check(True,"Python parse "+rel)
inputs=[project_rel]+SOURCE_PATHS["application"]+unchanged[3:]+["Tools/AnyEnginePort/verify_native_test_execution.py","Tools/AnyEnginePort/test_native_execution_gate.py","Tools/AnyEnginePort/prepare_native_runtime.py"]
workflow_rel='.github/workflows/pinkha-any-engine-port.yml'
workflow=(root/workflow_rel).read_text(encoding='utf-8')
block0="      - name: Publish lifecycle diagnostic log\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: any-engine-port-lifecycle-diagnostic-${{ github.sha }}\n          path: |\n            build/any-patched-evidence/runtime.log\n            build/any-patched-evidence/source-sha.txt\n            build/any-patched-evidence/native-source.json\n            build/any-patched-evidence/xcode-version.txt\n            build/any-patched-evidence/simulator.json\n          retention-days: 14\n          if-no-files-found: warn\n"
check(workflow.count(block0)==1,'early diagnostic block 0 appears once')
workflow=workflow.replace(block0,'')
block1="      - name: Publish hosted application diagnostic log\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: any-engine-port-application-diagnostic-${{ github.sha }}\n          path: |\n            build/any-patched-evidence/application.log\n            build/any-patched-evidence/source-sha.txt\n            build/any-patched-evidence/native-source.json\n            build/any-patched-evidence/xcode-version.txt\n            build/any-patched-evidence/simulator.json\n          retention-days: 14\n          if-no-files-found: warn\n"
check(workflow.count(block1)==1,'early diagnostic block 1 appears once')
workflow=workflow.replace(block1,'')
check(workflow==gitblob(workflow_rel).decode('utf-8').replace('\r\n','\n'),'all existing CI commands and guards unchanged')
inputs.append(workflow_rel)
record={"schemaVersion":3,"status":"PASS","scope":"source_structure_and_registration_only","actualAppleExecution":False,"baselineCommit":base,"timestampUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"checks":checks,"checkCount":len(checks),"inputs":{p:sha(root/p) for p in dict.fromkeys(inputs)},"parserSource":str(source.relative_to(root)).replace("\\","/"),"parserSourceSHA256":sha(source),"requiredApplicationMethods":sorted(expected_methods("application"))}
(evidence/"result.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8",newline="\n")
(evidence/"project.pbxproj").write_bytes(current_path.read_bytes())
(evidence/"verify_hosted_harness.py").write_bytes(Path(__file__).read_bytes())
for rel in inputs:
 target=evidence/"inputs"/rel
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes((root/rel).read_bytes())
(evidence/"baseline-project.pbxproj").write_bytes(gitblob(project_rel))
print(json.dumps({"status":"PASS","scope":record["scope"],"checks":len(checks),"resultSHA256":sha(evidence/"result.json"),"evidence":str(evidence.relative_to(root))}))

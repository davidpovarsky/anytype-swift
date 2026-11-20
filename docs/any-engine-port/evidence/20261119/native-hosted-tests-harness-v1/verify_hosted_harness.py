from pathlib import Path
import hashlib,json,re,plistlib,xml.etree.ElementTree as ET,datetime,subprocess
root=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
scratch=root/"build/any-engine-port/native-hosted-tests-harness-v1"
evidence=root/"docs/any-engine-port/evidence/20261119/native-hosted-tests-harness-v1"
evidence.mkdir(parents=True,exist_ok=True)
token=re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,"]+',re.S)
def parse_openstep(text):
 matches=list(token.finditer(text))
 assert "".join(m.group(0) for m in matches)==text,"Tokenizer coverage"
 items=[m.group(0) for m in matches if not m.group(0).isspace() and not m.group(0).startswith(("//","/*"))]
 at=0
 def take(expected=None):
  nonlocal at
  assert at<len(items),"Unexpected end of OpenStep property list"
  value=items[at];at+=1
  if expected is not None: assert value==expected,(value,expected)
  return value
 def value():
  if items[at]=="{":
   take("{");out={}
   while items[at]!="}":
    key=take()
    if key.startswith('"'):key=json.loads(key)
    assert key not in out,"Duplicate dictionary key "+key
    take("=");out[key]=value();take(";")
   take("}");return out
  if items[at]=="(":
   take("(");out=[]
   while items[at]!=")":
    out.append(value())
    if items[at]==",":take(",")
    else:assert items[at]==")"
   take(")");return out
  x=take()
  return json.loads(x) if x.startswith('"') else x
 result=value()
 assert at==len(items)
 return result
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
project_path="NativeApp/AnyNative.xcodeproj/project.pbxproj"
project=parse_openstep((root/project_path).read_text(encoding="utf-8"))
before=parse_openstep((scratch/"project.before.pbxproj").read_text(encoding="utf-8"))
objects=project["objects"];before_objects=before["objects"]
checks=[]
def check(name,condition):
 assert condition,name
 checks.append(name)
check("OpenStep project parsed with all unique dictionary keys",len(objects)>len(before_objects))
allowed={"A30000000000000000000001","A30000000000000000000002","A60000000000000000000001","AA0000000000000000000001"}
check("Existing app and UI-test target/source/framework/configuration objects unchanged",
      all(objects[k]==v for k,v in before_objects.items() if k not in allowed))
debug=dict(objects["AA0000000000000000000001"]["buildSettings"])
check("Only project Debug build-setting change is ONLY_ACTIVE_ARCH=YES",
      debug.pop("ONLY_ACTIVE_ARCH",None)=="YES" and debug==before_objects["AA0000000000000000000001"]["buildSettings"])
def walk(v):
 if isinstance(v,dict):
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
 else:yield v
check("Every project object reference resolves",
 all(v in objects for v in walk(project) if re.fullmatch(r"[AB][0-9A-F]{23}",v)))
p=objects[project["rootObject"]]
host=objects["B50000000000000000000001"];tests=objects["B50000000000000000000002"]
check("Exactly the original two and the new two native targets",len(p["targets"])==4 and set(p["targets"])=={
"A50000000000000000000001","A50000000000000000000002","B50000000000000000000001","B50000000000000000000002"})
check("Hosted tests are a unit-test bundle and depend only on dedicated host",
 tests["productType"]=="com.apple.product-type.bundle.unit-test" and
 [objects[x]["target"] for x in tests["dependencies"]]==["B50000000000000000000001"])
check("Host has no package-product or target dependencies",host["packageProductDependencies"]==[] and host["dependencies"]==[])
def phases(t,isa):return [objects[x] for x in t["buildPhases"] if objects[x]["isa"]==isa]
sources=phases(tests,"PBXSourcesBuildPhase")[0]["files"]
source_paths=[objects[objects[x]["fileRef"]]["path"] for x in sources]
original=json.loads((scratch/"original-inputs.json").read_text(encoding="utf-8"))
original_tests=[x for x in original if x["path"].endswith(".swift")]
check("Tests reference the original three files directly, without a copy",
 set(source_paths)=={"../"+x["path"] for x in original_tests} and len(source_paths)==3)
check("All original test bytes and main NativeLaunch scheme remain unchanged",
 all(sha(root/x["path"])==x["sha256"] for x in original))
methods=[]
imports=set()
for x in original_tests:
 text=(root/x["path"]).read_text(encoding="utf-8")
 methods+=re.findall(r"\bfunc (test[A-Za-z0-9_]+)\s*\(",text)
 imports|=set(re.findall(r"^(?:@testable )?import ([A-Za-z0-9_]+)",text,re.M))
expected_methods={
"testRealAccountWorkspaceJournalEditorAndColdReopen",
"testPostAuthKeychainFailureRevokesNativeAuthorityAndRecoversSameAccount",
"testRealKeychainNamespaceAndRecoveryMetadataIsolation",
"testRealProtectedHanlinCreationDenialCommitDuplicateAndRevocation",
"testNativeQuotesNotesRelatedIndexUnlinkAndRuntimeReopen"}
check("All five unchanged original XCTest methods included",len(methods)==5 and set(methods)==expected_methods)
products=[objects[x] for x in tests["packageProductDependencies"]]
framework_products=[objects[x]["productRef"] for x in phases(tests,"PBXFrameworksBuildPhase")[0]["files"]]
check("All 13 imported library products are explicit framework dependencies",
 len(products)==13 and set(framework_products)==set(tests["packageProductDependencies"]) and
 imports-{"Foundation","XCTest","SwiftUI","UIKit"}=={x["productName"] for x in products})
for entry in products:
 pkg=objects[entry["package"]]
 if pkg["isa"]=="XCLocalSwiftPackageReference":
  path=(root/"NativeApp"/pkg["relativePath"]).resolve()
  check("Local package "+entry["productName"]+" exists",(path/"Package.swift").is_file())
 else:
  check("Remote TorahInspectorCore keeps exact pinned revision",
    entry["productName"]=="TorahInspectorCore" and
    pkg["repositoryURL"]=="https://github.com/davidpovarsky/TorahInspectorKit.git" and
    pkg["requirement"]=={"kind":"revision","revision":"4e59e909dd22685bb46f9396bc57e5f8c627d773"})
for cfg_id in objects[tests["buildConfigurationList"]]["buildConfigurations"]:
 cfg=objects[cfg_id];s=cfg["buildSettings"]
 check("Hosted "+cfg["name"]+" loader/runpath/module configuration",
   s["TEST_HOST"]=="$(BUILT_PRODUCTS_DIR)/PinkhaAnyNativeTestHost.app/PinkhaAnyNativeTestHost" and
   s["BUNDLE_LOADER"]=="$(TEST_HOST)" and s["PRODUCT_MODULE_NAME"]=="PinkhaAnyNativeTests" and
   s["CODE_SIGN_STYLE"]=="Automatic" and
   "@loader_path/Frameworks" in s["LD_RUNPATH_SEARCH_PATHS"])
for cfg_id in objects[host["buildConfigurationList"]]["buildConfigurations"]:
 cfg=objects[cfg_id];s=cfg["buildSettings"]
 check("Host "+cfg["name"]+" has private entitlements and real loopback Info.plist",
    s["PRODUCT_BUNDLE_IDENTIFIER"]=="io.pinkha.anynative.testhost" and
    s["CODE_SIGN_ENTITLEMENTS"]=="TestHost/NativeTestHost.entitlements" and
    s["CODE_SIGN_INJECT_BASE_ENTITLEMENTS"]=="YES" and s["INFOPLIST_FILE"]=="Info.plist")
rights=plistlib.loads((root/"NativeApp/TestHost/NativeTestHost.entitlements").read_bytes())
identity="$(AppIdentifierPrefix)$(PRODUCT_BUNDLE_IDENTIFIER)"
check("Host declares only its own application identifier/private Keychain group",
      rights=={"application-identifier":identity,"keychain-access-groups":[identity]})
host_source=(root/"NativeApp/TestHost/AnyNativeTestHostApp.swift").read_text(encoding="utf-8")
check("Host imports only SwiftUI and cannot bootstrap Any runtime",
 re.findall(r"^import (\w+)",host_source,re.M)==["SwiftUI"] and
 not any(x in host_source for x in ["AnyNativeApplication(","AnyEmbeddedRuntime.","AnyNativeRootView(",".task {"]))
info=plistlib.loads((root/"NativeApp/Info.plist").read_bytes())
check("Host reuses literal-loopback ATS exception without global opt-out",
 info["NSAppTransportSecurity"]=={"NSExceptionDomains":{"127.0.0.1":{"NSExceptionAllowsInsecureHTTPLoads":True}}})
scheme_path="NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeHostedTests.xcscheme"
scheme=ET.parse(root/scheme_path).getroot()
testables=scheme.findall("./TestAction/Testables/TestableReference")
check("Hosted scheme runs the entire original bundle with parallel test execution disabled",
 len(testables)==1 and testables[0].attrib=={"skipped":"NO","parallelizable":"NO"} and
 testables[0].find("BuildableReference").get("BlueprintIdentifier")=="B50000000000000000000002" and
 not scheme.findall(".//SkippedTests") and not scheme.findall(".//SelectedTests"))
check("Scheme launch and macro expansion reference dedicated host",
 scheme.find("./TestAction/MacroExpansion/BuildableReference").get("BlueprintIdentifier")=="B50000000000000000000001" and
 scheme.find("./LaunchAction/BuildableProductRunnable/BuildableReference").get("BlueprintIdentifier")=="B50000000000000000000001")
for ref in scheme.findall(".//BuildableReference"):
 target=objects[ref.get("BlueprintIdentifier")]
 check("Scheme reference "+ref.get("BlueprintName")+" resolves to exact product",
    target["name"]==ref.get("BlueprintName") and objects[target["productReference"]]["path"]==ref.get("BuildableName"))
conventions=root/"Anytype.xcodeproj/project.pbxproj"
ct=conventions.read_text(encoding="utf-8")
convention_lines=[{"line":i,"text":line.strip()} for i,line in enumerate(ct.splitlines(),1)
 if "BUNDLE_LOADER" in line or "TEST_HOST =" in line]
check("Existing repository already uses application-hosted XCTest settings",
 any('BUNDLE_LOADER = "$(TEST_HOST)"' in x["text"] for x in convention_lines) and
 any("Anytype.app/Anytype" in x["text"] for x in convention_lines))
diff=subprocess.run(["git","diff","--check","--",project_path,scheme_path,"NativeApp/TestHost"],
 cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
(scratch/"git-diff-check.log").write_bytes(diff.stdout+diff.stderr)
check("Git diff whitespace check passes",diff.returncode==0)
files=[project_path,scheme_path,"NativeApp/TestHost/AnyNativeTestHostApp.swift","NativeApp/TestHost/NativeTestHost.entitlements"]
receipt={
 "schema":1,"completedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "result":"PASS_SOURCE_STRUCTURE_ONLY","checks":checks,"originalTestMethods":sorted(methods),
 "originalInputs":original,"files":[{"path":x,"sha256":sha(root/x),"bytes":(root/x).stat().st_size} for x in files],
 "existingHostedConvention":{"path":"Anytype.xcodeproj/project.pbxproj","sha256":sha(conventions),"lines":convention_lines},
 "primaryAppleSources":[
 {"url":"https://developer.apple.com/documentation/xcode/build-settings-reference.md","usedFor":["TEST_HOST","BUNDLE_LOADER","CODE_SIGN_ENTITLEMENTS","CODE_SIGN_INJECT_BASE_ENTITLEMENTS"]},
 {"url":"https://developer.apple.com/documentation/security/errsecmissingentitlement.md","usedFor":["Required entitlement missing","Keychain default access group","Signed entitlement inspection"]},
 {"url":"https://developer.apple.com/documentation/bundleresources/entitlements/keychain-access-groups.md","usedFor":["Keychain access-group entitlement"]}],
 "pending":["Xcode semantic build","Simulator ad-hoc signing and built entitlement inspection","Original five actual Keychain/runtime tests"],
 "notClaimed":["Apple execution","Keychain success","NativeLaunch pass","Device signing"],
 "preservedFailure":{"source":"d58b6a004c93320a4c57c8eba8e4518048d70fc1","executed":5,"failed":5,"cause":"Actual Keychain -34018 in standalone package test host"}}
(evidence/"result.json").write_bytes((json.dumps(receipt,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
print(json.dumps({"result":receipt["result"],"checks":len(checks),"originalTestMethods":methods,
 "receipt":str((evidence/"result.json").relative_to(root)).replace("\\","/"),"sha256":sha(evidence/"result.json"),"files":receipt["files"]},indent=2))

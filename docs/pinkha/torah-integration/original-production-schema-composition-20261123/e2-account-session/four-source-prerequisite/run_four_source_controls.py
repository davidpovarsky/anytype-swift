#!/usr/bin/env python3
"""Exact Foundation source controls. Not Combine/Lib/UIKit/account execution."""
import argparse, datetime, hashlib, json, os, pathlib, signal, subprocess
CASES=[
"fifo-empty-frontier","fifo-held-and-frozen-frontiers","fifo-canceled-waiter-retained",
"fifo-end-rejects-unresolved","fifo-terminated-yield-rejected","fifo-concurrent-enqueue",
"auth-frozen-parent-and-restriction","auth-retired-restriction-rejected",
"auth-permit-rechecks-restriction","auth-admitted-restriction-real-completion-drain"]
PATHS=[
"Anytype/Sources/ServiceLayer/Auth/AuthService.swift",
"Anytype/Sources/ServiceLayer/Account/AccountEventHandler.swift",
"Anytype/Sources/ServiceLayer/File/FileErrorEventHandler.swift",
"Modules/ProtobufMessages/Sources/ServiceMessageHandlerAdapter.swift"]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo",type=pathlib.Path,required=True);ap.add_argument("--output",type=pathlib.Path,required=True);a=ap.parse_args()
 repo=a.repo.resolve();out=a.output.resolve();out.mkdir(exist_ok=False);packet=pathlib.Path(__file__).resolve().parent
 result={"schema":1,"status":"NOT_COMPLETED","scope":"EXACT_FOUNDATION_FIFO_AND_AUTH_CAPTURE_CONTROLS_ONLY",
 "combine_executed":False,"registration_actors_executed":False,"apple_or_lib_or_native_execution":False,
 "historical_controls_reexecuted":False,"required_cases":CASES,"commands":[],"passed":[]}
 def save(): (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
 def read(path):
  p=repo/path
  return p.read_bytes() if p.is_file() else subprocess.check_output(["git","show","HEAD:"+path],cwd=repo,timeout=20)
 def run(label,argv,limit):
  started=datetime.datetime.now(datetime.timezone.utc).isoformat();timed=False
  stdout=out/(label+".stdout");stderr=out/(label+".stderr")
  with stdout.open("xb") as o,stderr.open("xb") as e:
   child=subprocess.Popen(argv,cwd=repo,stdout=o,stderr=e,start_new_session=True)
   try: code=child.wait(timeout=limit)
   except subprocess.TimeoutExpired:
    timed=True;os.killpg(child.pid,signal.SIGTERM)
    try:code=child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5)
  row={"label":label,"argv":argv,"started_at":started,"returncode":code,"timed_out":timed,
   "child_reaped":child.poll() is not None,"stdout_sha256":sha(stdout.read_bytes()),"stderr_sha256":sha(stderr.read_bytes())}
  result["commands"].append(row);save()
  if code or timed:raise RuntimeError(label+" failed")
  return stdout.read_text()
 try:
  corr=json.loads((packet/"SOURCE_CORRESPONDENCE.json").read_text())
  for row in corr["approved_paths"]:
   assert sha(read(row["path"]))==row["after_sha256"] and read(row["path"])==(packet/"after"/row["path"]).read_bytes()
  for path,expected in corr["seven_previously_accepted_afterimages_unchanged"].items():assert sha(read(path))==expected
  env=read("Modules/AnytypeCore/AnytypeCore/Utils/OriginalRuntimeEnvironment.swift").decode()
  assert "public static var deploymentMode: DeploymentMode" in env
  for path in PATHS[1:3]:
   text=read(path).decode();assert "OriginalRuntimeEnvironment.mode" not in text
   assert "OriginalRuntimeEnvironment.deploymentMode" in text and "await EventBunchSubscribtion.default.addHandlerAwaiting" in text
   assert "pendingEmbeddedRegistration?.id == id" in text and "embeddedInstallation === installation" in text
  file_text=read(PATHS[2]).decode();assert "func stopSubscription" not in file_text
  original_events=read("Anytype/Sources/Models/Documents/Events/Model/EventBunchSubscribtion.swift")
  exact_events=subprocess.check_output(["git","show","HEAD:Anytype/Sources/Models/Documents/Events/Model/EventBunchSubscribtion.swift"],cwd=repo)
  assert original_events==exact_events and b"handler = nil" in original_events
  adapter=read(PATHS[3]).decode();auth=read(PATHS[0]).decode()
  assert "try await listener.waitForPendingEventDelivery()\n        try Task.checkCancellation()" in adapter
  assert "defer { deliveryFence.didDeliverOne() }" in adapter and "await handler(event)" in adapter
  selected={}
  def segment(label,path,start,end=None):
   text=read(path).decode();begin=text.index(start);finish=text.index(end,begin) if end else len(text)
   exact=text[begin:finish];selected[label]={"path":path,"source_sha256":sha(read(path)),"bytes":len(exact.encode()),"sha256":sha(exact.encode())}
   (out/(label+".swift")).write_text(exact)
   return exact
  parts=[
   segment("ExactFIFO",PATHS[3],"private final class OriginalEventDeliveryFence:"),
   segment("ExactAuthAttempt",PATHS[0],"enum OriginalAuthRequestContext {","/// Constructed only here"),
   segment("ExactRejections","Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift","enum EditorDocumentWriteRejection:","/// Additional original document permissions."),
   segment("ExactCapture","Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift","struct EditorDocumentWriteCapture:","/// This task-local value"),
   segment("ExactLifetime","Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteLifetime.swift","import Foundation"),
   segment("ExactBinding","Modules/ProtobufMessages/Sources/InvocationDispatchBinding.swift","import Foundation")]
  harness=(packet/"FourSourceControls.swift").read_bytes();combined="import Foundation\nimport Dispatch\n\n"+"\n".join(parts)+"\n"+harness.decode()
  path=out/"ExactFoundationFourSourceControls.swift";path.write_text(combined)
  extraction={"status":"SOURCE_EXTRACTION_ONLY_BEFORE_EXECUTION","segments":selected,"source_text_replacements":[],
   "test_only_introspection":"Same-file private extensions read counters under original locks; no original source is rewritten.",
   "harness_sha256":sha(harness),"combined_sha256":sha(path.read_bytes()),
   "registration_scope":"Four unprojected syntax parses only; Combine/EventBunch actor integration is not executed.",
   "original_event_bunch_sha256":sha(original_events)}
  (out/"EXTRACTION.json").write_text(json.dumps(extraction,indent=2)+"\n")
  result["source_admission"]="PASS";result["extraction_sha256"]=sha((out/"EXTRACTION.json").read_bytes());save()
  run("swift-version",["swift","--version"],20)
  for i,p in enumerate(PATHS):run("unprojected-parse-"+str(i+1),["swiftc","-frontend","-parse",str(repo/p)],30)
  binary=out/"four-source-controls";run("portable-compile",["swiftc","-swift-version","6","-parse-as-library",str(path),"-o",str(binary)],90)
  result["binary_sha256"]=sha(binary.read_bytes())
  for i,name in enumerate(CASES):
   value=run("case-"+str(i+1),[str(binary),name],15).strip()
   assert value.startswith("PASS "+name+" assertions=")
   result["passed"].append({"name":name,"actual_output":value});save()
  result["status"]="PASS"
 except BaseException as e:
  result["status"]="FAIL";result["error_type"]=type(e).__name__;result["error"]=str(e);raise
 finally:
  result["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
  print(json.dumps({k:v for k,v in result.items() if k!="commands"},indent=2))
if __name__=="__main__":main()

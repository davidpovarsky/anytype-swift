"""Source-only App14 intake qualification using the original producer receipt."""
import ast,copy,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
COMMON="59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de"
RECEIPT="b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6"
SOURCE="76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
PRODUCER="b9e9d2f3cce9adfe6ffd45a6cce6c19f8bbce421"
def sha(b):return hashlib.sha256(b).hexdigest()
def definitions(s):return {x.name:ast.get_source_segment(s,x) for x in ast.parse(s).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
def main():
 own=Path(__file__).resolve().parent;repo=own.parents[3]
 before=(own.parent/"build13/combined_heart_semantics_current.py").read_text()
 current=(own/"combined_heart_semantics_current.py").read_text()
 assert sha(current.encode())==COMMON
 a,b=definitions(before),definitions(current)
 assert set(b)-set(a)=={"qualify_external_producer"} and set(a)-set(b)==set()
 unchanged=[name for name in a if a[name]==b[name]]
 assert set(a)-set(unchanged)=={"admit_and_clone_products"}
 observation_before=definitions((own.parent/"build13/combined_heart_observations_gateway.py").read_text())
 observation_after=definitions((own/"combined_heart_observations_gateway.py").read_text())
 assert observation_before==observation_after
 original_e=definitions((own.parent/"build13/combined_heart_semantics_replacement.py").read_text())
 actual_e=definitions((own/"combined_heart_semantics_replacement.py").read_text())
 assert set(original_e)==set(actual_e)
 assert {n for n in original_e if original_e[n]!=actual_e[n]}=={"admit_and_clone_products","main"}
 old_main=original_e["main"];new_main=actual_e["main"]
 old_cleanup='''            present = Commands.present(group)
            cleanup["groups"].append({"pgid": group, "present": present})
            if present:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"ownedGroupStillPresent": group})'''
 new_cleanup='''            try:
                present = Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append({"ownedGroupStillPresent": group})
            except BaseException as exc:
                # An unresolved kernel query is not absence and must not
                # prevent original receipts or account retention from surviving.
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"phase": "owned-group-observation", "pgid": group, **error(exc)})'''
 assert new_main.count(new_cleanup)==1 and new_main.replace(new_cleanup,old_cleanup)==old_main
 spec=importlib.util.spec_from_file_location("actual_shared_app14",own/"combined_heart_semantics_current.py")
 c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
 receipt_raw=sys.stdin.buffer.read();assert sha(receipt_raw)==RECEIPT
 receipt=c.decode(receipt_raw)
 def git(name):return subprocess.check_output(["git","-C",str(repo),"show",PRODUCER+":"+name],timeout=30)
 with tempfile.TemporaryDirectory(prefix="pinkha-app14-pure-") as directory:
  root=Path(directory);external={"commit":PRODUCER}
  for field,name in (("controller","Tools/PinkhaDualEngineRuntime/build_main_immutable.py"),("delta","docs/validation/20261126-native11619-apple-slices/app14-controller-delta.json")):
   data=git(name);target=root/Path(name).name;target.write_bytes(data)
   external[field]={"path":str(target),"bytes":len(data),"sha256":sha(data)}
  admission={"sourceCommit":SOURCE,"externalProducer":external}
  proof=c.qualify_external_producer(admission,repo,receipt)
  cases=[]
  def refused(name,ad,rc):
   try:c.qualify_external_producer(ad,repo,rc)
   except (ValueError,KeyError,AssertionError):cases.append(name)
   else:raise AssertionError("forged external authority accepted: "+name)
  ad=copy.deepcopy(admission);ad.pop("externalProducer");refused("missing producer",ad,receipt)
  ad=copy.deepcopy(admission);ad["externalProducer"]["unexpected"]=True;refused("open external contract",ad,receipt)
  ad=copy.deepcopy(admission);ad["externalProducer"]["commit"]="0"*40;refused("foreign producer Git commit",ad,receipt)
  ad=copy.deepcopy(admission);ad["sourceCommit"]="e540cd7e01b497f1b3173ae2e68b43ade0b00b6f";refused("foreign compiled source",ad,receipt)
  rc=copy.deepcopy(receipt);rc["controllerSHA256"]="0"*64;refused("foreign actual producer receipt",admission,rc)
  rc=copy.deepcopy(receipt);rc["assemblyReceiptSHA256"]="0"*64;refused("foreign assembly receipt",admission,rc)
  ad=copy.deepcopy(admission);ad["externalProducer"]["controller"]["bytes"]+=1;refused("changed controller size",ad,receipt)
  ad=copy.deepcopy(admission);ad["externalProducer"]["delta"]["sha256"]="0"*64;refused("changed inverse witness",ad,receipt)
  target=Path(external["controller"]["path"]);target.write_bytes(target.read_bytes()+b"\n")
  refused("actual producer bytes drift",admission,receipt)
  assert len(cases)==9
 result={"status":"PASS_SOURCE_INTAKE_CONTROLS_NOT_ACCEPTANCE","commonSHA256":COMMON,"actualProducerReceiptSHA256":RECEIPT,
  "externalOriginalInverse":proof,"unchangedCommonFunctions":unchanged,"unchangedObservationFunctions":sorted(observation_after),
  "originalESixStageBodyInverse":True,"newRefusalControls":cases,"testsExecuted":0,"appBuilds":0,"nativeCalls":0,"simulatorOperations":0}
 print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()

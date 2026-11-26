"""Reuse only the original source whose actual compile stopped at its disk floor."""
import hashlib,json
from pathlib import Path
PRIOR=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-core/attempt3")
RECEIPT_SHA="05ef0a2ede81003ee8e07097e181c3e23b6744066898692f124e3a1ff4f13535"
SOURCE_SHA="40dd49f7d75c1d11ba56e578bed1bd39946fa530d5a17c19647fd860b67dcb2f"
CANDIDATE_SHA="db2018871482d911b15fce3002d3e15d25fd17d50ca0ae7f64c72725de18bb58"
def digest(path):
 if path.resolve()!=path or path.is_symlink() or not path.is_file():raise ValueError("regular retained original required")
 return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
 if not value:raise ValueError(message)
def inventory(source):
 result={}
 for p in sorted(source.rglob("*")):
  require(p.resolve()==p and not p.is_symlink(),"retained original source alias")
  if p.is_file():result[str(p.relative_to(source))]={"bytes":p.stat().st_size,"sha256":digest(p)}
  else:require(p.is_dir(),"unexpected retained source kind")
 return result
def admit(directory):
 require(digest(PRIOR/"receipt.json")==RECEIPT_SHA,"exact original resource failure")
 prior=json.loads((PRIOR/"receipt.json").read_bytes())
 require(prior["status"]=="FAIL" and prior["sourceUnchanged"] is True
  and prior["sourceSHA256"]==SOURCE_SHA and prior["cleanupFailures"]==[],"original failure remains failed")
 require(len(prior["commands"])==4 and all(row["groupState"]=="ABSENT_ESRCH" for row in prior["commands"])
  and all(row["status"]=="PASS" and row["exitCode"]==0 for row in prior["commands"][:3]),"original owned commands ended")
 build=prior["commands"][-1]
 require(build["status"]=="FAIL" and build["resourceFloor"] is True and build["timedOut"] is False
  and build["exitCode"]==-15 and build["argv"][-1]=="./core" and "-c" in build["argv"],"actual resource-stopped compiler required")
 require(digest(PRIOR/"commands/build/result.json")=="bb1299af34cfff00095009ec26b9e340cb85e02aa2b3360b12cb053d5e57d59a"
  and json.loads((PRIOR/"commands/build/result.json").read_bytes())==build,"original build outcome differs")
 require(not (PRIOR/"cutover-real-core.test").exists() and not (PRIOR/"commands/actual-core").exists()
  and not list((PRIOR/"private").iterdir()),"original method/account was not invoked")
 require(digest(PRIOR/"source-before.json")==digest(PRIOR/"source-after.json")==SOURCE_SHA
  and digest(PRIOR/"candidate.json")==digest(directory/"native-core-registry-candidate.json")==CANDIDATE_SHA,"exact unchanged source/candidate")
 expected=json.loads((PRIOR/"source-before.json").read_bytes());source=PRIOR/"source"
 require(len(expected)==4879 and source.resolve()==source and inventory(source)==expected,"full retained source bytes differ")
 candidate=json.loads((PRIOR/"candidate.json").read_bytes())
 for name,row in candidate["sourceFiles"].items():
  require(expected["heart/"+name]==row and digest(directory/"overlay"/name)==row["sha256"],"core candidate delta differs")
 return source,expected,{"status":"PASS_RETAINED_SOURCE_FOR_NEW_ATTEMPT_NOT_NATIVE_ACCEPTANCE",
  "priorFailureReceiptSHA256":RECEIPT_SHA,"sourceInventorySHA256":SOURCE_SHA,"candidateSHA256":CANDIDATE_SHA,
  "sourceFiles":len(expected),"priorTestInvocations":0,"historicalGroupsProbed":0,"sourceCopied":False}

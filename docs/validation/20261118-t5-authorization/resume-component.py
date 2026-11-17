import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root=Path("C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118")
kit=Path("C:/Users/DAVID/Code/TorahInspectorKit-wave1-integration-20261115")
package=root/".build/portable-t5-authorization"
evidence=root/"docs/validation/20261118-t5-authorization"
first=evidence/"component.json"
previous=json.loads(first.read_text())
if previous["status"]!="RUNNING": raise RuntimeError("Original attempt already finalized")
previous.update(status="INCOMPLETE_TIMEOUT",external_job="job_be31ba8cfda3",external_timeout_seconds=60,
    finished_utc="2026-11-17T22:46:59.992836+00:00",tests_started=0)
first.write_text(json.dumps(previous,indent=2)+"\n",encoding="utf8")
def destination(source):
    if source.is_relative_to(kit/"Sources/TorahInspectorCore"):
        return package/"Sources/TorahInspectorCore"/source.relative_to(kit/"Sources/TorahInspectorCore")
    if source.is_relative_to(root/"Modules/PinkhaKit/Sources/PinkhaKit"):
        return package/"Sources/PinkhaKit"/source.relative_to(root/"Modules/PinkhaKit/Sources/PinkhaKit")
    return package/"Tests/PinkhaKitTests"/source.name
def unchanged():
    return all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha==hashlib.sha256(destination(Path(path)).read_bytes()).hexdigest()
        for path,sha in previous["source_sha256"].items())
if not unchanged(): raise RuntimeError("Source changed before component continuation")
receipt=dict(previous,status="RUNNING",started_utc=datetime.now(timezone.utc).isoformat(),continued_after="component.json")
for key in ["finished_utc","external_job","external_timeout_seconds","tests_started"]:
    receipt.pop(key,None)
receipt_path=evidence/"component-complete.json"
with receipt_path.open("x",encoding="utf8") as output: output.write(json.dumps(receipt,indent=2)+"\n")
try:
    with (evidence/"component-complete.log").open("x",encoding="utf8") as output:
        result=subprocess.run(previous["command"],cwd=root,stdout=output,stderr=subprocess.STDOUT,timeout=240)
    same=unchanged()
    receipt.update(status="PASS" if result.returncode==0 and same else "FAIL",returncode=result.returncode,source_unchanged=same)
except BaseException as error:
    receipt.update(status="FAIL",error_type=type(error).__name__,error=str(error))
receipt["finished_utc"]=datetime.now(timezone.utc).isoformat()
receipt_path.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
print(json.dumps({key:value for key,value in receipt.items() if key!="source_sha256"}))
print((evidence/"component-complete.log").read_text(encoding="utf8",errors="replace")[-14000:])
raise SystemExit(0 if receipt["status"]=="PASS" else 1)

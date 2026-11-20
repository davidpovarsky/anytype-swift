from pathlib import Path
import subprocess, hashlib, json, datetime, time
root=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
base=root/"build/any-engine-port/apple57-backup-toggle-fix-v1"
source=root/"NativeApp/UITests/NativeLaunchTests.swift"
swift=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
before=source.read_bytes()
assert hashlib.sha256(before).hexdigest()=="a6281a92153e6d93bc3e5a100b662571d9a19fffb722a0eb0d398180b640ee4f"
command=[str(swift),"-frontend","-parse","-target","arm64-apple-ios27.0-simulator",str(source)]
started=datetime.datetime.now(datetime.timezone.utc).isoformat(); begin=time.monotonic()
try:
 run=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,check=False)
 code=run.returncode;out=run.stdout;err=run.stderr;timedout=False
except subprocess.TimeoutExpired as exc:
 code=124;out=exc.stdout or b"";err=exc.stderr or b"";timedout=True
(base/"parse.stdout.log").write_bytes(out);(base/"parse.stderr.log").write_bytes(err)
stable=source.read_bytes()==before
receipt={"status":"PASS_SYNTAX_ONLY" if code==0 and stable else "FAIL","scope":"One source file Swift frontend parse; no UIKit semantic compilation or UI execution claimed.","startedAt":started,"durationSeconds":time.monotonic()-begin,"command":command,"compilerSHA256":hashlib.sha256(swift.read_bytes()).hexdigest(),"sourceSHA256":hashlib.sha256(before).hexdigest(),"sourceStable":stable,"exitCode":code,"timedOut":timedout,"stdoutBytes":len(out),"stderrBytes":len(err)}
(base/"parse-result.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt))
raise SystemExit(0 if receipt["status"]=="PASS_SYNTAX_ONLY" else 1)

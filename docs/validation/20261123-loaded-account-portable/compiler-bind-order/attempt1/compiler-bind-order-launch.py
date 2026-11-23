import pathlib,hashlib,json,os,sys,time,subprocess
ROOT=pathlib.Path("/run/anytapy-wave15-source-overlay-20261123/native")
WRAPPER=ROOT/"docs/validation/20261123-loaded-account-portable/compiler-bind-order/run-control.py"
MANIFEST=WRAPPER.parent/"control-inputs.json"
OUT=ROOT.parent/"compiler-bind-order-attempt1"
MARKER=ROOT.parent/"compiler-bind-order-launch-once.json"
assert os.getuid()==os.geteuid()==1001
assert not OUT.exists() and not MARKER.exists()
assert hashlib.sha256(WRAPPER.read_bytes()).hexdigest()=="6ba69e92b94fa90a22e0baf61397fc37e61c2f06d30b3eb46881ec333117f548"
assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest()=="4a65cb7ba65e2ff0ec57ebdc365a4c518e8f3577e468ed5cc0553da8ebe41595"
assert int(next(x.split()[1] for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))*1024>=2*1024**3
head="864dcd4051f5fd05446ca371929f14bbc8483a32"
argv=[sys.executable,"-B",str(WRAPPER),"--execute","--expected-head",head,"--expected-manifest","4a65cb7ba65e2ff0ec57ebdc365a4c518e8f3577e468ed5cc0553da8ebe41595"]
with MARKER.open("xb") as f:
 f.write((json.dumps({"schema":"compiler-bind-order-once-launch-v1","source":head,"argv":argv,"launcher_pid":os.getpid(),"time_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"one_new_control_only":True,"native_builds":0,"native_tests":0,"docker_actions":0},sort_keys=True)+"\n").encode());f.flush();os.fsync(f.fileno())
os.execv(sys.executable,argv)

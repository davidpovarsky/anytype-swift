import pathlib,json,subprocess,sys,os,time,hashlib
root=pathlib.Path(__file__).parent
spec=json.loads((root/"dispatch.json").read_text())
def write(name,value):
 p=root/name
 b=(json.dumps(value,indent=2,sort_keys=True)+"\n").encode()
 with p.with_suffix(".new").open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.with_suffix(".new").replace(p)
start=time.time()
running={"schema":"pinkha-root-supervised-dispatch-v1","status":"RUNNING","started":start,"supervisorPID":os.getpid(),"supervisorPGID":os.getpgrp(),"argv":spec["argv"],"sourceCommit":spec["sourceCommit"],"originalPhaseTimeoutSeconds":7200,"transportDetached":True,"supervisorSHA256":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
write("running.json",running)
try:
 with (root/"adapter-original.log").open("xb") as log:
  p=subprocess.Popen(spec["argv"],cwd=spec["controlDirectory"],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,close_fds=True)
  running["adapterPID"]=p.pid
  write("running.json",running)
  code=p.wait()
 result=dict(running,status="ADAPTER_EXIT_0" if code==0 else "ADAPTER_FAILED",finished=time.time(),exitCode=code)
except BaseException as exc:
 result=dict(running,status="SUPERVISOR_ERROR",finished=time.time(),errorType=type(exc).__name__,reason=str(exc))
 code=1
for key,path in [("producerReceipt",spec["producerReceipt"]),("actualProducer",spec["actualProducer"])]:
 p=pathlib.Path(path)
 if p.is_file():
  result[key]={"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
if "actualProducer" in result:
 result["executedProducerMatchesReviewedPreview"]=result["actualProducer"]["sha256"]==spec["expectedProducerSHA256"]
write("exit.json",result)
sys.exit(code)

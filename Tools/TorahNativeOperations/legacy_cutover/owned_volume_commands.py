"""Bounded commands with independent floors on both local core volumes.
Original child exit/log are persisted even if the post-exit group observation
is denied. Positive absence is permanent; historical IDs are never signalled.
"""
import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path

def digest(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError("regular exact file required: "+str(path))
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    with temporary.open("x") as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write("\n");stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)
class Commands:
    def __init__(self,root,floor,volumes):
        self.root=Path(root);self.floor=floor;self.rows=[];self.absent=set()
        self.volumes=tuple(Path(value) for value in volumes)
        if len(self.volumes)!=2 or any(value.resolve()!=value or not value.is_dir() for value in self.volumes):
            raise ValueError("two exact existing owned capacity roots required")
        if self.root not in self.volumes or len({value.stat().st_dev for value in self.volumes})!=2:
            raise ValueError("both distinct local execution/cache filesystems required")
    def capacity(self):
        import shutil
        return [{"path":str(value),"device":value.stat().st_dev,"freeBytes":shutil.disk_usage(value).free}
                for value in self.volumes]
    def observe(self,pgid):
        if pgid in self.absent:return "ABSENT_PREVIOUSLY_PROVED"
        try:os.killpg(pgid,0)
        except ProcessLookupError:
            self.absent.add(pgid);return "ABSENT_ESRCH"
        except PermissionError:return "UNRESOLVED_EPERM"
        return "PRESENT_OR_REUSED_UNRESOLVED"
    def run(self,name,argv,cwd,env,timeout):
        import shutil
        folder=self.root/"commands"/name;folder.mkdir(parents=True,exist_ok=False)
        started=time.monotonic()
        row={"argv":argv,"cwd":str(cwd),"startedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"FAIL"}
        process=None;pending=None
        try:
            samples=self.capacity();row["volumesBefore"]=samples
            row["minimumFreeBytes"]={str(value["device"]):value["freeBytes"] for value in samples}
            if any(value["freeBytes"]<self.floor for value in samples):raise RuntimeError("pre-command emergency capacity floor")
            with (folder/"original.log").open("xb") as log:
                process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                row.update(pid=process.pid,pgid=process.pid);self.rows.append(row);save(folder/"started.json",row)
                while True:
                    try:row["exitCode"]=process.wait(timeout=2);break
                    except subprocess.TimeoutExpired:
                        try:
                            samples=self.capacity()
                            for value in samples:
                                key=str(value["device"])
                                row["minimumFreeBytes"][key]=min(row["minimumFreeBytes"][key],value["freeBytes"])
                            resource=any(value["freeBytes"]<self.floor for value in samples)
                            if resource:row["volumesAtStop"]=samples
                        except Exception as error:
                            # A failed second-volume observation cannot leave
                            # the current owned child running without its floor.
                            resource=True
                            row["capacityObservationError"]=type(error).__name__+": "+str(error)
                        timed_out=time.monotonic()-started>timeout
                        if not resource and not timed_out:continue
                        row.update(resourceFloor=resource,timedOut=timed_out)
                        # Only this still-live, unreaped Popen child owns a
                        # signalling opportunity. Never signal after wait.
                        for sig in (signal.SIGTERM,signal.SIGKILL):
                            if process.poll() is not None:
                                row["exitCode"]=process.returncode;break
                            if os.getpgid(process.pid)!=process.pid:raise RuntimeError("owned child group changed")
                            try:os.killpg(process.pid,sig)
                            except ProcessLookupError:self.absent.add(process.pid)
                            try:row["exitCode"]=process.wait(timeout=5);break
                            except subprocess.TimeoutExpired:continue
                        break
                # Persist original exit before any fallible post-exit observer.
                save(folder/"original-exit.json",{"exitCode":row.get("exitCode"),"pid":process.pid,
                    "timedOut":row.get("timedOut",False),"resourceFloor":row.get("resourceFloor",False)})
                row["groupState"]=self.observe(process.pid)
                if row.get("exitCode")==0 and row["groupState"].startswith("ABSENT_") and not row.get("timedOut") and not row.get("resourceFloor"):
                    row["status"]="PASS"
        except Exception as error:
            pending=error;row["error"]=type(error).__name__+": "+str(error)
        finally:
            row["seconds"]=time.monotonic()-started
            try:
                if (folder/"original.log").exists():row["logSHA256"]=digest(folder/"original.log")
            except Exception as error:
                row.update(status="FAIL",logRetentionError=type(error).__name__+": "+str(error))
                if pending is None:pending=error
            try:
                save(folder/"result.json",row)
            except Exception as error:
                # Keep this failure in the parent receipt even if the command
                # directory itself cannot retain a terminal result.
                row.update(status="FAIL",resultRetentionError=type(error).__name__+": "+str(error))
                if pending is None:pending=error
        if pending is not None:raise pending
        if row["status"]!="PASS":raise RuntimeError("owned command failed: "+name)
        return folder/"original.log"
    def cleanup(self):
        failures=[]
        for row in self.rows:
            pgid=row["pgid"]
            if pgid in self.absent:continue
            try:
                state=self.observe(pgid)
                if not state.startswith("ABSENT_"):failures.append({"pgid":pgid,"state":state,"signals":0})
            except Exception as error:failures.append({"pgid":pgid,"error":type(error).__name__+": "+str(error),"signals":0})
        return failures

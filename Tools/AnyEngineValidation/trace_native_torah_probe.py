#!/usr/bin/env python3
"""Ephemeral loopback HTTP route/timing diagnostic. Never logs headers or bodies."""
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import argparse, hashlib, http.client, importlib.util, json, os, socket, threading, time, urllib.request

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("baseline","fixture","probe","native-binary","native-manifest"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--allow-disposable-writes",action="store_true")
    args=parser.parse_args()
    if not args.allow_disposable_writes:parser.error("Explicit disposable fixture authorization required")
    spec=importlib.util.spec_from_file_location("native_torah_original_runner",ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py")
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    baseline=json.loads(args.baseline.read_text());fixture=json.loads(args.fixture.read_text())
    if (baseline.get("sourceStable") is not True or baseline.get("buildExitCode")!=0 or
        sha(args.probe)!=baseline["probeSHA256"] or original.manifest()!=baseline["sourceManifest"]):
        parser.error("Existing probe no longer matches its successful source-bound build")
    if sha(args.native_binary)!=original.NATIVE_SHA or sha(args.native_manifest)!=original.MANIFEST_SHA:
        parser.error("Native binary/source manifest mismatch")
    if fixture.get("endpoint")!="http://127.0.0.1:60663":parser.error("Only the assigned60663 fixture may be traced")
    with urllib.request.urlopen(fixture["endpoint"]+"/v1/health",timeout=10) as response:health=json.load(response)
    if health.get("status")!="ok" or health.get("account")!=fixture["accountId"]:parser.error("Assigned fixture account mismatch")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    prefix=ROOT/"docs/any-engine-port/evidence/20261119"/("native-torah-http-trace-"+stamp)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    trace_path=prefix.with_suffix(".requests.jsonl")
    trace=trace_path.open("w",encoding="utf-8")
    trace_lock=threading.Lock();connection_lock=threading.Lock()
    connections=set();handler_threads=set();events=[];next_id=0
    def log(event):
        with trace_lock:
            events.append(event);trace.write(json.dumps(event,separators=(",",":"))+"\n");trace.flush()
    hop={"connection","proxy-connection","keep-alive","transfer-encoding","te","trailer","upgrade"}
    class Handler(BaseHTTPRequestHandler):
        protocol_version="HTTP/1.0"
        def log_message(self,*args):pass
        def setup(self):
            super().setup();self.connection.settimeout(45)
            self.upstream=http.client.HTTPConnection("127.0.0.1",60663,timeout=75)
            with connection_lock:
                connections.add(self.upstream);handler_threads.add(threading.current_thread())
        def finish(self):
            try:self.upstream.close()
            finally:
                with connection_lock:
                    connections.discard(self.upstream);handler_threads.discard(threading.current_thread())
                try:super().finish()
                except (OSError,ValueError):pass
        def route(self):
            nonlocal next_id
            started=time.monotonic()
            with trace_lock:
                next_id+=1;identifier=next_id
            path=urlsplit(self.path).path
            base={"id":identifier,"method":self.command,"path":path}
            def event(phase,status=None,error=None):
                row=dict(base,phase=phase,status=status,elapsedMs=round((time.monotonic()-started)*1000,3),utc=now())
                if error:row["errorType"]=error
                log(row)
            event("received")
            try:
                if not path.startswith("/v1/") or self.headers.get("Transfer-Encoding"):
                    raise ValueError("unsupported diagnostic request")
                length=int(self.headers.get("Content-Length","0"))
                if length<0 or length>16*1024*1024:raise ValueError("diagnostic request bound")
                body=self.rfile.read(length) if length else None
                if body is not None and len(body)!=length:raise ValueError("incomplete diagnostic request")
                headers={key:value for key,value in self.headers.items() if key.lower() not in hop|{"host","content-length"}}
                headers["Host"]="127.0.0.1:60663"
                if length:headers["Content-Length"]=str(length)
                self.upstream.request(self.command,self.path,body=body,headers=headers)
                event("forwarded")
                response=self.upstream.getresponse()
                event("response_headers",response.status)
                data=response.read(16*1024*1024+1)
                if len(data)>16*1024*1024:raise ValueError("diagnostic response bound")
                event("response_complete",response.status)
                self.send_response_only(response.status,response.reason)
                for key,value in response.getheaders():
                    if key.lower() not in hop|{"content-length"}:self.send_header(key,value)
                self.send_header("Content-Length",str(len(data)))
                self.send_header("Connection","close")
                self.close_connection=True
                self.end_headers()
                if data:self.wfile.write(data)
                self.wfile.flush()
                event("delivered",response.status)
            except Exception as error:
                event("error",error=type(error).__name__)
                self.close_connection=True
                try:
                    self.send_response_only(502)
                    self.send_header("Content-Length","0")
                    self.end_headers()
                except (OSError,ValueError):pass
        do_GET=route;do_POST=route;do_PATCH=route;do_DELETE=route;do_PUT=route
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    server.daemon_threads=True;server.block_on_close=False
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    proxy_endpoint="http://127.0.0.1:"+str(server.server_port)
    record={"schemaVersion":1,"status":"RUNNING","startedAt":now(),
            "scope":"native_t5_http_route_diagnostic","businessScope":original.SCOPE,
            "sourceManifest":baseline["sourceManifest"],"baselineBuildReceiptSHA256":sha(args.baseline),
            "probeSHA256":sha(args.probe),"nativeBinarySHA256":original.NATIVE_SHA,
            "nativeSourceManifestSHA256":original.MANIFEST_SHA,"runnerSHA256":sha(Path(__file__)),
            "transportTopologyChangedForDiagnostics":True,"proxyBindsLiteralLoopbackOnly":True,"proxyConnectionMode":"explicit_close_diagnostic",
            "recordedFields":["id","method","path_without_query","phase","status","elapsedMs","utc","errorType"],
            "headersRecorded":False,"bodiesRecorded":False,"productionTimeoutsChanged":False,
            "engineStartedAt":health.get("startedAt"),"expectedBusinessChecks":19}
    output=prefix.with_suffix(".json");output.write_text(json.dumps(record,indent=2)+"\n")
    stdout_path=prefix.with_suffix(".stdout.log");stderr_path=prefix.with_suffix(".stderr.log")
    env=dict(os.environ)
    env["PATH"]=r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin"+os.pathsep+env.get("PATH","")
    try:
        command=[str(args.probe),proxy_endpoint,fixture["spaceId"],fixture["accountId"],"--torah-workflow","--allow-disposable-writes"]
        with stdout_path.open("wb") as stdout,stderr_path.open("wb") as stderr:
            code=original.bounded(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,seconds=300)
        record["probeExitCode"]=code
        lines=stdout_path.read_text(encoding="utf-8").strip().splitlines()
        record["result"]=json.loads(lines[-1]) if lines else {}
    except Exception as error:
        record["failure"]={"kind":type(error).__name__}
    finally:
        server.shutdown();server.server_close()
        with connection_lock:pending=list(connections)
        for connection in pending:
            try:
                if connection.sock:connection.sock.shutdown(socket.SHUT_RDWR)
                connection.close()
            except OSError:pass
        thread.join(timeout=5)
        with connection_lock:pending_threads=list(handler_threads)
        deadline=time.monotonic()+5
        for handler_thread in pending_threads:
            handler_thread.join(timeout=max(0,deadline-time.monotonic()))
        with connection_lock:record["traceComplete"]=not any(t.is_alive() for t in handler_threads)
        with trace_lock:
            trace.flush()
    # Request threads are daemon threads and all their sockets were closed.
    record.update(finishedAt=now(),sourceStable=original.manifest()==baseline["sourceManifest"],
                  probeUnchanged=sha(args.probe)==record["probeSHA256"],
                  nativeBinaryUnchanged=sha(args.native_binary)==original.NATIVE_SHA,
                  nativeManifestUnchanged=sha(args.native_manifest)==original.MANIFEST_SHA)
    result=record.get("result",{})
    success=(record.get("probeExitCode")==0 and result.get("status")=="PASS" and result.get("scope")==original.SCOPE
             and result.get("count")==19 and len(set(result.get("checks",[])))==19)
    stable=record.get("traceComplete",False) and all(record[k] for k in ("sourceStable","probeUnchanged","nativeBinaryUnchanged","nativeManifestUnchanged"))
    record["status"]="PASS_DIAGNOSTIC_PROXY" if success and stable else "FAIL_DIAGNOSTIC_PROXY"
    for name,path in (("trace",trace_path),("stdout",stdout_path),("stderr",stderr_path)):
        if path.is_file():record[name]=path.relative_to(ROOT).as_posix();record[name+"SHA256"]=sha(path)
    with trace_lock:record["lastEvents"]=events[-16:];record["requestCount"]=next_id
    output.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k!="sourceManifest"},indent=2))
    print(json.dumps({"receipt":output.relative_to(ROOT).as_posix()}))
    return 0 if success and stable else 1

if __name__=="__main__":raise SystemExit(main())

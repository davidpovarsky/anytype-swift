#!/usr/bin/env python3
"""Finite loopback HTTP fixture for the engine Markdown receipt boundary."""
import http.server,json,pathlib,signal,sys,time
root=pathlib.Path(sys.argv[1]); config=json.loads((root/"config.json").read_text())
events=[]; body=config.get("body",""); version="v1"; wrote=False
running=True
def stop(*_):
    global running
    running=False
signal.signal(signal.SIGTERM,stop)
if hasattr(signal,"pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM})
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send(self,status,value,raw=None):
        data=json.dumps(value,ensure_ascii=False).encode() if raw is None else raw
        self.send_response(status);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
    def record(self,method,payload=None):
        events.append({"method":method,"path":self.path,"body":payload})
        (root/"events.json").write_text(json.dumps(events))
    def do_GET(self):
        if self.path=="/v1/auth":
            account="other" if wrote and config.get("mode")=="account-switch" else config.get("account","account")
            self.send(200,{"authorized":True,"accountId":account});return
        assert self.path=="/v1/spaces/space/objects/object/editor/editor_blocks/markdown"
        self.record("GET")
        (root/("readback-responded" if wrote else "read-responded")).touch()
        if wrote and config.get("mode")=="readback-forbidden":
            self.send(403,{"error":{"code":"acl.forbidden"}});return
        value={"content":body,"version":"v3" if wrote and config.get("mode")=="readback-changed" else version}
        if config.get("mode")=="missing-read-version":value.pop("version")
        self.send(200,value)
    def do_PUT(self):
        global body,version,wrote
        assert self.path=="/v1/spaces/space/objects/object/editor/editor_blocks/markdown"
        data=self.rfile.read(int(self.headers["Content-Length"]));request=json.loads(data)
        self.record("PUT",request);(root/"write-responded").touch()
        assert request["ifVersion"]=="v1"
        mode=config.get("mode","")
        if mode=="conflict":
            self.send(409,{"error":{"code":"markdown.conflict"}});return
        if mode=="block-too-large":
            self.send(400,{"error":{"code":"markdown.block_too_large"}});return
        wrote=True;body=config.get("normalized",request["content"]);version="v2"
        if mode=="partial-rejection":
            self.send(200,{"rejections":[{"code":"acl.forbidden"}]});return
        if mode in ("server-error","unknown-error"):
            self.send(500 if mode=="server-error" else 418,{"error":{"code":"undocumented.native.failure"}});return
        ack={"inserted":["block-1"],"updated":[],"deleted":[],"unchanged":0,"version":version}
        if mode=="missing-ack-version":ack.pop("version")
        if mode=="malformed-json":self.send(200,None,b"{");return
        self.send(200,ack)
server=http.server.HTTPServer(("127.0.0.1",0),Handler)
server.timeout=.2
print(server.server_port,flush=True)
deadline=time.monotonic()+45
while running and time.monotonic()<deadline:server.handle_request()
server.server_close()

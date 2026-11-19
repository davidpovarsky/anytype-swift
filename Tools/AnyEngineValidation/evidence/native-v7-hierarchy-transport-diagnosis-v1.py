import hashlib,http.client,json,time
from pathlib import Path
root=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
out=root/"Tools/AnyEngineValidation/evidence/native-v7-hierarchy-transport-diagnosis-v1.json"
space="bafyreihw4veejecpzom3fqvlpzz7ppwvoj7tbag26jobbwbl2vraxs2klm.2nf3py0wn7qmz"
result={"scope":"Read-only diagnosis on the hierarchy-owned disposable v7 fixture; no production transport changes.","endpoint":"http://127.0.0.1:56668","spaceId":space,"requests":[]}
def save(): out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
conn=http.client.HTTPConnection("127.0.0.1",56668,timeout=8)
try:
 for method,path,body in [("GET","/v1/health",None),("GET","/v1/auth",None),("GET","/v1/health",None),("POST","/v1/spaces/"+space+"/query",{"dataset":"objects","limit":100})]:
  row={"method":method,"path":path,"phase":"before_send"};result["requests"].append(row);save();start=time.monotonic()
  raw=None if body is None else json.dumps(body).encode()
  conn.request(method,path,body=raw,headers={} if raw is None else {"Content-Type":"application/json"})
  row["phase"]="awaiting_headers";save()
  response=conn.getresponse()
  row.update(status=response.status,version=response.version,contentLength=response.getheader("Content-Length"),transferEncoding=response.getheader("Transfer-Encoding"),connection=response.getheader("Connection"),chunked=response.chunked,willClose=response.will_close,phase="awaiting_body",localPort=conn.sock.getsockname()[1] if conn.sock else None);save()
  data=response.read(1048577)
  if len(data)>1048576: raise RuntimeError("bounded_response_overflow")
  row.update(phase="complete",elapsedSeconds=round(time.monotonic()-start,3),bodyBytes=len(data),bodySHA256=hashlib.sha256(data).hexdigest())
  if body is not None:
   value=json.loads(data);records=value.get("records",[])
   row["records"]=[{"id":record.get("id"),"type":record.get("any",{}).get("type"),"isFolder":str(record.get("any",{}).get("name","")).startswith("Guarded folder "),"isCustomChild":str(record.get("any",{}).get("name","")).startswith("Custom child "),"isPageChild":str(record.get("any",{}).get("name","")).startswith("Page child ")} for record in records]
   row["recordCount"]=len(records);row["responseErrorPresent"]=bool(value.get("error"))
  save()
 result["status"]="PASS_READONLY_DIAGNOSIS"
except Exception as error:
 result.update(status="FAIL_READONLY_DIAGNOSIS",errorType=type(error).__name__)
 if result["requests"]: result["requests"][-1]["errorType"]=type(error).__name__
finally: conn.close();save()
print(json.dumps({"status":result["status"],"requests":result["requests"],"errorType":result.get("errorType")}))

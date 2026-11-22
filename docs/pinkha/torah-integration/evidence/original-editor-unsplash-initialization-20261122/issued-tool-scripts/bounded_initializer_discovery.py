import pathlib,subprocess,json,re,hashlib
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
head="568d69f55a4b1b1bc318b8ee20144c720c8c16a5"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-unsplash-init-20261122")
def git(*a,input=None):
 r=subprocess.run(["git",*a],cwd=w,input=input,capture_output=True,timeout=60);r.check_returncode();return r.stdout
names=git("grep","-l","-F","documentWriteOwner",head,"--","Anytype/Sources").decode().splitlines()
paths=[n.removeprefix(head+":") for n in names if n.endswith(".swift")]
request="".join(head+":"+p+"\n" for p in paths).encode()
data=git("cat-file","--batch",input=request);cursor=0;reviewed=[];candidates=[]
for p in paths:
 end=data.index(b"\n",cursor);header=data[cursor:end].decode().split();assert header[1]=="blob"
 length=int(header[2]);raw=data[end+1:end+1+length];cursor=end+length+2
 text=raw.decode()
 if "@Injected(" not in text and "@LazyInjected(" not in text:continue
 injected=re.findall(r"@(?:Lazy)?Injected\([^\n]+\)\s*(?:private\s+|public\s+|internal\s+|fileprivate\s+)?var\s+([A-Za-z_]\w*)",text)
 reviewed.append({"path":p,"blob":header[0],"sha256":hashlib.sha256(raw).hexdigest(),"injected_properties":injected})
 lines=text.splitlines()
 for i,line in enumerate(lines):
  m=re.search(r"self\.(\w+)\s*=\s*(\w+)\s*$",line)
  if m and m[1]==m[2] and m[1] in injected:
   candidates.append({"path":p,"line":i+1,"injected_property":m[1],"context":lines[max(0,i-14):i+13],"source_sha256":hashlib.sha256(raw).hexdigest()})
   destination=out/("INITIALIZER_DISCOVERY_"+str(len(candidates)-1)+".swift");destination.write_bytes(raw)
assert cursor==len(data)
record={"schema":1,"head":head,"owner_mention_files":len(paths),"owner_and_injected_files":len(reviewed),"reviewed_files":reviewed,"property_self_assignments":candidates,"limits":"Bounded static candidate discovery for this newly observed definite-initialization pattern only. No old weak-self/actor/preparation audit replay, no parsing/testing, no source edits, no exhaustive compiler certification."}
(out/"INITIALIZER_DISCOVERY.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
(out/"discover_initialization_pattern.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({"owner_mention_files":len(paths),"owner_and_injected_files":len(reviewed),"candidates":candidates,"record_sha256":hashlib.sha256((out/"INITIALIZER_DISCOVERY.json").read_bytes()).hexdigest()}))

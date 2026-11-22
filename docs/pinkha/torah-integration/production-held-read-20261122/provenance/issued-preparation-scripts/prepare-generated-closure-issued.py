from pathlib import Path
import subprocess,json,re,hashlib
repo=Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
root=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-held-read-implementation-20261122")
base="18ac6d39dfe76b12e5dead9627c831c6a88d073c"
assert root.is_dir()
dest=root/"generated-closure"
assert not dest.exists();dest.mkdir()
listing=subprocess.check_output(["git","ls-tree","-r","--name-only",base,"--","Modules/ProtobufMessages/Sources/Protocol"],cwd=repo,text=True).splitlines()
mapping={}
for path in listing:
    if path.endswith(".swift"):
        key=Path(path).stem
        assert key not in mapping,key
        mapping[key]=path
roots=["Anytype_Rpc","Anytype_Rpc.Object","Anytype_Rpc.Object.Show","Anytype_Model_ObjectView"]
pending={mapping[k] for k in roots};sources={};unresolved=set();edges={}
def resolve(token):
    t=token
    while t:
        if t in mapping:return mapping[t]
        if "." not in t:break
        t=t.rsplit(".",1)[0]
    return None
while pending:
    batchpaths=sorted(pending);pending=set()
    request=b"".join((base+":"+p+"\n").encode() for p in batchpaths)
    run=subprocess.run(["git","cat-file","--batch"],cwd=repo,input=request,capture_output=True,check=True)
    offset=0
    for path in batchpaths:
        end=run.stdout.index(b"\n",offset);header=run.stdout[offset:end].decode().split();offset=end+1
        assert len(header)==3 and header[1]=="blob";size=int(header[2])
        raw=run.stdout[offset:offset+size];offset+=size+1
        sources[path]={"raw":raw,"blob":header[0]}
        tokens=set(re.findall(r"\bAnytype_(?:Model|Rpc)(?:_[A-Za-z0-9_]+)?(?:\.[A-Z][A-Za-z0-9_]*)*",raw.decode()))
        deps=set()
        for token in tokens:
            target=resolve(token)
            if target is None:unresolved.add(token)
            else:
                deps.add(target)
                if target not in sources and target not in batchpaths:pending.add(target)
        edges[path]=sorted(deps)
    assert offset==len(run.stdout)
assert not unresolved,sorted(unresolved)
rows=[]
imports=set()
for path,item in sorted(sources.items()):
    raw=item["raw"];target=dest/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    imports.update(re.findall(r"^import (\w+)",raw.decode(),re.M))
    rows.append({"path":path,"gitBlob":item["blob"],"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"dependencies":edges[path]})
assert imports=={"Foundation","SwiftProtobuf"},imports
manifest={"schemaVersion":1,"base":base,"roots":roots,"files":rows,"filesCount":len(rows),"totalBytes":sum(x["bytes"] for x in rows),"imports":sorted(imports),"unresolvedReferences":[],"status":"SOURCE_CLOSURE_PREPARED_NOT_COMPILED","scope":"Complete immutable original generated files with all original conformances. No generated source change or regeneration."}
(root/"GENERATED_CLOSURE.json").write_bytes((json.dumps(manifest,indent=2)+"\n").encode())
probe_paths=["Anytype/Sources/ServiceLayer/Account/AccountManager.swift","Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/PreparedEditorPageSession.swift","Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/PreparedEditorPageDocument.swift","Modules/Services/Sources/Models/Details/ObjectDetails.swift","Modules/Services/Sources/Models/Extensions/ObjectDetails+Parsing.swift","Modules/Services/Sources/Generated/BundledPropertyKey.swift"]
files=[]
for path in probe_paths:
    raw=subprocess.check_output(["git","show",base+":"+path],cwd=repo)
    files.append({"path":path,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"source":raw.decode()})
provenance=[]
for args in [["rg","-n","ObjectShow","Modules/ProtobufMessages/Sources","--glob","*.swift"],["rg","-n","Anytype_Rpc\\.ObjectShow|typealias[[:space:]]+ObjectShow|struct[[:space:]]+ObjectShow","Anytype","Modules","OriginalEditorFramework","--glob","*.swift"]]:
    p=subprocess.run(args,cwd=repo,capture_output=True,check=True)
    provenance.append({"args":args,"stdout":p.stdout.decode(),"exitCode":p.returncode,"stdoutSHA256":hashlib.sha256(p.stdout).hexdigest()})
service="Modules/ProtobufMessages/Sources/Generated/service+invocation.swift"
raw=subprocess.check_output(["git","show",base+":"+service],cwd=repo)
lines=raw.decode().splitlines(True)
hits=[i for i,line in enumerate(lines) if "func objectShow(" in line]
assert len(hits)==1
start=hits[0];excerpt="".join(lines[start:start+10])
provenance.append({"path":service,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"startLine":start+1,"excerpt":excerpt})
(root/"ACTUAL_OBJECTSHOW_TYPE_PROVENANCE.json").write_bytes((json.dumps(provenance,indent=2)+"\n").encode())
print(json.dumps({"closure":{"files":len(rows),"bytes":sum(x["bytes"] for x in rows),"manifestSHA256":hashlib.sha256((root/"GENERATED_CLOSURE.json").read_bytes()).hexdigest(),"imports":sorted(imports)},"sources":files,"serviceExcerpt":excerpt}))

import pathlib,json,hashlib,difflib,subprocess
d=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-textblock-existential-20261122")
r=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121");h="d8416b161ba7af42e8459d612a94f7591470513e"
p="Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/SimpleTable/Block/TextBlock/SimpleTablesTextBlockActionHandler.swift"
b=(d/"SimpleTablesTextBlockActionHandler.swift").read_bytes()
assert hashlib.sha256(b).hexdigest()=="e56b728efa118250ba7dc8f6eed68d48a9945db696c55ed4593b4848e2094f47"
start=b.index(b"    private func cut(range: NSRange) {");end=b.index(b"    private func createEmptyBlock()",start)
old=b[start:end];assert old.count(b"actionHandler.scheduleMutationTask { [self] in")==1
new=old.replace(b"actionHandler.scheduleMutationTask { [self] in",b"actionHandler.scheduleMutationTask { [self] () -> Void in")
c=b.replace(old,new)
(d/"SimpleTablesTextBlockActionHandler.CANDIDATE.swift").write_bytes(c)
patch="".join(difflib.unified_diff(b.decode().splitlines(keepends=True),c.decode().splitlines(keepends=True),fromfile="a/"+p,tofile="b/"+p)).encode()
(d/"SIMPLE_TABLE_CUT_VOID.patch").write_bytes(patch)
proto="Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandlerProtocol.swift"
x=subprocess.run(["git","show",h+":"+proto],cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30).stdout
(d/"TextBlockActionHandlerProtocol.swift").write_bytes(x)
out={"path":p,"base_sha256":hashlib.sha256(b).hexdigest(),"candidate_sha256":hashlib.sha256(c).hexdigest(),"patch_sha256":hashlib.sha256(patch).hexdigest(),"patch":patch.decode(),"actual_diagnostic":False,"rationale":"Identical generic scheduler + single-expression weak-service optional cut on existential document; preventative source-compatibility candidate only","protocol_path":proto,"protocol_sha256":hashlib.sha256(x).hexdigest(),"protocol":x.decode()}
(d/"SIMPLE_TABLE_CANDIDATE_PROVENANCE.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))

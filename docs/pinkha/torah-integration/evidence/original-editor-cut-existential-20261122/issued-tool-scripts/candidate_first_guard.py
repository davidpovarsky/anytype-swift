import pathlib,hashlib,json,subprocess,difflib,datetime
r=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
d=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-textblock-existential-20261122")
h="d8416b161ba7af42e8459d612a94f7591470513e";path="Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift"
b=(d/"TextBlockActionHandler.BASE.swift").read_bytes()
assert hashlib.sha256(b).hexdigest()=="41ef1dc75c22d6617b629c31b3cd60b002ffacdb87b01373fa98bc3d37c10203"
old=b"    private func cut(range: NSRange) {\r\n        guard !isVirtualUnmaterialized else { return }\r\n        actionHandler.scheduleMutationTask { [self] in\r\n"
new=old.replace(b"{ [self] in",b"{ [self] () -> Void in")
assert b.count(old)==1
candidate=b.replace(old,new)
(d/"TextBlockActionHandler.CANDIDATE.swift").write_bytes(candidate)
patch="".join(difflib.unified_diff(b.decode().splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile="a/"+path,tofile="b/"+path)).encode()
(d/"CUT_VOID.patch").write_bytes(patch)
protocol_path="Anytype/Sources/ServiceLayer/Block/Pastboard/DocumentService/PasteboardBlockDocumentServiceProtocol.swift"
p=subprocess.run(["git","show",h+":"+protocol_path],cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30)
(d/"PasteboardBlockDocumentServiceProtocol.swift").write_bytes(p.stdout)
q=subprocess.run(["git","grep","-n","-E",r"\.(cut|copy)\(document:",h,"--","Anytype/Sources"],cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
discovery={"ref":h,"pattern":r"\.(cut|copy)\(document:","returncode":q.returncode,"hits":q.stdout.decode(),"scope":"Only original generic document pasteboard calls, static discovery; not compiler certification"}
(d/"PASTEBOARD_CALL_DISCOVERY.json").write_text(json.dumps(discovery,indent=2),encoding="utf-8")
info={"source_ref":h,"source_path":path,"preimage_sha256":hashlib.sha256(b).hexdigest(),"candidate_sha256":hashlib.sha256(candidate).hexdigest(),"patch_sha256":hashlib.sha256(patch).hexdigest(),"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"changes":"One explicit Void callback result, no body or capture change; source-only candidate pending semantic validation","files":[{"name":x.name,"sha256":hashlib.sha256(x.read_bytes()).hexdigest(),"bytes":x.stat().st_size} for x in d.iterdir() if x.is_file()]}
(d/"CANDIDATE_PROVENANCE.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
print(json.dumps({"candidate":info,"patch":patch.decode(),"discovery":discovery},ensure_ascii=False))

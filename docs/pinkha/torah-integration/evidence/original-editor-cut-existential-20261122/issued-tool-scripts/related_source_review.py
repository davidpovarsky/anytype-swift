import pathlib,subprocess,json,hashlib
r=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121");h="d8416b161ba7af42e8459d612a94f7591470513e"
d=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-textblock-existential-20261122")
paths=[
"Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/SimpleTable/Block/TextBlock/SimpleTablesTextBlockActionHandler.swift",
"Anytype/Sources/PresentationLayer/TextEditor/AccessoryView/SlashMenu/Handler/SlashMenuActionHandler.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageBlocksStateManager.swift"
]
rows=[]
for n,p in enumerate(paths):
 b=subprocess.run(["git","show",h+":"+p],cwd=r,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30).stdout
 (d/pathlib.PurePosixPath(p).name).write_bytes(b)
 lines=b.decode().splitlines()
 if n==0:view=b.decode()
 elif n==1:view="\n".join(f"{i+1} {x}" for i,x in enumerate(lines) if i<70 or 215<=i<280)
 else:view="\n".join(f"{i+1} {x}" for i,x in enumerate(lines) if i<85 or 510<=i<575)
 rows.append({"path":p,"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),"lines":len(lines),"source":view})
(d/"PASTEBOARD_CALL_SOURCE_REVIEW.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
print(json.dumps(rows,ensure_ascii=False))

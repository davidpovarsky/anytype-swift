import pathlib,subprocess,json,hashlib,datetime
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-editor-visibility-20261122")
assert not out.exists();out.mkdir()
ref="7b594f6f28961258d81b0eb2e7a29c7b047bb1d2"
path="Anytype/Sources/PresentationLayer/TextEditor/EditorPage/FlowLayout/Models/BlockIndentationStyle.swift"
def git(args,allowed=(0,)):
 p=subprocess.run(["git"]+args,cwd=repo,capture_output=True,timeout=90)
 assert p.returncode in allowed,(args,p.stderr.decode("utf-8","replace"))
 return p.stdout
assert git(["rev-parse","HEAD"]).decode().strip()==ref
assert not git(["status","--porcelain"])
raw=git(["show",ref+":"+path]);(out/"BlockIndentationStyle.before.swift").write_bytes(raw)
uses=git(["grep","-n","-F","BlockIndentationStyle",ref,"--","Anytype/Sources","Modules","OriginalEditorFramework","Tools"],(0,1)).decode()
gate=git(["grep","-n","-F","Unqualified original editor/document/writer declaration is public",ref,"--","Tools"],(0,1)).decode()
(out/"ORIGINAL_USE_SITES.txt").write_text(uses,encoding="utf-8",newline="\n")
(out/"GRAPH_GATE_LOCATION.txt").write_text(gate,encoding="utf-8",newline="\n")
idx={"ref":ref,"path":path,"blob":git(["rev-parse",ref+":"+path]).decode().strip(),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"source":raw.decode(),"uses":uses,"gate_location":gate,"at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/"SOURCE_PROVENANCE.json").write_text(json.dumps({k:v for k,v in idx.items() if k not in ("source","uses")},indent=2)+"\n",encoding="utf-8",newline="\n")
(out/"read_visibility_source.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps(idx,ensure_ascii=False))

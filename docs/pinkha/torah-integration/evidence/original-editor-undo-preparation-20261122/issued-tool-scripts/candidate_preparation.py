import pathlib,subprocess,json,hashlib,difflib
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121')
h='925b7e3cc687dcccad7703f57bd0a6b374dc1919'
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-undo-inference-compile-20261122')
assert not out.exists();out.mkdir()
def git(*a):
 p=subprocess.run(['git','-C',str(w),*a],capture_output=True,timeout=90);assert p.returncode==0,p.stderr.decode('utf8','replace');return p.stdout
assert git('rev-parse','HEAD').decode().strip()==h
assert not git('status','--porcelain=v1').strip()
path='Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoView.swift'
b=git('show',h+':'+path)
assert hashlib.sha256(b).hexdigest()=='5571bedc2a2bb3469096461b52777e776419b95fa510176bbba41804b9c5c24a'
t=b.decode()
for op in ['Undo','Redo']:
 old=f'AsyncButton(prepareAction: model.hasDocumentWriteOwner ? {{ model.prepare{op}() }} : nil)'
 new=f'AsyncButton(prepareAction: {op.lower()}Preparation)'
 assert t.count(old)==1
 t=t.replace(old,new)
anchor='    var body: some View {\n'
extra='''    private var undoPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasDocumentWriteOwner else { return nil }
        return { model.prepareUndo() }
    }

    private var redoPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasDocumentWriteOwner else { return nil }
        return { model.prepareRedo() }
    }

'''
assert t.count(anchor)==2
t=t.replace(anchor,extra+anchor,1)
c=t.encode()
p=''.join(difflib.unified_diff(b.decode().splitlines(True),t.splitlines(True),fromfile='a/'+path,tofile='b/'+path)).encode()
(out/'UNDO_BASE.swift').write_bytes(b)
(out/'UNDO_CANDIDATE.swift').write_bytes(c)
(out/'UNDO_PREPARATION.patch').write_bytes(p)
deps=[]
for q,name in [('Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoViewModel.swift','UNDO_MODEL.swift'),('Modules/DesignKit/Sources/DesignKit/Components/AsyncButton/AsyncButton.swift','ORIGINAL_ASYNC_BUTTON.swift')]:
 d=git('show',h+':'+q);(out/name).write_bytes(d);deps.append({'path':q,'snapshot':name,'sha256':hashlib.sha256(d).hexdigest(),'git_blob':git('rev-parse',h+':'+q).decode().strip()})
receipt={'source_head':h,'path':path,'source_sha256':hashlib.sha256(b).hexdigest(),'source_blob':git('rev-parse',h+':'+path).decode().strip(),'candidate_sha256':hashlib.sha256(c).hexdigest(),'patch_sha256':hashlib.sha256(p).hexdigest(),'dependencies':deps,'scope':'Explicitly typed deferred preparation only; original AsyncButton and model unchanged. Actual Apple acceptance pending.'}
(out/'SOURCE_PROVENANCE.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps({'directory':str(out),'manifest':receipt,'patch':p.decode(),'candidate':c.decode()}))

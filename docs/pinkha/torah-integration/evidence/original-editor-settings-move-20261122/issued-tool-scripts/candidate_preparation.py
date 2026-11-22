import subprocess,json,hashlib,pathlib,difflib,datetime
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
head="d5df214b50faafbae4b8eb3edcf8b27bcdc930b8"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
assert not out.exists(), "Candidate directory already exists; inspect instead of replay"
def git(*args):
 p=subprocess.run(["git",*args],cwd=repo,capture_output=True,timeout=50);p.check_returncode();return p.stdout
assert git("rev-parse","HEAD").decode().strip()==head
assert not git("status","--porcelain").strip(), "Frozen producer is not clean"
paths=[
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/TypePropertiesView/Model/TypePropertiesMoveHandler.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettingsMenu/ObjectSettingsMenuView.swift",
"Anytype/Sources/PresentationLayer/Modules/PublishToWeb/PublishToWebInternalView.swift"]
expected=["96b5167c6d7b60ca91f416beb9922264d345ab90259490397993a121ac2821b7","8b3c495068a5eef2bd8eff16330948bd7a90a90e0fbd7cc8b66618e041dd37cc","12e9acb59175c584060ca871d78992758671b1589c311e0ac155752c426ecbdd"]
bases=[]
for path,sha in zip(paths,expected):
 data=git("show",head+":"+path);assert hashlib.sha256(data).hexdigest()==sha;assert (repo/path).read_bytes()==data;bases.append(data.decode())
old='''            try await originalEditorScope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                try originalEditorScope.owner.validateDocument(document)
            }'''
new='''            try await MainActor.run {
                try originalEditorScope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                    try originalEditorScope.owner.validateDocument(document)
                }
            }'''
assert bases[0].count(old)==1
move=bases[0].replace(old,new)
settings=bases[1]
for old,new in [
("prepareAction: viewModel.viewModel.hasPreparedSource ? { viewModel.prepareConflictReset() } : nil,","prepareAction: conflictResetPreparation,"),
("prepareAction: viewModel.viewModel.hasPreparedSource ? { viewModel.prepareArchiveConfirmation() } : nil,","prepareAction: archiveConfirmationPreparation,")]:
 assert settings.count(old)==1;settings=settings.replace(old,new)
old='''publish: viewModel.viewModel.hasPreparedSource ? { action in
                    try viewModel.viewModel.withCurrentSource(action)
                } : nil'''
assert settings.count(old)==2;settings=settings.replace(old,"publish: currentSourcePublication")
settings_region='''    private var conflictResetPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { viewModel.prepareConflictReset() }
    }

    private var archiveConfirmationPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { viewModel.prepareArchiveConfirmation() }
    }

    private var currentSourcePublication: (@MainActor (@MainActor () -> Void) throws -> Void)? {
        guard viewModel.viewModel.hasPreparedSource else { return nil }
        return { action in
            try viewModel.viewModel.withCurrentSource(action)
        }
    }

'''
anchor="    @ViewBuilder\n    private func renderSection("
assert settings.count(anchor)==1;settings=settings.replace(anchor,settings_region+anchor)
publishing=bases[2]
for old,new in [
("prepareAction: model.hasPreparedSource ? { model.prepareUnpublish() } : nil,","prepareAction: unpublishPreparation,"),
("prepareAction: model.hasPreparedSource ? { model.preparePublish(action: .update) } : nil,","prepareAction: updatePreparation,"),
("prepareAction: model.hasPreparedSource ? { model.preparePublish(action: .create) } : nil,","prepareAction: publishPreparation,")]:
 assert publishing.count(old)==1;publishing=publishing.replace(old,new)
publishing_region='''    private var unpublishPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.prepareUnpublish() }
    }

    private var updatePreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.preparePublish(action: .update) }
    }

    private var publishPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasPreparedSource else { return nil }
        return { model.preparePublish(action: .create) }
    }

'''
anchor="    private var controlButtons: some View {"
assert publishing.count(anchor)==1;publishing=publishing.replace(anchor,publishing_region+anchor)
out.mkdir()
records=[]
for index,(path,base,candidate) in enumerate(zip(paths,bases,[move,settings,publishing])):
 stem=pathlib.Path(path).stem
 (out/(stem+".base.swift")).write_bytes(base.encode())
 (out/(stem+".candidate.swift")).write_bytes(candidate.encode())
 patch="".join(difflib.unified_diff(base.splitlines(keepends=True),candidate.splitlines(keepends=True),fromfile="a/"+path,tofile="b/"+path,n=5))
 (out/(stem+".patch")).write_bytes(patch.encode())
 records.append({"path":path,"base_sha256":hashlib.sha256(base.encode()).hexdigest(),"base_blob":git("rev-parse",head+":"+path).decode().strip(),"candidate_sha256":hashlib.sha256(candidate.encode()).hexdigest(),"patch_sha256":hashlib.sha256(patch.encode()).hexdigest(),"basis":"observed compiler diagnostic" if index<2 else "preventive exact same optional nested MainActor Sendable preparation pattern; no actual diagnostic","patch":patch})
(out/"SETTINGS_PROPERTIES.swift.txt").write_bytes(settings_region.encode())
(out/"PUBLISHING_PROPERTIES.swift.txt").write_bytes(publishing_region.encode())
deps=[
"Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/TypePropertiesView/Model/TypePropertiesDropDelegate.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/TypePropertiesView/TypePropertiesViewModel.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettings/ObjectSettingsViewModel.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettingsMenu/ObjectSettingsMenuViewModel.swift",
"Anytype/Sources/PresentationLayer/Modules/PublishToWeb/PublishToWebInternalViewModel.swift",
"Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettings/Alerts/ObjectSettingsResolveConflictAlert.swift",
"Anytype/Sources/PresentationLayer/Modules/Chat/Subviews/DeleteChatAlert/ChatDeleteChatAlert.swift",
"Modules/DesignKit/Sources/DesignKit/Components/AsyncButton/AsyncStandardButton.swift",
"Modules/DesignKit/Sources/DesignKit/Components/BottomAlert/BottomAlertButtonView.swift",
"Anytype/Sources/Models/Documents/Document/BaseDocumentProtocol.swift"]
dep_records=[]
for i,path in enumerate(deps):
 data=git("show",head+":"+path);name=f"DEPENDENCY_{i}.swift";(out/name).write_bytes(data)
 dep_records.append({"path":path,"snapshot":name,"blob":git("rev-parse",head+":"+path).decode().strip(),"sha256":hashlib.sha256(data).hexdigest()})
manifest={"source_head":head,"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"candidates":records,"dependencies":dep_records,"scope":"3 source-only candidate files, not yet applied, parsed, typechecked or qualified"}
(out/"CANDIDATE_PROVENANCE.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for record in records:print(json.dumps(record))
print(json.dumps({"out":str(out),"provenance_sha256":hashlib.sha256((out/"CANDIDATE_PROVENANCE.json").read_bytes()).hexdigest(),"dependencies":dep_records}))

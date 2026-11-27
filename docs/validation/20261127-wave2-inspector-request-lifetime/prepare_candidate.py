from pathlib import Path
import hashlib, json, difflib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source'
CANDIDATE = ROOT / 'candidate'
edits = []

def change(path, replacements, base=SOURCE):
    old = (base / path).read_text()
    text = old
    for before, after in replacements:
        count = text.count(before)
        assert count == 1, (path, before, count)
        text = text.replace(before, after, 1)
    target = CANDIDATE / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    edits.append({'path':path, 'source':str(base / path), 'replacements':replacements})

presenter = 'Modules/PinkhaTorahPresentation/Sources/PinkhaTorahPresentation/TorahSourcesSearchPresenter.swift'
factories = (ROOT / 'request-factories.swift').read_text()
change(presenter, [
    ('    private var searchEpoch: UInt = 0\n', '    private var presentationGeneration = UUID()\n    private var searchEpoch: UInt = 0\n'),
    ('    public func performSearch(debounce: Duration = .zero) async {\n', factories + '\n    public func performSearch(debounce: Duration = .zero) async {\n'),
    ('    public func cancelPendingRequests() {\n', '    public func cancelPendingRequests() {\n        presentationGeneration = UUID()\n'),
])

heart = 'Anytype/Sources/Pinkha/Torah/UI/TorahSourcesSearchView.swift'
change(heart, [
    ('    @Environment(\\.locale) private var locale\n\n    var body: some View {\n        VStack(spacing: 0) {', '    @Environment(\\.locale) private var locale\n\n    var body: some View {\n        let searchRequest = presenter.makeSearchRequest(debounce: .milliseconds(300))\n        let refreshRequest = presenter.makeAssociationRefreshRequest()\n        VStack(spacing: 0) {'),
    ('            await presenter.performSearch(debounce: .milliseconds(300))', '            await searchRequest()'),
    ('        .task(id: presenter.context.id) { await presenter.refreshAssociations() }', '        .task(id: presenter.context.id) { await refreshRequest() }'),
    ('                Task { await presenter.unlinkAssociation(item) }', '                let request = presenter.makeUnlinkRequest(item)\n                Task { await request() }'),
    ('                    action: { await presenter.performSearch() }', '                    action: presenter.makeSearchRequest()'),
    ('                Task { await presenter.link(result) }\n            } : result.scope == .references ? {\n                Task { await presenter.openReference(result) }', '                let request = presenter.makeLinkRequest(result)\n                Task { await request() }\n            } : result.scope == .references ? {\n                let request = presenter.makeOpenReferenceRequest(result)\n                Task { await request() }'),
    ('            onLink: {\n                Task { await presenter.link(result) }', '            onLink: {\n                let request = presenter.makeLinkRequest(result)\n                Task { await request() }'),
])

native = 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift'
change(native, [
    ('    @ViewBuilder private var searchContent: some View {\n        @Bindable var presenter = presenter\n', '    @ViewBuilder private var searchContent: some View {\n        @Bindable var presenter = presenter\n        let refreshRequest = presenter.makeAssociationRefreshRequest()\n'),
    ('                                Button(role: .destructive) { Task { await presenter.unlinkAssociation(item) } }', '                                Button(role: .destructive) {\n                                    let request = presenter.makeUnlinkRequest(item)\n                                    Task { await request() }\n                                }'),
    ('                            Task { await presenter.performSearch() }', '                            let request = presenter.makeSearchRequest()\n                            Task { await request() }'),
    ('                                    Task { await presenter.openReference(result) }', '                                    let request = presenter.makeOpenReferenceRequest(result)\n                                    Task { await request() }'),
    ('                                    Task { await presenter.link(result) }', '                                    let request = presenter.makeLinkRequest(result)\n                                    Task { await request() }'),
    ('                Task { await presenter.performSearch(debounce: .milliseconds(300)) }', '                let request = presenter.makeSearchRequest(debounce: .milliseconds(300))\n                Task { await request() }'),
    ('            .task { session.updateEffectiveLocale(locale); await presenter.refreshAssociations() }', '            .task { session.updateEffectiveLocale(locale); await refreshRequest() }'),
], base=ROOT / 'retry-source')

suffix_path = ROOT / 'queued-request-tests.swift'
if suffix_path.is_file():
    tests = 'AnyTypeTests/Pinkha/TorahSearchResolutionPublicationTests.swift'
    original = (SOURCE / tests).read_bytes()
    suffix = suffix_path.read_bytes()
    target = CANDIDATE / tests
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(original + b'\n' + suffix)
    edits.append({'path':tests,'source':str(SOURCE / tests),'append':b'\n'.hex()+suffix.hex()})

def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
map_path = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
old_map = (SOURCE / map_path).read_text()
new_map = old_map
map_replacements = []
for path in [presenter, heart]:
    before = blob((SOURCE/path).read_bytes()); after = blob((CANDIDATE/path).read_bytes())
    assert new_map.count(before) == 1
    new_map = new_map.replace(before, after, 1)
    map_replacements.append((before, after))
target = CANDIDATE / map_path
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(new_map)
edits.append({'path':map_path,'source':str(SOURCE/map_path),'replacements':map_replacements})

rows=[]; patches=[]; inverses=[]
for edit in edits:
    path=edit['path']; before=Path(edit['source']).read_bytes(); after=(CANDIDATE/path).read_bytes()
    if 'append' in edit:
        suffix=bytes.fromhex(edit['append']); assert after.endswith(suffix); restored=after[:-len(suffix)]
    else:
        restored=after.decode()
        for old,new in reversed(edit['replacements']):
            assert restored.count(new)==1,(path,new)
            restored=restored.replace(new,old,1)
        restored=restored.encode()
    assert restored==before,path
    row={'path':path,'before':{'sha256':hashlib.sha256(before).hexdigest(),'gitBlob':blob(before),'bytes':len(before)},'after':{'sha256':hashlib.sha256(after).hexdigest(),'gitBlob':blob(after),'bytes':len(after)}}
    rows.append(row); inverses.append({**row,'fullInverseExact':True})
    patches.append(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='a/'+path,tofile='b/'+path)))
(ROOT/'source.patch').write_text(''.join(patches))
(ROOT/'candidate-manifest.json').write_text(json.dumps({'schema':'inspector-queued-request-candidate-v1','base':'2752229aacf72f468f32a4bfe5fe0a91142f5dbe','nativeViewDonor':'1a890015578962bc6eab8c6e9bb70c51ce189cf3','status':'SOURCE_ONLY_NOT_COMPILED','files':rows},indent=2)+'\n')
(ROOT/'source-inverse.json').write_text(json.dumps({'schema':'inspector-queued-request-inverse-v1','files':inverses,'mapRowsBefore':len(json.loads(old_map)['changes']),'mapRowsAfter':len(json.loads(new_map)['changes']),'testsExecuted':False},indent=2)+'\n')
(ROOT/'literal-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
print(json.dumps(rows,indent=2))

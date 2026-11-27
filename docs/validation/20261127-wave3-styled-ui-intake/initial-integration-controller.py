import base64, gzip, hashlib, json, pathlib, re, subprocess, time, traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = '53a300d3a77920a2a4db09d13d9dc2e00ef5398e'
DONOR = '7380a797d13b279b6d19e43ade7af1929089b8ef'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
DP = 'docs/validation/20261127-wave2-native-styled-ui/'
PREFIX = 'docs/validation/20261127-wave3-styled-ui-intake'
NATIVE = 'NativeApp/UITests/NativeLaunchTests.swift'
MAP = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w2-styled-intake-payload.json.gz')
OUT = pathlib.Path('/tmp/pinkha-wave3-styled-ui-source-integration.json')

def h(b): return hashlib.sha256(b).hexdigest()
def b(*a): return subprocess.check_output(G + list(a), stderr=subprocess.PIPE)
def t(*a): return b(*a).decode().strip()
def owned(path, data, exclusive=True):
    code = 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);f=p.open(sys.argv[2]);f.write(sys.stdin.buffer.read());f.close()'
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT / path), 'xb' if exclusive else 'wb'], input=data, capture_output=True, check=True)

assert not OUT.exists()
receipt = {'schema':'pinkha-wave3-styled-ui-source-integration/v1','parent':START,'donor':DONOR,'startedAt':time.time(),'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    packed = PAYLOAD.read_bytes()
    assert h(packed) == 'd28fb8f681b12065aba1a27fdf40aea086871d16a8711e5f8848348b2d137ec5'
    payload = json.loads(gzip.decompress(packed))
    retained = {}
    for row in payload['files']:
        value = base64.b64decode(row['base64'], validate=True)
        assert h(value) == row['sha256'] and len(value) == row['bytes']
        assert row['name'] in ['independent-review.json','independent-byte-proof.json','font-run-correction.diff','verify_source.py']
        assert row['name'] not in retained
        retained[row['name']] = value
    assert h(retained['independent-review.json']) == '4a06ea24b47773e5794ccc1636de1fe0e7ac4ad27e4b279f42a4073ffcd867d5'
    review = json.loads(retained['independent-review.json'])
    assert review['donorCommit'] == DONOR and review['comparedRootCommit'] == START
    assert review['status'] == 'READY_FOR_ROOT_SOURCE_INTEGRATION_EXECUTION_REMAINS_CLOSED'
    assert t('rev-parse','HEAD') == START and t('symbolic-ref','HEAD') == REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status = t('status','--porcelain=v1','--untracked-files=all')
    assert t('ls-remote','origin',REF).split()[0] == START
    assert t('rev-parse',DONOR+'^{tree}') == review['donorTree']
    assert t('rev-parse',DONOR+'^') == review['parentCommit']
    paths = [(r['status'],r['filename']) for r in review['changedPaths']]
    assert len(paths) == 14 and len([p for s,p in paths if s == 'modified']) == 3
    actual = t('diff-tree','--no-commit-id','--name-status','--no-renames','-r',DONOR).splitlines()
    assert actual == [('M' if s == 'modified' else 'A') + '\t' + p for s,p in paths]
    for row in review['changedPaths']:
        assert t('rev-parse',DONOR+':'+row['filename']) == row['sha']
        if row['status'] == 'added': assert row['filename'].startswith(DP) and not (ROOT/row['filename']).exists()
    source_rows = []
    for name in ['AnyNativeEditor.swift','AnySemanticAnchorObservation.swift']:
        path = 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/' + name
        inv = json.loads(b('show',DONOR+':'+DP+name+'.inverse.json'))
        before, after = b('show',START+':'+path), b('show',DONOR+':'+path)
        assert h(before) == inv['beforeSHA256'] and h(after) == inv['afterSHA256']
        restored = after
        for op in reversed(inv['changes']):
            new, old = op['new'].encode(), op['old'].encode()
            assert restored.count(new) == 1
            restored = restored.replace(new, old, 1)
        assert restored == before
        source_rows.append({'path':path,'beforeSHA256':h(before),'afterSHA256':h(after),'literalInverseOperations':len(inv['changes'])})
    native_before, native_after = b('show',START+':'+NATIVE), b('show',DONOR+':'+NATIVE)
    assert len(native_before) == 237631 and h(native_before) == '5d3462b25dd64423cf33fc1243b2d734acea55011a9e5da4c66004022685958a'
    assert len(native_after) == 271344 and h(native_after) == '8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86'
    assert native_after.startswith(native_before)
    assert len(re.findall(rb'func (test\w+)\(',native_before)) == 21 and len(re.findall(rb'func (test\w+)\(',native_after)) == 23
    preserved_paths = [MAP,GATE,'Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json']
    preserved_paths += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
    preserved = {p:b('show',START+':'+p) for p in preserved_paths}
    assert len(json.loads(preserved[MAP])['changes']) == 129
    preview = subprocess.run(G+['merge-tree','--write-tree',START,DONOR],capture_output=True,text=True)
    assert preview.returncode == 1 and preview.stdout.splitlines()[0] == '0efc766b8656420f90388755e7fc3ff4ce2945f7'
    conflict_lines = [x for x in preview.stdout.splitlines() if re.match(r'^100644 [a-f0-9]{40} [123]\t',x)]
    assert len(conflict_lines) == 3 and all(x.endswith('\t'+NATIVE) for x in conflict_lines)
    assert t('diff','--name-only',START,preview.stdout.splitlines()[0]).splitlines() == sorted(p for s,p in paths)
    receipt['previewConflict'] = {'stdout':preview.stdout,'stderr':preview.stderr,'resolution':'Exact donor NativeLaunch bytes, verified to contain the complete current237631-byte21-method prefix plus only the reviewed33713-byte2-method suffix.'}
    merged = subprocess.run(G+['merge','--no-ff','--no-commit',DONOR],capture_output=True,text=True)
    assert merged.returncode == 1
    unmerged = t('ls-files','-u').splitlines()
    assert len(unmerged) == 3 and all(x.endswith('\t'+NATIVE) for x in unmerged)
    owned(NATIVE,native_after,exclusive=False)
    b('add','--',NATIVE)
    assert not t('ls-files','-u')
    for s,p in paths: assert (ROOT/p).read_bytes() == b('show',DONOR+':'+p),p
    assert t('diff','--cached','--name-only').splitlines() == sorted(p for s,p in paths)
    prior = pathlib.Path('/tmp/pinkha-wave3-hanlin-stop-source-integration.json').read_bytes()
    assert h(prior) == '221d2100bb9b1fc655a22a0af67f0870bd9cb43b9c36085005e323d64ad8c255' and json.loads(prior)['head'] == START
    retained['prior-hanlin-stop-integration.json'] = prior
    retained['root-integration-controller.py'] = pathlib.Path(__file__).read_bytes()
    note = {'schema':'pinkha-root-styled-ui-source-review/v1','rootParent':START,'donor':DONOR,'donorTree':review['donorTree'],
      'sourceRows':source_rows,'literalInverseOperations':5,'nativeLaunchBefore':{'bytes':len(native_before),'sha256':h(native_before),'methods':21},
      'nativeLaunchAfter':{'bytes':len(native_after),'sha256':h(native_after),'methods':23},'completeCurrentPrefixPreserved':True,
      'conflictResolution':receipt['previewConflict'],'independentReviewSHA256':h(retained['independent-review.json']),
      'sourceRetentionMapUnchanged':True,'nativeSDKPinsAndLocksAndProjectTargetsUnchanged':True,
      'review':[
        'Root read the editor and original read-only observer changes, full original9-choice catalog/menu and cold persistence obligations, live Dynamic Type predicates and finite private rendezvous. Only actual mounted UITextView attributes are observed behind existing DEBUG/simulator/owned-scope controls.',
        'Five literal inverse operations reconstruct both exact current sources. The complete current21-method NativeLaunch is a byte-exact prefix; the automatic append conflict is resolved only by the proven additive donor bytes.',
        'All expanded attributed font runs and empty typing font must grow; actual same-process UIKit/native/selection equality and nominal restoration remain required. Original failed first-run-only review remains retained.',
        'NativeLaunch23 belongs to the separate PinkhaAnyNativeUITests runner. Shared Stage1 UI compilation cannot qualify its two original compiler inputs. Its existing sole controller requires a separately reviewed live-size setter/readback/finally-restore implementation.',
        'This merge is original source integration only. Actual exact-source compilation, enumeration, native persistence, live Dynamic Type, visual language/device/appearance cells and physical-device acceptance remain NOT_RUN.'
      ],'AppleCompilation':'NOT_RUN','runtime':'NOT_RUN','visual':'NOT_RUN','physicalDevice':'NOT_RUN','ReleaseArchive':'NOT_RUN','TestFlight':'NOT_RUN'}
    retained['root-source-review.json'] = (json.dumps(note,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    for name,data in retained.items(): owned(PREFIX+'/'+name,data)
    b('add','--',PREFIX)
    b('diff','--cached','--check','--',*(p for s,p in paths if p.endswith('.swift')),PREFIX)
    for p,v in preserved.items(): assert (ROOT/p).read_bytes() == v,p
    expected = sorted([p for s,p in paths]+[PREFIX+'/'+n for n in retained])
    assert t('diff','--cached','--name-only').splitlines() == expected
    tree = t('write-tree'); gate = pathlib.Path('/tmp/pinkha-wave3-styled-ui-retention.json'); assert not gate.exists()
    run = subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout); pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
    result = json.loads(gate.read_bytes())
    assert run.returncode == 0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors']) == 129
    msg = 'Integrate original native styled-block and live typography acceptance source\n\nRetain the complete original21-method runner prefix and existing editor behavior. Resolve only the proven additive NativeLaunch append conflict. Actual separate runner compilation and native/UI acceptance remain open.\n\nIntegrated from '+DONOR+'\n'
    subprocess.run(G+['commit','-F','-'],input=msg.encode(),capture_output=True,check=True)
    head = t('rev-parse','HEAD'); assert t('show','-s','--format=%P',head).split() == [START,DONOR]
    assert t('status','--porcelain=v1','--untracked-files=all') == status
    assert t('ls-remote','origin',REF).split()[0] == START
    push = subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),payloadSHA256=h(packed),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,sourceMapUnchanged=True,newTestsExecuted=0)
    if push.returncode == 0:
        assert t('ls-remote','origin',REF).split()[0] == head
        receipt['normalPushReadback'] = head
    assert push.returncode == 0
    receipt['state'] = 'SOURCE_INTEGRATED_AND_PUBLISHED'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'; receipt['error'] = traceback.format_exc()
    raise
finally:
    receipt['completedAt'] = time.time()
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)

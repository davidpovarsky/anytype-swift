"""Normal exact source merges with closed E, App10 and T5 activation boundaries."""
import base64, difflib, gzip, hashlib, json, os, pathlib, re, subprocess, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='919626d8a5a2701c2dfb56277a657fa593700b98'
START_TREE='314816d893ec5b9a3643526da3080e2ede9a4a89'
PRIOR_BYTES=47998
PRIOR_SHA256='7efdf7e39beecfdd701c382db1afa07167706cfd9822ec877f262353ee34f2a6'
PRIOR_CONTROLLER_SHA256='571e30cc70a01493aab1f024e2914771c4ad2be413373425efd95172cc612b9e'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-e-properties-app10-t5-intake'
OUT=pathlib.Path('/tmp/pinkha-root-e-properties-app10-t5-source-integration-20261127.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-e-properties-app10-t5-source-payload.json.gz')
PRIOR=pathlib.Path('/tmp/pinkha-root-sdk4cb-host-source-integration-20261127.json')
GATE='Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT=pathlib.Path('/tmp/pinkha-root-e-properties-app10-t5-source-retention-20261127.json')
EXPECTED_DONORS=['d860cb15de479556110c5e6efa07e739fb0d07fc','21d63bef8950f8b927f0d8d3b4b052758bc98fcb','6abd34abc0ab3388d82dc4a9884e205f9fe8ab74']

def h(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def match(raw,row):assert len(raw)==row['bytes'] and h(raw)==row['sha256'] and blob(raw)==row['gitBlob']
def resources():
    rows={}
    for name,path,floor in [('root','/',2147483648),('development',str(ROOT),536870912)]:
        s=os.statvfs(path);free=s.f_bavail*s.f_frsize
        assert free>=floor+67108864,(name,free,floor,'fixed64MiB source allowance')
        rows[name]={'freeBytes':free,'floorBytes':floor,'sourceAllowanceBytes':67108864}
    return rows
def safe_path(path):
    p = pathlib.PurePosixPath(path)
    assert not p.is_absolute() and '..' not in p.parts and str(p) == path and '\0' not in path
    return path
def destination_preflight(path, previous):
    target = ROOT / safe_path(path)
    for parent in [target, *target.parents]:
        if parent == ROOT:
            break
        assert not parent.is_symlink(), str(parent)
    if previous is None:
        assert not target.exists(), ('preserve existing untracked destination', path)
    else:
        assert target.is_file() and target.read_bytes() == previous, path
def owned(path, raw, replace):
    safe_path(path)
    code = '''import pathlib,sys
root=pathlib.Path(sys.argv[1]);relative=pathlib.PurePosixPath(sys.argv[2]);p=root/relative
for parent in [p,*p.parents]:
 if parent==root:break
 assert not parent.is_symlink(),str(parent)
p.parent.mkdir(parents=True,exist_ok=True)
if sys.argv[3]=='wb':assert p.is_file()
with p.open(sys.argv[3]) as stream:stream.write(sys.stdin.buffer.read())
'''
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT), path, 'wb' if replace else 'xb'],
                   input=raw, capture_output=True, check=True, timeout=30)
def write_blob(raw):
    result = subprocess.run(G + ['hash-object', '-w', '--stdin'], input=raw,
                            capture_output=True, check=True, timeout=30).stdout.decode().strip()
    assert result == blob(raw)
    return result
def private_tree(entries):
    code = '''import json,os,subprocess,sys,tempfile
root,start,entries=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-e-properties-app10-t5-full-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index')
 subprocess.run(g+['read-tree',start],env=env,capture_output=True,check=True,timeout=30)
 for path,sha in sorted(entries.items()):
  subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+sha+','+path],env=env,capture_output=True,check=True,timeout=30)
 print(subprocess.run(g+['write-tree'],env=env,capture_output=True,check=True,timeout=30).stdout.decode().strip())
'''
    return subprocess.run(PRE + ['python3', '-B', '-c', code],
                          input=json.dumps([str(ROOT), START, entries]).encode(),
                          capture_output=True, check=True, timeout=90).stdout.decode().strip()
def exact_changes(reference, expected):
    values = t('diff', '--name-status', '-z', START, reference).split('\0')
    if values and values[-1] == '':
        values.pop()
    assert len(values) % 2 == 0
    actual = dict(zip(values[1::2], values[0::2]))
    assert len(actual) == len(expected) and actual == expected, actual
def diff_check(args,expected):
    p=subprocess.run(G+args,capture_output=True)
    receipt.setdefault('diffChecks',[]).append({'argv':args,'exit':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()})
    assert p.returncode==expected['exit'] and p.stdout.decode()==expected['stdout'] and p.stderr.decode()==expected['stderr']
def pins(expectedKit,manifestSHA,lockSHA):
    sdk=json.loads(b('show',':Tools/Hanlin/source.json'))
    assert sdk['revision']=='4cb6454c1c6e110ead73179c06ada9e909bf250b'
    common=b('show',':Tools/MiniApps/receipt_admission.py');assert h(common)=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    stage=b('show',':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift');assert h(stage)=='c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    manifest=b('show',':Modules/PinkhaTorahPresentation/Package.swift');assert h(manifest)==manifestSHA and expectedKit.encode() in manifest
    lock=b('show',':Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved');assert h(lock)==lockSHA
    values=json.loads(lock)['pins'];assert len(values)==56
    p={x['identity']:x['state'] for x in values};assert len(p)==56
    assert p['torahinspectorkit']=={'revision':expectedKit}
    assert p['swift-collections']=={'revision':'7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e','version':'1.3.0'}
    for path,row in payload['protectedSDKOutputs'].items():match(b('show',':'+path),row)
    assert len(payload['protectedSDKOutputs'])==6
    source_map=json.loads(b('show',':docs/any-engine-port/SOURCE_REFACTOR_MAP.json'))
    assert len(source_map['changes'])==132
    protobuf=b('show',':Modules/ProtobufMessages/Package.swift')
    assert h(protobuf)=='1cc18e497d8385c9f6a34c039aac3678b72963507f095567660a1fa51db64220'
    core_raw=b('show',':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json')
    assert h(core_raw)=='81d178d6d829dc2eff201b8b8dcd190db2da79dc68a6cc06f36ca0d8a90d2778'
    core=json.loads(core_raw)['files'];assert len(core)==15
    for path,row in core.items():match(b('show',':'+path),row)
    return {'sdk':sdk['revision'],'kit':expectedKit,'kitManifestSHA256':h(manifest),'packageResolvedSHA256':h(lock),'allPackagePins':values,'collections':p['swift-collections'],'common57SHA256':h(common),'stage1SHA256':h(stage),'protobufPackageSHA256':h(protobuf),'core15ManifestSHA256':h(core_raw),'protectedSDKOutputs':payload['protectedSDKOutputs']}
def closed_activation(contents):
    app=json.loads(contents['Tools/PinkhaDualEngineRuntime/hosted_property_cache_bin/activation.json'])
    assert app['readyForExecution'] is False and app['plans']==[]
    assert app['expectedMethods']==10 and app['expectedCases']==18
    for key in ('appSourceSHA','appSourceTree','buildReceiptSHA256','hostedOwnerSHA256','native23CompilerReceiptSHA256','nativeSourceManifestSHA256'):assert app[key] is None
    t5=json.loads(contents['Tools/PinkhaDualEngineRuntime/hosted_t5/activation.json'])
    assert t5['readyForRuntime'] is False and t5['plans']==[] and t5['finalProducerTuple'] is None
    assert t5['compiledSourceCounts']==[57,10,2] and t5['runtimeExecuted'] is False and t5['historicalFixturesReused'] is False
def controller_inverse(original,current):
    # Exact byte spans, not semantic substitutions or normalization.
    old_lines=original.splitlines(keepends=True);new_lines=current.splitlines(keepends=True)
    old_offsets=[0];new_offsets=[0]
    for line in old_lines:old_offsets.append(old_offsets[-1]+len(line))
    for line in new_lines:new_offsets.append(new_offsets[-1]+len(line))
    operations=[]
    for tag,a,z,c,d in difflib.SequenceMatcher(a=old_lines,b=new_lines,autojunk=False).get_opcodes():
        if tag=='equal':continue
        operations.append({'originalStartByte':old_offsets[a],'originalEndByte':old_offsets[z],
                           'newStartByte':new_offsets[c],'newEndByte':new_offsets[d],
                           'originalBase64':base64.b64encode(original[old_offsets[a]:old_offsets[z]]).decode(),
                           'newBase64':base64.b64encode(current[new_offsets[c]:new_offsets[d]]).decode()})
    restored=current
    for op in reversed(operations):
        start,end=op['newStartByte'],op['newEndByte'];assert restored[start:end]==base64.b64decode(op['newBase64'])
        restored=restored[:start]+base64.b64decode(op['originalBase64'])+restored[end:]
    assert restored==original
    return {'schema':'pinkha-full-original-controller-byte-inverse-v1','originalSHA256':h(original),'currentSHA256':h(current),'originalBytes':len(original),'currentBytes':len(current),'operations':operations,'fullOriginalRestored':True}

# Unbound preparation must stop before any host evidence, claim or Git operation.
assert re.fullmatch('[0-9a-f]{40}',START) and re.fullmatch('[0-9a-f]{40}',START_TREE)
assert re.fullmatch('[0-9a-f]{64}',PRIOR_SHA256) and re.fullmatch('[0-9a-f]{64}',PRIOR_CONTROLLER_SHA256) and PRIOR_BYTES>0
assert ROOT.resolve()==ROOT and ROOT.is_dir() and not OUT.exists()
receipt={'schema':'pinkha-root-e-properties-app10-t5-source-integration/v1','startedAt':time.time(),'parent':START,'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
    receipt['resourceBefore']=resources()
    packed=PAYLOAD.read_bytes();assert len(packed)==1851982 and h(packed)=='267d438158cb3dd1c697814fe311e413644af755c99e12c9054fc6e253e47298'
    raw=gzip.decompress(packed);assert len(raw)==6011479 and h(raw)=='0aca7a94b82c7b1d9f8d8bce3f900f2908e1fc9ef5e1c3d9de5dab2c2246f80f'
    payload=json.loads(raw);assert payload['requiresSuccessfulSDK571Integration'] and payload['sourceRetentionRows']==132
    assert payload['executionReady'] is False and payload['eFactoryActivationPermitted'] is False and payload['packageFlagProposalIncluded'] is False
    assert t('rev-parse','HEAD')==START and t('rev-parse','HEAD^{tree}')==START_TREE and t('symbolic-ref','HEAD')==REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status=b('status','--porcelain=v1','--untracked-files=all');untracked=b('ls-files','--others','--exclude-standard','-z')
    assert t('ls-remote','origin',REF).split()[0]==START
    beforePins=pins('26beca175d64a4d34e3567f2bbb4bf308d714478','e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494','4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689')
    prior=PRIOR.read_bytes();assert len(prior)==PRIOR_BYTES and h(prior)==PRIOR_SHA256
    p=json.loads(prior);assert p['state']=='SDK4CB_HOST_SOURCE_PUBLISHED_RUNTIME_PENDING'
    assert p['head']==START and p['tree']==START_TREE and p['normalPushReadback']==START and p['reviewedRefactors']==132
    assert p['controllerSHA256']==PRIOR_CONTROLLER_SHA256 and p['parent']=='e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff'
    assert p['sourceRetentionPassed'] is True and p['pushExit']==0
    paths=set(t('ls-tree','-r','--name-only',START).splitlines());rows=payload['files']
    assert len(rows)==217 and sum(r['status']=='M' for r in rows.values())==4
    assert not set(rows).intersection(payload['excludedChanges']) and not set(rows).intersection(payload['protectedSDKOutputs'])
    donors=[r['commit'] for r in payload['donors']];assert donors==EXPECTED_DONORS
    b('-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',*donors)
    donor_paths=set()
    for donor in payload['donors']:
        for link in donor['chain']:
            assert t('show','-s','--format=%P',link['commit']).split()==[link['parent']]
            assert t('rev-parse',link['commit']+'^{tree}')==link['tree']
        subprocess.run(G+['merge-base','--is-ancestor',donor['base'],START],capture_output=True,check=True)
        selected={r['path'] for r in donor['files']};assert not donor_paths.intersection(selected);donor_paths.update(selected)
        assert t('diff','--name-only',donor['base'],donor['commit']).splitlines()==sorted(selected)
        assert dict(line.split('\t')[::-1] for line in t('diff','--name-status',donor['base'],donor['commit']).splitlines())=={p:rows[p]['status'] for p in selected}
        for path in selected:
            match(b('show',donor['commit']+':'+path),rows[path]['after'])
            assert t('ls-tree',donor['commit'],'--',path).split()[0]=='100644'
    root_new=payload['rootNewFiles'];assert len(root_new)==83 and len(set(root_new))==83
    assert set(root_new).isdisjoint(donor_paths) and set(root_new)|donor_paths==set(rows)
    contents={}
    for path,row in rows.items():
        safe_path(path);value=base64.b64decode(row['base64'],validate=True);match(value,row['after'])
        assert row['after']['gitMode']=='100644'
        if row['status']=='A':
            assert path not in paths;destination_preflight(path,None)
        else:
            assert path in paths;previous=b('show',START+':'+path);match(previous,row['before'])
            assert previous==base64.b64decode(row['beforeBase64'],validate=True)
            assert t('ls-tree',START,'--',path).split()[0]=='100644';destination_preflight(path,previous)
        contents[path]=value
    assert all(rows[path]['status']=='A' for path in root_new)
    closed_activation(contents)
    gate_original=b('show',START+':'+GATE);self_raw=pathlib.Path(__file__).read_bytes()
    entries={path:write_blob(value) for path,value in contents.items()}
    preview=private_tree(entries);expected_source={path:row['status'] for path,row in rows.items()}
    exact_changes(preview,expected_source);diff_check(['diff','--check',START,preview],payload['diffCheck'])
    intake={'schema':'pinkha-root-e-properties-app10-t5-source-intake/v1','parent':START,'parentTree':START_TREE,
            'donors':donors,'files':{path:{k:v for k,v in row.items() if k not in ('base64','beforeBase64')} for path,row in rows.items()},
            'wholeMergeTreeEqualsReviewedInputs':True,'expectedSourceTree':preview,'rootNewFiles':root_new,
            'priorSDKReceiptSHA256':h(prior),'protectedPins':beforePins,'sourceRetentionRows':132,
            'untrackedPathListSHA256':h(untracked),'originalGateBlob':blob(gate_original),
            'sourceDiffCheck':payload['diffCheck'],'completeDiffCheck':payload['completeDiffCheck'],
            'controllerSHA256':h(self_raw),'payloadSHA256':h(raw),'transportSHA256':h(packed),
            'eFactoryActivated':False,'packageFlagProposedOrChanged':False,'runtimeActivated':False,
            'newTestsExecuted':0,'knownOpenGaps':payload['knownOpenGaps'],
            'scope':'Source checkpoint only. E factory disabled; App10 and T5 remain closed. Preserve SDK4cb source, all132 map rows, Kit26, all55 other pins, common57, Stage1, Core15, native inputs and untracked paths.'}
    evidence={'root-source-intake.json':(json.dumps(intake,sort_keys=True,indent=2)+'\n').encode(),
              'root-integration-controller.py':self_raw,'prior-sdk571-integration.original.json':prior}
    for name,row in payload['evidence'].items():
        value=base64.b64decode(row['base64'],validate=True);match(value,row);assert name not in evidence;evidence[name]=value
    original=evidence['prior-successful-integration-controller.original.py']
    assert h(original)=='3bd2dccbe1cdad803fa2554ad1d28eff754083e923241744672b71445f629729'
    evidence['root-controller-full-original-inverse.json']=(json.dumps(controller_inverse(original,self_raw),sort_keys=True,indent=2)+'\n').encode()
    for name,value in evidence.items():
        path=PREFIX+'/'+safe_path(name);assert path not in paths and path not in contents
        destination_preflight(path,None);entries[path]=write_blob(value)
    expected={**expected_source,**{PREFIX+'/'+name:'A' for name in evidence}}
    whole_preview=private_tree(entries);exact_changes(whole_preview,expected)
    diff_check(['diff','--check',START,whole_preview],payload['completeDiffCheck']);resources()
    # Preserve complete START tree and every reviewed original before the normal merge.
    assert t('rev-parse','HEAD')==START and t('write-tree')==START_TREE
    assert b('status','--porcelain=v1','--untracked-files=all')==status and b('ls-files','--others','--exclude-standard','-z')==untracked
    assert t('ls-remote','origin',REF).split()[0]==START
    receipt.update(phase='NORMAL_SOURCE_MERGE',expectedSourceTree=preview,expectedTree=whole_preview)
    merge=subprocess.run(G+['merge','--no-ff','--no-commit',*donors],capture_output=True)
    receipt['merge']={'exit':merge.returncode,'stdout':merge.stdout.decode(),'stderr':merge.stderr.decode()}
    assert merge.returncode==0 and not t('diff','--name-only','--diff-filter=U')
    assert pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).read_text().split()==donors
    for path in root_new:owned(path,contents[path],replace=False)
    b('add','--sparse','--',*root_new)
    assert t('write-tree')==preview and t('diff','--cached','--name-only').splitlines()==sorted(rows)
    afterPins=pins('26beca175d64a4d34e3567f2bbb4bf308d714478','e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494','4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689')
    assert beforePins==afterPins
    for name,value in evidence.items():owned(PREFIX+'/'+name,value,replace=False)
    b('add','--sparse','--',*[PREFIX+'/'+name for name in sorted(evidence)])
    assert t('write-tree')==whole_preview and t('diff','--cached','--name-only').splitlines()==sorted(expected)
    exact_changes(whole_preview,expected);diff_check(['diff','--cached','--check'],payload['completeDiffCheck'])
    assert not t('diff','--name-only') and b('ls-files','--others','--exclude-standard','-z')==untracked
    assert b('show',':'+GATE)==gate_original and (ROOT/GATE).read_bytes()==gate_original
    assert not GATE_OUT.exists() and not pathlib.Path(str(GATE_OUT)+'.stdout').exists() and not pathlib.Path(str(GATE_OUT)+'.stderr').exists()
    receipt['phase']='SOURCE_RETENTION_GATE'
    p=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',whole_preview,'--output',str(GATE_OUT)],cwd=ROOT,capture_output=True,timeout=120)
    pathlib.Path(str(GATE_OUT)+'.stdout').open('xb').write(p.stdout);pathlib.Path(str(GATE_OUT)+'.stderr').open('xb').write(p.stderr)
    result=json.loads(GATE_OUT.read_bytes());assert p.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==132
    assert pins('26beca175d64a4d34e3567f2bbb4bf308d714478','e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494','4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689')==afterPins
    assert t('write-tree')==whole_preview and t('rev-parse','HEAD')==START
    assert b('ls-files','--others','--exclude-standard','-z')==untracked
    message='Merge reviewed E source, Properties lifetime and closed App10/T5 controls\n\nPreserve all217 exact source/evidence paths, four original preimages and three normal donor ancestries. Add83 root-only closed control/evidence files. E Apple factory stays disabled and its Package flag is not applied; the queued-owner handoff blocker remains explicit. App10/T5 remain false/null with no runtime acceptance. Verify the complete current-root private index, all132 retention rows, SDK4cb six-file outputs, Kit26 and all55 other pins, common57, Stage1, Core15 and original untracked paths. Preserve54 literal single-space lines in original Properties patch evidence. No Apple build, tests, signing or TestFlight claim.\n'
    receipt['phase']='COMMIT_SOURCE'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');receipt['head']=head
    assert t('show','-s','--format=%P',head).split()==[START]+donors and t('rev-parse','HEAD^{tree}')==whole_preview
    assert b('status','--porcelain=v1','--untracked-files=all')==status and b('ls-files','--others','--exclude-standard','-z')==untracked
    assert t('symbolic-ref','HEAD')==REF and t('ls-remote','origin',REF).split()[0]==START
    receipt.update(tree=whole_preview,donors=donors,files=sorted(expected),inputPins=afterPins,sourceRetentionPassed=True,reviewedRefactors=132,
                   retentionSHA256=h(GATE_OUT.read_bytes()),intakeSHA256=h(evidence['root-source-intake.json']),controllerSHA256=h(self_raw),
                   payloadSHA256=h(raw),transportSHA256=h(packed),newTestsExecuted=0,eFactoryActivated=False,runtimeActivated=False)
    receipt['phase']='NORMAL_PUSH'
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr)
    if push.returncode==0:
        assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['resourceAfter']=resources();receipt['state']='SOURCE_MERGED_E_DISABLED_APP10_T5_CLOSED_RUNTIME_PENDING'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time()
    try:
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
        print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
    except BaseException:
        if receipt['state']!='FAILED_PRESERVED':raise
        print(json.dumps({'state':'FAILED_PRESERVED','firstFailure':receipt.get('error'),'terminalReceiptFailure':traceback.format_exc(),'head':receipt.get('head')}),flush=True)

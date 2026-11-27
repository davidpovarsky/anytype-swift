#!/usr/bin/env python3
"""Local byte/AST/JSON/Merkle review only; never import or execute a donor."""
import ast
import base64
import collections
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
OUT = ROOT / 'prepared1'
SOURCE = ROOT / 'source'
T = 'Tools/AnyEngineValidation/bookmark_native_create_20261127/'
D = 'docs/validation/20261127-bookmark-native-create/'
BASE = '5a45fe4af2c4601faad181f81d391057c1237654'
BASE_TREE = '13578db08a5e215fd70e88209e6ec409135440e2'
DONOR = 'e8331a3943db99cc8c73b9c61c6120b4ecf5ee7d'
DONOR_TREE = 'c78246b891799d5583b204c1bef6337e5fc0b19a'
PARENT = '6b91db33d325f22b62d829051db203121c6cdb8e'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def ident(raw, mode='100644'):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
            'gitMode': mode}

def data(path):
    return json.loads(Path(path).read_bytes())

def primary(name):
    obj = data(ROOT / 'primary' / name)
    value = obj['structuredContent']['content']
    return json.loads(value)

def raw(name):
    return (SOURCE / name).read_bytes()

def put(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as handle:
        handle.write(content)
    return ident(content)

def parse_leaves(value):
    found = {}
    for record in value.split(b'\0'):
        if not record:
            continue
        info, name = record.split(b'\t', 1)
        mode, kind, blob = info.decode().split(' ')
        name = name.decode()
        require(name not in found and kind in ('blob', 'commit'), 'unique finite Git leaf')
        found[name] = (mode, blob)
    return found

def tree(leaves):
    root = {}
    for name, value in leaves.items():
        node = root
        parts = name.split('/')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        require(parts[-1] not in node, 'no path alias/collision')
        node[parts[-1]] = value
    def walk(node):
        rows = []
        for name, value in node.items():
            is_dir = isinstance(value, dict)
            mode, digest = ('40000', walk(value)) if is_dir else value
            rows.append(((name + ('/' if is_dir else '')).encode(),
                         mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(digest)))
        content = b''.join(row[1] for row in sorted(rows))
        return hashlib.sha1(b'tree ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    return walk(root)

def inverse(before, after):
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    ao, bo = [0], [0]
    for line in a:
        ao.append(ao[-1] + len(line))
    for line in b:
        bo.append(bo[-1] + len(line))
    ops = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        ops.append({'beforeStart': ao[i], 'beforeEnd': ao[j], 'afterStart': bo[k], 'afterEnd': bo[l],
                    'beforeBase64': base64.b64encode(before[ao[i]:ao[j]]).decode(),
                    'afterBase64': base64.b64encode(after[bo[k]:bo[l]]).decode()})
    result = after
    for op in reversed(ops):
        old = base64.b64decode(op['beforeBase64'])
        new = base64.b64decode(op['afterBase64'])
        require(result[op['afterStart']:op['afterEnd']] == new, 'literal inverse after bytes')
        result = result[:op['afterStart']] + old + result[op['afterEnd']:]
    require(result == before, 'whole original reconstructed')
    result = before
    for op in reversed(ops):
        old = base64.b64decode(op['beforeBase64'])
        new = base64.b64decode(op['afterBase64'])
        require(result[op['beforeStart']:op['beforeEnd']] == old, 'literal forward before bytes')
        result = result[:op['beforeStart']] + new + result[op['beforeEnd']:]
    require(result == after, 'whole successor reconstructed')
    return {'before': ident(before), 'after': ident(after), 'operations': ops,
            'wholeForwardExact': True, 'wholeInverseExact': True}

def overlay_path(name):
    prefix = '.runtime-artifacts/sdk-source/'
    return T + 'overlay/' + ('sdk/' + name[len(prefix):] if name.startswith(prefix) else 'any/' + name)

def selected_ast_literals(content, names):
    values = {}
    for node in ast.parse(content).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            values[node.targets[0].id] = ast.literal_eval(node.value)
    require(set(values) == set(names), 'exact literal source dictionaries')
    return values

def declaration(content, name):
    nodes = [n for n in ast.parse(content).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    require(len(nodes) == 1, 'one declaration ' + name)
    n = nodes[0]
    first = min([n.lineno] + [x.lineno for x in n.decorator_list])
    return b''.join(content.splitlines(keepends=True)[first-1:n.end_lineno])

def go_events(content, wanted):
    runs, passes, actions = [], [], collections.Counter()
    for line in content.splitlines():
        if not line:
            continue
        row = json.loads(line)
        action = row.get('Action')
        actions[action] += 1
        require(action not in ('fail', 'skip'), 'no failed/skipped original event')
        if 'Test' in row:
            key = (row['Package'], row['Test'])
            require(key in wanted, 'only exact declared original test')
            if action == 'run':
                runs.append(key)
            if action == 'pass':
                passes.append(key)
    require(set(runs) == set(passes) == wanted and len(runs) == len(passes) == len(wanted), 'one run/pass each')
    return {'runs': len(runs), 'passes': len(passes), 'failures': 0, 'skips': 0,
            'methods': [{'package': p, 'name': n} for p, n in sorted(wanted)],
            'rawEventCounts': dict(actions), 'raw': ident(content)}

def normal(row):
    return (row['exitCode'] == 0 and row['processGroupAbsent'] is True and
            row['forcedCleanup'] is False and row['signals'] == row['cleanupErrors'] == [] and
            row.get('stopReason') is None and row['unreapedLeaderDuringGroupCleanup'] is True)

def main():
    require(not OUT.exists(), 'new owned static qualification only')
    OUT.mkdir()
    compare = primary('parent-to-donor.original.json')
    current = primary('current-to-donor.original.json')
    require(compare['ahead_by'] == 1 and compare['behind_by'] == 0 and compare['base_commit']['sha'] == PARENT, 'direct donor parent')
    require(current['ahead_by'] == 1 and current['behind_by'] == 304 and current['merge_base_commit']['sha'] == PARENT, 'current exact ancestry')
    files = {r['filename']: r for r in compare['files']}
    require(len(files) == 61 and all(r['status'] == 'added' for r in files.values()), 'exact61 additive paths')
    require({r['filename']: r['sha'] for r in current['files']} == {p:r['sha'] for p,r in files.items()}, 'same complete current merge delta')
    root_metadata = primary('donor-root-tree.original.json')
    require(root_metadata['sha'] == DONOR_TREE, 'exact donor tree')
    identities, subtree_proofs = {}, []
    for prefix, name in [(T, 'tree-Tools-bookmark.original.json'), (D, 'tree-docs-bookmark.original.json')]:
        meta = primary(name)
        require(meta['truncated'] is False, 'full finite subtree')
        leaves = {}
        for row in meta['tree']:
            if row['type'] != 'blob':
                continue
            path = prefix + row['path']
            require(row['mode'] == '100644' and path in files and row['sha'] == files[path]['sha'], 'exact original mode/blob')
            content = raw(path)
            identity = ident(content, row['mode'])
            require(identity['gitBlob'] == row['sha'], 'primary raw Git blob ' + path)
            identities[path] = identity
            leaves[row['path']] = (row['mode'], row['sha'])
        require(tree(leaves) == meta['sha'], 'reconstructed original subtree')
        subtree_proofs.append({'prefix':prefix, 'tree':meta['sha'], 'files':len(leaves), 'exact':True})
    require(set(identities) == set(files), 'complete61 primary closure')
    decoded = data(ROOT/'primary-decoded-identities.json')
    require(sum(r['bytes'] for r in identities.values()) == 1804377 == decoded['totalBytes'], 'whole61 byte count')
    for path, row in identities.items():
        require(all(decoded['files'][path][k] == row[k] for k in ('bytes','sha256','gitBlob')), 'initial primary identities preserved')
    advertised = json.loads(raw(D+'FILES.json'))
    require(set(advertised['files']) == set(identities)-{D+'FILES.json'}, 'original FILES excludes only self')
    for path, row in advertised['files'].items():
        require(row == {k:identities[path][k] for k in ('bytes','sha256')}, 'all60 published FILES rows')
    baseline_raw = (WORK/'wave3-bookmark-mounted-result-source-integration-prepared/prepared1/expected-final-complete-leaves.stdout').read_bytes()
    baseline = parse_leaves(baseline_raw)
    require(tree(baseline) == BASE_TREE, 'full actual5a45 tree')
    pub = data(WORK/'shared62-native26-compatibility-source/publication1/source-inputs.json')
    require(len(pub['files']) == 60 and pub['actualBase'] == BASE and pub['actualBaseTree'] == BASE_TREE, 'frozen compatibility baseline')
    require(not set(files)&set(baseline) and not set(files)&set(pub['files']), 'all61 absent current and disjoint60')
    compatibility = dict(baseline)
    for path, row in pub['files'].items():
        content = base64.b64decode(row['base64'])
        require(ident(content, row['after']['gitMode']) == row['after'], 'frozen60 after bytes')
        if row.get('before') is not None:
            require(baseline[path] == (row['before']['gitMode'],row['before']['gitBlob']), 'frozen60 current preimage')
        else:
            require(path not in baseline, 'frozen evidence addition absent')
        compatibility[path] = (row['after']['gitMode'],row['after']['gitBlob'])
    require(tree(compatibility) == '3ba2c3108503e39b661704e11db7694cd5cd5906', 'frozen3ba2 exact')
    only_c13, combined = dict(baseline), dict(compatibility)
    for path, row in identities.items():
        only_c13[path] = combined[path] = (row['gitMode'],row['gitBlob'])

    formatted = json.loads(raw(D+'source/formatted-source.json'))
    old = json.loads(raw(D+'source/native1616-source.json'))['files']
    composed = json.loads(raw(D+'source/composed1625-source.json'))['files']
    compiled = json.loads(raw(D+'source/compiled1626-inputs.json'))
    require(len(old)==1616 and len(composed)==1625 and len(compiled['files'])==1626 and len(formatted['files'])==17, 'native source counts')
    native_rows, inverses, new = {}, {}, {}
    derived = dict(old)
    for name, row in formatted['files'].items():
        public = overlay_path(name)
        content = raw(public)
        identity = ident(content)
        require({k:identity[k] for k in ('bytes','sha256')} == {k:row[k] for k in ('bytes','sha256')}, 'native overlay raw')
        before = old.get(name)
        require(row['beforeSHA256'] == (before['sha256'] if before else None), 'native original before SHA')
        derived[name] = {k:identity[k] for k in ('bytes','sha256')}
        native_rows[name] = {'publicPath': public, 'role':row['role'], 'before':before, 'after':identity}
        if before:
            relative = public.removeprefix(T+'overlay/')
            original = (ROOT/'original-native8'/relative).read_bytes()
            require({k:ident(original)[k] for k in ('bytes','sha256')} == before, 'actual local immutable native preimage')
            inverses[name] = inverse(original, content)
        else:
            new[name] = identity
    require(len(inverses)==8 and len(new)==9 and derived==composed, '8M9A whole native composition')
    require(sum(r['role']=='production' for r in native_rows.values())==13, '13 native production files')
    config = {'bytes':1137,'sha256':'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'}
    require(dict(composed, **{'staging.yml':config}) == compiled['files'] and set(compiled['files']) == set(compiled['modes']), 'compiled1626 exact public config addition')
    require(collections.Counter(compiled['modes'].values()) == {384:1618,448:8}, 'exact compiled source modes')

    control_pairs = [
        ('qualification/original/qualify_bookmark_native.py','qualification/complete_bookmark_native.py'),
        ('bodyless/owned_swift_commands_original.py','bodyless/owned_native_commands.py'),
        ('bodyless/original/run_bodyless_bookmark.py','bodyless/before-policy-schema/run_bodyless_bookmark.py'),
        ('bodyless/before-policy-schema/run_bodyless_bookmark.py','bodyless/run_bodyless_bookmark.py')]
    controller_inverses = {b:{'originalPath':T+a, **inverse(raw(T+a),raw(T+b))} for a,b in control_pairs}
    timer_original = declaration(raw(T+'bodyless/absolute_http_source_original.py'), 'absolute_http_deadline')
    timer_after = declaration(raw(T+'bodyless/native_boundary_support.py'), 'absolute_http_deadline')
    require(timer_original==timer_after and len(timer_after)==1745 and hashlib.sha256(timer_after).hexdigest()=='b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81', 'original full HTTP deadline retained')
    require(raw(T+'qualification/owned_swift_commands.py') == raw(T+'bodyless/owned_swift_commands_original.py'), 'shared original owner exact')
    literals = selected_ast_literals(raw(T+'publication/validate_public_evidence.py'), ('FIXED','CONTROLLERS'))
    pinned = {}
    for table, prefix in [('FIXED',D),('CONTROLLERS',T)]:
        for path, digest in literals[table].items():
            p = prefix + path
            require(identities[p]['sha256']==digest, 'declared original source/receipt pin '+p)
            pinned[p] = identities[p]

    expected = {'sdk-eight':set(), 'server-five':set()}
    for name, names in formatted['tests'].items():
        source = raw(overlay_path(name)).decode()
        declarations = re.findall(r'^func (Test\w+)\(t \*testing\.T\)', source, re.M)
        require(set(declarations)==set(names) and len(declarations)==len(names), 'full original test declarations')
        sdk = name.startswith('.runtime-artifacts/sdk-source/')
        rel = name.removeprefix('.runtime-artifacts/sdk-source/') if sdk else name
        package = ('github.com/anyproto/any-sync-sdk/' if sdk else 'github.com/anyproto/any/') + str(Path(rel).parent)
        expected['sdk-eight' if sdk else 'server-five'].update((package,n) for n in names)
    parsed = {name:go_events(raw(D+'logs/'+file),expected[name]) for name,file in [('sdk-eight','retained-sdk-eight.log'),('server-five','new-server-five.log')]}
    failed = json.loads(raw(D+'receipts/original-qualification-fail.json'))
    success = json.loads(raw(D+'receipts/completion13-pass.json'))
    require(failed['status']=='FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and len(failed['processes'])==3 and all(normal(r) for r in failed['processes'][:2]), 'preserved actual initial two normal groups')
    interrupted = failed['processes'][2]
    require(interrupted['exitCode']==-15 and interrupted['signals']==[15] and interrupted['forcedCleanup'] is True and interrupted['processGroupAbsent'] is True and interrupted['cleanupErrors']==[], 'exact failed third group')
    require(failed['errors']==[{'type':'RuntimeError','message':'RuntimeError: measured shared cache incremental cap'}], 'initial failure cause exact')
    require(success['status']=='PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and len(success['processes'])==4 and all(normal(r) for r in success['processes']), 'four actual new normal groups')
    require(success['errors']==success['completionErrors']==[] and success['allOwnedGroupsPositivelyAbsent'] is True and failed['allOwnedGroupsPositivelyAbsent'] is True, 'actual retained/new closure')
    for name, result in parsed.items():
        projection = {k:v for k,v in result.items() if k not in ('raw','rawEventCounts')}
        require(success[name]==projection, 'raw Go events match completion')
        if name=='sdk-eight':
            require(failed[name]==projection, 'same8 retained event proof')
    for receipt in (failed,success):
        require(receipt['sourceDraftSHA256']==identities[D+'source/formatted-source.json']['sha256'] and receipt['sourceManifestSHA256']==identities[D+'source/composed1625-source.json']['sha256'] and receipt['compiledSourceInputSHA256']==identities[D+'source/compiled1626-inputs.json']['sha256'], 'receipt whole source identity')
    require(success['retainedActualMethodCount']==8 and success['newActualMethodCount']==5 and success['priorTestMethodsReexecuted']==0 and success['nativeProductBuilds']==1, '8 retained +5new, no rerun, one product')
    labels = ('current-native-compiler-environment.log','new-server-five.log','native-build.log','native-metadata.log')
    for row,name in zip(success['processes'],labels):
        require(row['logSHA256']==identities[D+'logs/'+name]['sha256'], 'new group original log SHA')
    for row,name in zip(failed['processes'],('retained-go-environment.log','retained-sdk-eight.log','original-failed-server-compile.log')):
        require(row['logSHA256']==identities[D+'logs/'+name]['sha256'], 'old group original log SHA')
    require(success['retainedQualification']['qualifiedProcesses']==failed['processes'][:2] and success['retainedQualification']['failedCompileProcess']==failed['processes'][2], 'original rows retained literally')
    require(success['retainedCompilerEvidenceScope']['historicalNativeCompilerExecutablesObserved'] is False and success['retainedCompilerEvidenceScope']['historicalPATHObserved'] is False, 'historical compiler observation limitation')
    metadata = raw(D+'logs/native-metadata.log').decode()
    require('github.com/anyproto/any/cmd/any' in metadata and 'github.com/anyproto/anytype-heart' not in metadata and '.runtime-artifacts/sdk-source' in metadata, 'standalone native graph, not Heart')

    body_failure = json.loads(raw(D+'receipts/bodyless-attempt1-fail.json'))
    body = json.loads(raw(D+'receipts/bodyless-attempt2-pass.json'))
    require(body_failure['status']=='FAIL_BODYLESS_BOOKMARK_PRESERVED' and body_failure['commands']==body_failure['requests']==body_failure['mutations']==[] and body_failure['errors']==[{'type':'KeyError','message':"'actual'"}], 'first no-child bodyless failure kept')
    require(body['status']=='PASS_ONE_BODYLESS_BOOKMARK_ACTUAL_CRASH_AND_OFFLINE_REOPEN' and body['errors']==body['completionErrors']==[], 'actual bodyless pass')
    require(len(body['commands'])==3 and [r['exitCode'] for r in body['commands']]==[0,-9,0] and all(r['processGroupAbsent'] is True and r['forcedCleanup'] is False and r['cleanupErrors']==r['signals']==[] for r in body['commands']), 'three exact bodyless process closures')
    require(body['commands'][1]['intentionalCrashGateValidated'] is True and body['commands'][1]['intentionalCrashSignal']==9, 'intentional crash gate')
    require(len(body['phases'])==2 and body['phases'][0]['actualPID'] != body['phases'][1]['actualPID'] and body['phases'][0]['observation']==body['phases'][1]['observation'], 'same observed result fresh cold PID')
    require(body['phases'][0]['observation']['editorRows']=={'records':[],'total':0,'hasNext':False} and body['phases'][0]['observation']['markdown']['content']=='', 'real bodyless result')
    require(body['phases'][0]['observation']['sourceURL']=={'bytes':56,'sha256':'bd9bc3cf70057b67f6fc047326182d5eabef82b1ec6dd2e86dd766017fd93b46'}, 'decomposed source URL exact')
    require(len(body['requests'])==37 and len(body['mutations'])==7 and [r['name'] for r in body['mutations']]==['space','type','editor-part','property-owner','url-property','layout','bookmark'], '37 HTTP records/7orderedmutations')
    for mutation in body['mutations']:
        request=body['requests'][mutation['requestIndex']]
        require(mutation['state']=='validated-acknowledgement' and all(request[k]==mutation[k] for k in ('method','path','status','requestBody','rawResponse')), 'retained exact ACK/request relation')
    cold=[r for r in body['requests'] if r['phase']=='native-cold-offline']
    require(len(cold)==13 and all(r['readOnlyOperation'] is True for r in cold), 'cold13 read-only requests')
    require(body['qualifiedProducer']['sha256']==identities[D+'receipts/completion13-pass.json']['sha256'] and body['qualifiedProducer']['nativeBinary']==success['nativeBinary'], 'bodyless exact compiled product chain')
    require(body['accountInitializations']==body['nativeBodylessCreates']==1 and body['controllerMutationRetries']==body['compilerInvocations']==body['priorTestMethodsReexecuted']==0, 'one new account/Bookmark, no retry or build/test replay')
    require(body['syntheticDefinitionOnly'] is True and body['originalMigrationTypesStillUnqualified'] is True and all(body[k] is False for k in ('sourceAdmissionPromoted','wholeMigrationComplete','originalBuiltinTypeMigrationQualified','originalPlaintextHistoryReconstructed')), 'no original Type/whole migration promotion')
    require(body['controller']=={k:identities[T+'bodyless/run_bodyless_bookmark.py'][k] for k in ('bytes','sha256')}, 'executed bodyless controller identity')

    runtime_path=WORK/'wave1-c13-runtime18-current-intake/runtime18.receipt.original.json'
    runtime_raw=runtime_path.read_bytes(); runtime=json.loads(runtime_raw)
    require(ident(runtime_raw)['sha256']=='f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2', 'original separate Runtime18 receipt')
    runtime_serialized=json.dumps(runtime)
    for name in ('source/composed1625-source.json','source/compiled1626-inputs.json','receipts/completion13-pass.json','receipts/original-qualification-fail.json'):
        require(identities[D+name]['sha256'] in runtime_serialized, 'separate Runtime18 retained C13 reference')
    require(success['nativeBinary']['sha256'] in runtime_serialized and 'NOT_RUN_SEPARATE_READ_ONLY_FOUR_DECISIONS_REQUIRED' in runtime_serialized, 'separate runtime retains C13 native, HTTP4 pending')

    inverse_identity=put('native-full-inverses.json',{'schema':'pinkha-c13-eight-original-native-full-inverses/v1','files':inverses,'added9':new,'operations':sum(len(r['operations']) for r in inverses.values()),'candidateImports':0,'testsExecuted':0})
    controller_inverse_identity=put('controller-lineage-full-inverses.json',{'schema':'pinkha-c13-historical-controller-lineage-inverses/v1','files':controller_inverses,'wholeOriginalHTTPDeadline':ident(timer_after),'candidateImports':0,'testsExecuted':0})
    rows={path:{'status':'added','before':None,'after':identity,'base64':base64.b64encode(raw(path)).decode()} for path,identity in sorted(identities.items())}
    source_identity=put('source-inputs.json',{'schema':'pinkha-w1-c13-e833-source-inputs/v1','actualBase':BASE,'actualBaseTree':BASE_TREE,'donor':DONOR,'donorTree':DONOR_TREE,'donorParent':PARENT,'mergeBase':PARENT,'files':rows,'sourcePathCount':61,'statusCounts':{'added':61},'candidateImports':0,'testsExecuted':0,'hostActions':0,'bindingReady':False,'runtimeActivation':False})
    proof={'schema':'pinkha-w1-c13-independent-primary-byte-evidence-join/v1','status':'PASS_SOURCE_AND_ORIGINAL_EVIDENCE_REVIEW_ONLY',
        'actualBase':BASE,'actualBaseTree':BASE_TREE,'donor':DONOR,'donorTree':DONOR_TREE,'donorParent':PARENT,
        'primary61':{'files':identities,'totalBytes':1804377,'gitBlobsVerified':61,'mode':'100644','subtrees':subtree_proofs,'allAbsentAtBase':True},
        'composition':{'baseLeaves':len(baseline),'c13OnlyLeaves':len(only_c13),'c13OnlyTree':tree(only_c13),'compatibility60Tree':tree(compatibility),'combined121Leaves':len(combined),'combined121TreeWithoutRootIntake':tree(combined),'pathOverlap':[]},
        'native':{'baseFiles':1616,'overlayFiles':17,'modified':8,'added':9,'production':13,'testFiles':4,'composedFiles':1625,'compiledFiles':1626,'modes':dict(collections.Counter(compiled['modes'].values())),'rows':native_rows,'fullInverse':inverse_identity},
        'historicalControllerLineage':controller_inverse_identity,'sourcePinnedOriginals':pinned,
        'componentEvidence':{'rawEvents':parsed,'retainedFailure':identities[D+'receipts/original-qualification-fail.json'],'completion':identities[D+'receipts/completion13-pass.json'],'originalFailedServerCompileExit':-15,'retainedNormalGroups':2,'newNormalGroups':4,'priorMethodsReexecuted':0,'nativeBinary':success['nativeBinary'],'historicalCCompilerExecutablesAndPATHObserved':False},
        'bodylessEvidence':{'priorFailure':identities[D+'receipts/bodyless-attempt1-fail.json'],'actualPass':identities[D+'receipts/bodyless-attempt2-pass.json'],'processExits':[0,-9,0],'groupsPositivelyClosed':3,'requests':37,'coldReadOnlyRequests':13,'setupMutations':6,'bookmarkCreates':1,'mutationRetries':0,'freshAccountInitializations':1,'sameWarmColdObservation':True,'syntheticDefinitionOnly':True,'originalTypeMigrationQualified':False,'originalPrivateResponseBytesIndependentlyFetched':False},
        'separateRuntime18':{'receipt':ident(runtime_raw),'retainedC13SourceAndReceiptJoin':True,'newSourceManifestSHA256':'12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9','newCompiledSourceSHA256':'3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4','newBinarySHA256':'84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974','newSourceFiles':1638,'newSDKFiles':750,'newChangedFiles':15,'publishedByE833':False,'fullNewSourceManifestOrBytesReadByThisReview':False,'rawLogQualificationOwner':'/root/apple_release','HTTP4':'NOT_RUN_SEPARATE_READ_ONLY_FOUR_DECISIONS_REQUIRED','AppleAcceptance':False},
        'sourceInputs':source_identity,'candidateImports':0,'testsExecuted':0,'hostActions':0,'newRuntimeAcceptance':False}
    proof_identity=put('independent-byte-proof.json',proof)
    put('static-run-result.json',{'status':'PASS_LOCAL_BYTES_JSON_AST_MERKLE_ONLY','proof':proof_identity,'sourceInputs':source_identity,'candidateImports':0,'testsExecuted':0,'hostActions':0})
    print(json.dumps({'status':'PASS_LOCAL_BYTES_JSON_AST_MERKLE_ONLY','files':61,'bytes':1804377,'native8InverseOperations':sum(len(r['operations']) for r in inverses.values()),'sourceInputs':source_identity,'proof':proof_identity,'combined121Tree':tree(combined)},sort_keys=True))

if __name__ == '__main__':
    main()

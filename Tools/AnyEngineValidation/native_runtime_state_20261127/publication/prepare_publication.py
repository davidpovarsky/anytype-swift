#!/usr/bin/env python3
"""Prepare the finite runtime15/actual18 packet locally; never publish or run it."""
import ast
import base64
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
N = HERE.parents[1]
WORKSPACE = N.parent
SOURCE = HERE.parent
CODE = 'Tools/AnyEngineValidation/native_runtime_state_20261127/'
DOC = 'docs/validation/20261127-native-runtime-state/'
BASE = '02bfc5cb35e7fd3a32ea4d70cb8669ff4c858b93'
TREE = 'a4ed2be80fe26acc102edabbfa12dc3150f0867b'
BRANCH = 'codex/chatgpt-wave15-network-final-authority-20261127'
WT = '/mnt/development/projects/worktrees/anytype-network-final-authority-publish-20261127'
OLD = N/'positive_full_tier_offload/publication/publish_positive_offload.py'
OLD_SHA = '7d458a1240d9821728fcb88bdfcc6ac25e1ee8b4c860b6d77eebd2e43a0bcaae'
PRIOR_RECEIPT = '/mnt/development/projects/evidence/pinkha-w1-positive-offload-publication-20261127/attempt1/result.json'
PRIOR_SHA = 'e91b2eaa513cc1c1e6c5c311c36f74dd6b63e4556ff4ee3223b271aa22e39f37'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main():
    original = OLD.read_bytes()
    assert identity(original)['sha256'] == OLD_SHA
    text = original.decode()

    def replace(before, after):
        nonlocal text
        assert text.count(before) == 1, before
        text = text.replace(before, after)

    replace('"""Publish only exact positive-Offload controls and actual public evidence.\n\nExtends the same already owned, clean network branch at exact972f. No native,\ncompiler, account, prior test replay, existing-file replacement or force push.\n"""',
        '"""Publish exact runtime15 source, actual18 and explicitly unrun HTTP4 controls.\n\nExtends the same already owned, clean network branch at exact02bfc. No native,\ncompiler, account, prior test replay, existing-file replacement or force push.\n"""')
    for name in ('PLAN_SHA', 'LOCAL_SHA', 'VALIDATOR_SHA'):
        line = next(line for line in text.splitlines() if line.startswith(name+' = '))
        replace(line, name+" = '__"+name+"__'")
    replace('REMOTE_COUNT = 11', 'REMOTE_COUNT = 43')
    replace('LOCAL_COUNT = 6', 'LOCAL_COUNT = 11')
    replace("BASE = '972f6c2eaed18fdcfa4e5f885d519b3fb18a9aa7'", "BASE = '"+BASE+"'")
    replace("BASE_TREE = 'de8a7074500d28918af62dcbbb2f5c70b82b0580'", "BASE_TREE = '"+TREE+"'")
    replace("PRIOR_PUBLICATION = Path('/mnt/development/projects/evidence/pinkha-w1-final-authority-publication-20261127/attempt2/result.json')",
        "PRIOR_PUBLICATION = Path('"+PRIOR_RECEIPT+"')")
    replace("PRIOR_PUBLICATION_SHA = 'f70e4ea6c21c28b0242471e183c4345cc4babe0fcf172bc43f6b17dda5f0c208'", "PRIOR_PUBLICATION_SHA = '"+PRIOR_SHA+"'")
    replace("OUT = Path('/mnt/development/projects/evidence/pinkha-w1-positive-offload-publication-20261127/attempt1')",
        "OUT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-publication-20261127/attempt1')")
    replace("CODE = 'Tools/AnyEngineValidation/native_file_positive_offload/'", "CODE = '"+CODE+"'")
    replace("DOC = 'docs/validation/20261127-native-file-positive-offload/'", "DOC = '"+DOC+"'")
    replace("'protocol': 'pinkha-positive-offload-evidence-publication-v1'", "'protocol': 'pinkha-runtime-state-source-evidence-publication-v1'")
    replace("plan['protocol']=='pinkha-positive-offload-publication-plan-v1'", "plan['protocol']=='pinkha-runtime-state-publication-plan-v1'")
    replace("prior['status']=='PASS_NORMAL_PUBLICATION_OF_FINAL_FILES_AUTHORITY_WITH_LOSSLESS_HISTORICAL_ARTIFACTS'",
        "prior['status']=='PASS_NORMAL_PUBLICATION_OF_POSITIVE_FULL_TIER_OFFLOAD_EVIDENCE'")
    replace("prior['publicFileCount']==52", "prior['publicFileCount']==19")
    replace("len(prior['commands'])==29", "len(prior['commands'])==28")
    replace("spec_from_file_location('positive_offload_public_evidence',module_path)",
        "spec_from_file_location('runtime_state_public_evidence',module_path)")
    replace("'protocol':'pinkha-positive-offload-public-file-set-v1'", "'protocol':'pinkha-runtime-state-public-file-set-v1'")
    replace("'existing complete index matches exact972f; no initialization/reset'", "'existing complete index matches exact02bfc; no initialization/reset'")
    replace("'Qualify backed full-tier Offload and cloud cache recovery'", "'Publish current-authority runtime observations and actual18 proof'")
    replace("report['status']='PASS_NORMAL_PUBLICATION_OF_POSITIVE_FULL_TIER_OFFLOAD_EVIDENCE'",
        "report['status']='PASS_NORMAL_PUBLICATION_OF_RUNTIME_STATE15_ACTUAL18_HTTP4_PENDING'")
    # Preserve the already-qualified Git/proof operations while placing the
    # first owned filesystem transition inside the terminal-receipt boundary.
    replace("""    OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    physical(OUT.parent)
    OUT.mkdir(mode=0o700, exist_ok=False)
    # Reserving result before try/finally prevents a repeated invocation from
    # replacing any earlier evidence. All subsequent saves stay in this root.
    with (OUT/'result.json').open('xb') as stream:
        stream.write(b'{}\\n'); stream.flush(); os.fsync(stream.fileno())
    fsync_directory(OUT)
""", "")
    replace("    owned_worktree = True\n", "    owned_worktree = True\n    owned_output = False\n    owned_parent = False\n")
    replace("        require(path.is_relative_to(OUT), 'owned evidence destination')",
        "        require(owned_output and path.is_relative_to(OUT), 'owned evidence destination')")
    replace("        size = allocated(OUT)\n", "        size = allocated(OUT) if owned_output else 0\n")
    replace("        report['initialFreeBytes'] = guard(True)\n", """        report['initialFreeBytes'] = guard(True)
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            physical(OUT.parent.parent)
            require(OUT.parent.parent.is_dir(), 'existing public evidence ancestor')
            if not os.path.lexists(OUT.parent):
                OUT.parent.mkdir(mode=0o700); owned_parent = True
                fsync_directory(OUT.parent); fsync_directory(OUT.parent.parent)
            physical(OUT.parent)
            require(OUT.parent.is_dir(), 'physical publication parent')
            OUT.mkdir(mode=0o700, exist_ok=False); owned_output = True
            OUT.chmod(0o700)
            # The fresh root is owned before reservation. No repeated invocation
            # may enter this boundary or replace an earlier receipt.
            with (OUT/'result.json').open('xb') as stream:
                stream.write(b'{}\\n'); stream.flush(); os.fsync(stream.fileno())
            fsync_directory(OUT); fsync_directory(OUT.parent)
            report['ownedOutputCreated'] = True
            report['ownedParentCreated'] = owned_parent
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
""")
    replace("""        checkpoint()
        print(json.dumps({'status':report['status'],'result':str(OUT/'result.json'),
            'sha256':digest(OUT/'result.json'),'commit':report.get('commit'),
            'allStartedOwnedGroupsPositivelyAbsent':report['allStartedOwnedGroupsPositivelyAbsent'],
            'errors':report['errors'],'completionErrors':report['completionErrors']}))
""", """        report['ownedOutputCreated'] = owned_output
        report['ownedParentCreated'] = owned_parent
        retained_sha = None
        try:
            if owned_output:
                checkpoint()
                retained_sha = digest(OUT/'result.json')
        except BaseException as error:
            report['status'] = 'FAIL_PRESERVED_WITHOUT_RESET_OR_RETRY'
            report['completionErrors'].append({'phase':'receipt-retention',
                'type':type(error).__name__,'message':str(error)})
        summary = {'status':report['status'],'result':str(OUT/'result.json') if owned_output else None,
            'sha256':retained_sha,'commit':report.get('commit'),
            'allStartedOwnedGroupsPositivelyAbsent':report['allStartedOwnedGroupsPositivelyAbsent'],
            'errors':report['errors'],'completionErrors':report['completionErrors']}
        if retained_sha is None:
            # The original tool stdout retains an explicit FAIL even if the
            # filesystem cannot save the newly owned terminal receipt.
            raw = (json.dumps(report,sort_keys=True,separators=(',',':'))+'\\n').encode()
            summary['failedReceiptFallback'] = dict(identity(raw),encoding='base64',
                data=base64.b64encode(raw).decode())
        print(json.dumps(summary))
""")
    ast.parse(text)
    template = text.encode()
    save(HERE/'publish_runtime_state.template.py', template)
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(True), text.splitlines(True),
        'actual-7d458/publish_positive_offload.py', 'runtime-state/publish_runtime_state.template.py'))
    save(HERE/'publisher.review.patch', patch.encode())
    original_functions = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(original).body if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(template).body if isinstance(node, ast.FunctionDef)}
    assert set(original_functions) == set(new_functions)
    assert all(original_functions[name] == new_functions[name] for name in original_functions if name != 'main')

    remote_source = '/mnt/development/projects/evidence/pinkha-n-runtime-state-source-20261127-attempt1'
    remote_http = '/mnt/development/projects/evidence/pinkha-n-runtime-state-http-source-20261127-attempt1'
    runtime = '/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7'
    c13 = '/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127'
    c13_local = WORKSPACE/'migration-relay/bookmark-create-native'
    draft = json.loads((SOURCE/'SOURCE_DRAFT2.json').read_bytes())
    remote_rows = [(CODE+'overlay/'+name, remote_source+'/overlay/'+name, SOURCE/'overlay'/name) for name in sorted(draft['files'])]
    remote_rows += [(CODE+name, remote_source+'/'+name, SOURCE/name) for name in (
        'SOURCE_DRAFT2.json', 'WIRE_CONTRACT.json', 'runtime-state.draft2.patch',
        'qualification/qualify_runtime_state.py', 'qualification/QUALIFICATION_PLAN.json',
        'qualification/COMPOSED1638.json', 'qualification/owned_swift_commands.py')]
    remote_rows += [
        (DOC+'receipts/format15.json', '/mnt/development/projects/evidence/pinkha-n-runtime-state-gofmt-20261127-attempt1/result.json', SOURCE/'actual-format15-result.json'),
        (DOC+'receipts/runtime-source-install.json', '/mnt/development/projects/evidence/pinkha-n-runtime-state-source-install-20261127-attempt1/result.json', SOURCE/'qualification/installation/actual-attempt1-result.json'),
        (DOC+'receipts/runtime18.json', runtime+'/result.json', SOURCE/'qualification/actual-attempt7/result.json'),
        (DOC+'maps/runtime-compiled-source-inputs.json', runtime+'/compiled-source-inputs.json', SOURCE/'qualification/actual-attempt7/compiled-source-inputs.json'),
        (DOC+'maps/runtime-source-manifest.json', runtime+'/source-manifest.json', SOURCE/'qualification/actual-attempt7/source-manifest.json'),
    ]
    for phase in ('toolchain', 'sdk-units', 'server-units', 'fresh-sdk', 'native-build', 'native-metadata'):
        remote_rows.append((DOC+'logs/'+phase+'.log', runtime+'/'+phase+'/original.log', SOURCE/'qualification/actual-attempt7'/phase/'original.log'))
    for name in ('verify_runtime_state_http.py', 'runtime_product_admission.py', 'runtime_wire_validation.py', 'owned_swift_commands.py'):
        remote_rows.append((CODE+'http/'+name, remote_http+'/'+name, SOURCE/'http'/name))
    remote_rows += [
        (DOC+'receipts/http4-source-install-only.json', '/mnt/development/projects/evidence/pinkha-n-runtime-state-http-source-install-20261127-attempt1/result.json', SOURCE/'http/installation/actual-attempt1-result.json'),
        (DOC+'receipts/c13-original-fail.json', c13+'/qualification-attempt1/result.json', c13_local/'actual-qualification-attempt1/result.json'),
        (DOC+'receipts/c13-completion.json', c13+'/qualification-completion-attempt1/result.json', c13_local/'actual-qualification-completion-attempt1/result.json'),
        (DOC+'maps/c13-compiled-source-inputs.json', c13+'/qualification-completion-attempt1/compiled-source-inputs.json', c13_local/'actual-qualification-completion-attempt1/compiled-source-inputs.json'),
        (DOC+'maps/c13-source-manifest.json', c13+'/qualification-completion-attempt1/source-manifest.json', c13_local/'actual-qualification-completion-attempt1/source-manifest.json'),
        (DOC+'logs/c13-native-metadata.log', c13+'/qualification-completion-attempt1/native-metadata/original.log', c13_local/'actual-qualification-completion-attempt1/native-metadata/original.log'),
    ]
    local_rows = [
        (DOC+'README.md', HERE/'README.md'),
        (CODE+'SOURCE_BASE.json', SOURCE/'SOURCE_BASE.json'),
        (CODE+'PROPOSAL.md', SOURCE/'PROPOSAL.md'),
        (CODE+'FORMATTING_PROVENANCE.json', SOURCE/'FORMATTING_PROVENANCE.json'),
        (CODE+'http/HTTP_SOURCE_PLAN.json', SOURCE/'http/HTTP_SOURCE_PLAN.json'),
        (CODE+'http/README.md', SOURCE/'http/README.md'),
        (CODE+'http/SOURCE_DERIVATION.json', SOURCE/'http/SOURCE_DERIVATION.json'),
        (CODE+'http/dispatch_runtime_http4.py', SOURCE/'http/dispatch_runtime_http4.py'),
        (CODE+'publication/validate_public_evidence.py', HERE/'validate_public_evidence.py'),
        (CODE+'publication/publish_runtime_state.template.py', HERE/'publish_runtime_state.template.py'),
        (CODE+'publication/prepare_publication.py', Path(__file__)),
    ]
    assert len(remote_rows) == 43 and len(local_rows) == 11
    content, remote, local, payload = {}, [], [], {}
    for name, source, path in remote_rows:
        raw = path.read_bytes(); assert name not in content
        content[name] = raw
        remote.append(dict(destination=name, source=source, maximumBytes=2*1024**2, **identity(raw)))
    for name, path in local_rows:
        raw = path.read_bytes(); assert name not in content
        content[name] = raw
        local.append(dict(destination=name, **identity(raw)))
        payload[name] = dict(base64=base64.b64encode(raw).decode(), **identity(raw))
    spec = importlib.util.spec_from_file_location('runtime_public_validator', HERE/'validate_public_evidence.py')
    validator = importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)
    checked = validator.validate(content, CODE, DOC)
    plan = {'protocol': 'pinkha-runtime-state-publication-plan-v1', 'expectedHead': BASE, 'expectedTree': TREE,
        'branch': BRANCH, 'worktree': WT, 'remotePublicCopies': remote, 'localPublicFiles': local,
        'priorPublicationReceipt': {'path': PRIOR_RECEIPT, 'sha256': PRIOR_SHA},
        'existingSourceFilesReplaced': 0, 'newAccountOrRuntimeActions': 0,
        'actual18ReceiptSHA256': 'f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2',
        'http4ExecutionStatus': 'NOT_RUN', 'preparedStatus': 'SOURCE_ONLY_NOT_PUBLISHED'}
    plan_raw, payload_raw = encoded(plan), encoded(payload)
    save(HERE/'PUBLICATION_PLAN.json', plan_raw)
    save(HERE/'LOCAL_PUBLIC_FILES.json', payload_raw)
    actual = template
    for marker, value in ((b'__PLAN_SHA__', identity(plan_raw)['sha256']),
            (b'__LOCAL_SHA__', identity(payload_raw)['sha256']),
            (b'__VALIDATOR_SHA__', identity((HERE/'validate_public_evidence.py').read_bytes())['sha256'])):
        assert actual.count(marker) == 1
        actual = actual.replace(marker, value.encode())
    ast.parse(actual)
    save(HERE/'publish_runtime_state.py', actual)
    content[DOC+'publication-inputs.json'] = plan_raw
    content[DOC+'FILES.json'] = encoded({'protocol': 'pinkha-runtime-state-public-file-set-v1', 'baseCommit': BASE,
        'inputPlanSHA256': identity(plan_raw)['sha256'], 'localPublicPayloadSHA256': identity(payload_raw)['sha256'],
        'nativeExecutableCopiedToGit': False, 'privateAccountFiles': 0,
        'files': {name: identity(raw) for name, raw in sorted(content.items())}})
    for name, raw in content.items():
        save(HERE/'candidate'/name, raw)
        if name.endswith('.py'):
            ast.parse(raw)
    preparation = {'status': 'PREPARED_SOURCE_ONLY_NOT_PUBLISHED', 'publicFiles': len(content),
        'publicBytes': sum(map(len, content.values())), 'plan': identity(plan_raw), 'localPayload': identity(payload_raw),
        'publisher': identity(actual), 'template': identity(template), 'validator': identity((HERE/'validate_public_evidence.py').read_bytes()),
        'reviewPatch': identity(patch.encode()), 'actualPriorPublisher': {'path': str(OLD), 'sha256': OLD_SHA},
        'nonMainFunctionASTIdentical': True, 'pureLocalEvidenceValidation': checked,
        'newCompilerTestNativeAccountActions': 0, 'http4ActualRuntimeStatus': 'NOT_RUN'}
    save(HERE/'PREPARATION.json', encoded(preparation))
    print(json.dumps({key: value for key, value in preparation.items() if key != 'pureLocalEvidenceValidation'}, sort_keys=True))


if __name__ == '__main__':
    main()

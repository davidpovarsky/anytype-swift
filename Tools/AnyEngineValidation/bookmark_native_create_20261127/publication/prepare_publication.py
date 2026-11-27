#!/usr/bin/env python3
"""Prepare exact C13/bodyless public source and evidence locally, without Git."""
import ast
import base64
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = HERE.parent
WORKSPACE = HERE.parents[2]
N = WORKSPACE/'network_files'
CODE = 'Tools/AnyEngineValidation/bookmark_native_create_20261127/'
DOC = 'docs/validation/20261127-bookmark-native-create/'
BASE = '6b91db33d325f22b62d829051db203121c6cdb8e'
TREE = 'd544013fd818a5d0a7e7a59b569cf8f1a21b2d77'
BRANCH = 'codex/chatgpt-wave15-w1-bookmark-native-20261127'
WT = '/mnt/development/projects/worktrees/anytype-bookmark-native-publish-20261127'
REMOTE = '/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127'
OLD = N/'final_authority_publication/publish_final_files_authority.py'
OLD_SHA = 'd4615e0cbbace5597d0842900449fc6dde68241a76e4ee50f46ccda4ce072a3f'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    spec = importlib.util.spec_from_file_location('bookmark_public_validator', HERE/'validate_public_evidence.py')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    remote_rows = [
        (DOC+'receipts/original-qualification-fail.json', REMOTE+'/qualification-attempt1/result.json', C/'actual-qualification-attempt1/result.json'),
        (DOC+'receipts/completion13-pass.json', REMOTE+'/qualification-completion-attempt1/result.json', C/'actual-qualification-completion-attempt1/result.json'),
        (DOC+'receipts/bodyless-attempt1-fail.json', REMOTE+'/bodyless-native-attempt1/result.json', C/'bodyless-consumer/actual-native-attempt1/result.json'),
        (DOC+'receipts/bodyless-attempt2-pass.json', REMOTE+'/bodyless-native-attempt2/result.json', C/'bodyless-consumer/actual-native-attempt2/result.json'),
        (DOC+'receipts/canonical-format.json', '/mnt/development/projects/evidence/pinkha-c-bookmark-format-20261127/attempt1/result.json', C/'actual-format1/result.json'),
        (DOC+'source/composed1625-source.json', REMOTE+'/qualification-completion-attempt1/source-manifest.json', C/'actual-qualification-completion-attempt1/source-manifest.json'),
        (DOC+'source/compiled1626-inputs.json', REMOTE+'/qualification-completion-attempt1/compiled-source-inputs.json', C/'actual-qualification-completion-attempt1/compiled-source-inputs.json'),
    ]
    local_rows = [
        (DOC+'source/formatted-source.json', C/'BOOKMARK_SOURCE_FORMATTED.json'),
        (DOC+'source/native1616-source.json', N/'final_authority_publication/receipts/native1616-source.json'),
        (DOC+'source/native1616-preimage-join.json', C/'FINAL1616_PREIMAGE_JOIN.json'),
        (DOC+'receipts/native1616-producer.json', N/'final_files_authority_product/completion2/actual_native1_result.json'),
        (DOC+'receipts/canonical-format-worker.json', C/'actual-format1/worker-result.json'),
        (DOC+'receipts/original-os-denial-controls.json', C/'bodyless-consumer/policy-source/canonical-policy-receipt.json'),
        (DOC+'receipts/source-installation.json', C/'installation/actual-installation1/result.json'),
        (DOC+'receipts/bodyless-original-source-installation.json', C/'bodyless-consumer/completion-source/installation/actual-installation1/result.json'),
        (DOC+'receipts/bodyless-policy-source-installation.json', C/'bodyless-consumer/policy-source/installation/actual-installation1/result.json'),
        (DOC+'receipts/c21-base-publication.json', WORKSPACE/'migration-relay/source-facts-publication/publication-attempt2-result.json'),
        (CODE+'qualification/original/qualify_bookmark_native.py', C/'qualify_bookmark_native.py'),
        (CODE+'qualification/complete_bookmark_native.py', C/'completion/complete_bookmark_native.py'),
        (CODE+'qualification/owned_swift_commands.py', N/'final_authority_publication/owned_swift_commands.py'),
        (CODE+'qualification/linux_outbound_denial.py', N/'public_native_inputs/linux_outbound_denial.py'),
        (CODE+'qualification/retained-eight-completion.review.patch', C/'completion/retained-eight-completion.review.patch'),
        (CODE+'qualification/current-native-compiler-evidence.review.patch', C/'completion/current-native-compiler-evidence.review.patch'),
        (CODE+'bodyless/original/run_bodyless_bookmark.py', C/'bodyless-consumer/run_bodyless_bookmark.py'),
        (CODE+'bodyless/before-policy-schema/run_bodyless_bookmark.py', C/'bodyless-consumer/completion-source/run_bodyless_bookmark.py'),
        (CODE+'bodyless/run_bodyless_bookmark.py', C/'bodyless-consumer/policy-source/run_bodyless_bookmark.py'),
        (CODE+'bodyless/policy-schema.review.patch', C/'bodyless-consumer/policy-source/policy-schema.review.patch'),
        (DOC+'README.md', HERE/'README.md'),
        (CODE+'publication/validate_public_evidence.py', HERE/'validate_public_evidence.py'),
        (CODE+'publication/prepare_publication.py', Path(__file__)),
    ]
    for name in ['native_boundary_support.py', 'owned_native_commands.py', 'owned_swift_commands_original.py', 'absolute_http_source_original.py']:
        local_rows.append((CODE+'bodyless/'+name, C/'bodyless-consumer'/name))
    formatted = json.loads((C/'BOOKMARK_SOURCE_FORMATTED.json').read_bytes())
    for name in formatted['files']:
        local_rows.append((CODE+validator.source_archive_path(name), C/'formatted-overlay'/name))
    for name, origin in [
        ('retained-go-environment', 'actual-qualification-attempt1/go-environment'),
        ('retained-sdk-eight', 'actual-qualification-attempt1/sdk-eight'),
        ('original-failed-server-compile', 'actual-qualification-attempt1/server-five'),
        ('current-native-compiler-environment', 'actual-qualification-completion-attempt1/current-native-compiler-environment'),
        ('new-server-five', 'actual-qualification-completion-attempt1/server-five'),
        ('native-build', 'actual-qualification-completion-attempt1/native-build'),
        ('native-metadata', 'actual-qualification-completion-attempt1/native-metadata'),
    ]:
        local_rows.append((DOC+'logs/'+name+'.log', C/origin/'original.log'))
    original = OLD.read_bytes()
    assert identity(original)['sha256'] == OLD_SHA
    text = original.decode()

    def replace(before, after):
        nonlocal text
        assert text.count(before) == 1, before
        text = text.replace(before, after)

    replace('"""Publish fixed final metadata/cache sources and actual evidence only.\n\nCreates one new isolated branch from the pinned network parent. No native,\ncompiler, account, prior test replay, existing worktree edit or force push.\n"""',
            '"""Publish exact optional Bookmark native source and actual public evidence.\n\nCreates one isolated branch from accepted C21. No compiler, native account,\nold-method replay, runtime worktree edit, C3 cache mutation or force push.\n"""')
    for name in ['PLAN_SHA', 'LOCAL_SHA', 'VALIDATOR_SHA']:
        line = next(line for line in text.splitlines() if line.startswith(name+' = '))
        replace(line, name+" = '__"+name+"__'")
    replace("ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'\n", '')
    replace('REMOTE_COUNT = 43', 'REMOTE_COUNT = '+str(len(remote_rows)))
    replace('LOCAL_COUNT = 6', 'LOCAL_COUNT = '+str(len(local_rows)+1))
    replace("BASE = 'e330c0230f352cadff76b4fa0feafd1032fa142e'", "BASE = '"+BASE+"'\nBASE_TREE = '"+TREE+"'")
    replace("BRANCH = 'codex/chatgpt-wave15-network-final-authority-20261127'", "BRANCH = '"+BRANCH+"'")
    replace("WORKTREE = Path('/mnt/development/projects/worktrees/anytype-network-final-authority-publish-20261127')", "WORKTREE = Path('"+WT+"')")
    replace("OUT = Path('/mnt/development/projects/evidence/pinkha-w1-final-authority-publication-20261127/attempt1')",
            "OUT = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-publication-20261127/attempt1')")
    replace("CODE = 'Tools/AnyEngineValidation/native_file_metadata_authority/'", "CODE = '"+CODE+"'")
    replace("DOC = 'docs/validation/20261127-native-file-metadata-authority/'", "DOC = '"+DOC+"'")
    replace("ROOT_FLOOR+(16*MIB if admission else 0)", "ROOT_FLOOR+(32*MIB if admission else 0)")
    replace("'rootAdmissionReserveBytes': 16*MIB", "'rootAdmissionReserveBytes': 32*MIB")
    replace("        for module_name, module_sha in [('validate_public_evidence',VALIDATOR_SHA),\n                                        ('final_product_admission',ADMISSION_SHA)]:\n            module_path = HERE/(module_name+'.py'); pin(module_path,module_sha)\n            module_spec = importlib.util.spec_from_file_location('final_publication_'+module_name,module_path)\n            loaded_module = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(loaded_module)\n            if module_name=='validate_public_evidence': evidence_validator=loaded_module\n            else: admission=loaded_module",
            "        module_path = HERE/'validate_public_evidence.py'; pin(module_path,VALIDATOR_SHA)\n        module_spec = importlib.util.spec_from_file_location('bookmark_public_evidence',module_path)\n        evidence_validator = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(evidence_validator)")
    replace('evidence_validator.validate(content,CODE,DOC,admission)', 'evidence_validator.validate(content,CODE,DOC)')
    replace("require(textgit('base-commit',['rev-parse',BASE+'^{commit}'])==BASE, 'exact network parent commit')",
            "require(textgit('base-commit',['rev-parse',BASE+'^{commit}'])==BASE and\n                textgit('base-tree',['rev-parse',BASE+'^{tree}'])==BASE_TREE, 'exact accepted C21 parent commit and full tree')")
    replace("'Enforce current FilesV2 metadata and cache authority'", "'Qualify guarded Bookmark creation and bodyless crash recovery'")
    for before, after in [
        ('pinkha-final-files-authority-source-publication-v1', 'pinkha-bookmark-native-create-source-publication-v1'),
        ('pinkha-final-files-authority-publication-plan-v1', 'pinkha-bookmark-native-create-publication-plan-v1'),
        ('pinkha-final-files-authority-public-file-set-v1', 'pinkha-bookmark-native-create-public-file-set-v1'),
        ('PASS_NORMAL_PUBLICATION_OF_FINAL_FILES_AUTHORITY', 'PASS_NORMAL_PUBLICATION_OF_BOOKMARK_NATIVE_13_AND_BODYLESS_PROOF'),
    ]:
        replace(before, after)
    ast.parse(text)
    template = text.encode()
    save(HERE/'publish_bookmark.template.py', template)
    local_rows.append((CODE+'publication/publish_bookmark.template.py', HERE/'publish_bookmark.template.py'))
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(True), text.splitlines(True),
                    'qualified-d461/publish_final_files_authority.py', 'bookmark/publish_bookmark.template.py'))
    save(HERE/'publisher.review.patch', patch.encode())
    content, remote, local, payload = {}, [], [], {}
    for name, source, path in remote_rows:
        data = path.read_bytes(); assert name not in content; content[name] = data
        remote.append(dict(destination=name, source=source, maximumBytes=2*1024**2, **identity(data)))
    for name, path in local_rows:
        data = path.read_bytes(); assert name not in content; content[name] = data
        local.append(dict(destination=name, **identity(data)))
        payload[name] = dict(base64=base64.b64encode(data).decode(), **identity(data))
    checked = validator.validate(content, CODE, DOC)
    plan = {'protocol': 'pinkha-bookmark-native-create-publication-plan-v1', 'expectedHead': BASE, 'expectedTree': TREE,
            'branch': BRANCH, 'worktree': WT, 'remotePublicCopies': remote, 'localPublicFiles': local,
            'existingSourceFilesReplaced': 0, 'newAccountOrRuntimeActions': 0, 'preparedStatus': 'SOURCE_ONLY_NOT_PUBLISHED'}
    plan_raw, payload_raw = encoded(plan), encoded(payload)
    save(HERE/'PUBLICATION_PLAN.json', plan_raw); save(HERE/'LOCAL_PUBLIC_FILES.json', payload_raw)
    actual = template
    for name, raw in [('PLAN_SHA', plan_raw), ('LOCAL_SHA', payload_raw), ('VALIDATOR_SHA', (HERE/'validate_public_evidence.py').read_bytes())]:
        before = ('__'+name+'__').encode(); assert actual.count(before) == 1
        actual = actual.replace(before, identity(raw)['sha256'].encode())
    ast.parse(actual); save(HERE/'publish_bookmark.py', actual)
    content[DOC+'publication-inputs.json'] = plan_raw
    descriptor = {'protocol': 'pinkha-bookmark-native-create-public-file-set-v1', 'baseCommit': BASE,
                  'inputPlanSHA256': identity(plan_raw)['sha256'], 'localPublicPayloadSHA256': identity(payload_raw)['sha256'],
                  'nativeExecutableCopiedToGit': False, 'privateAccountFiles': 0,
                  'files': {name: identity(data) for name, data in sorted(content.items())}}
    content[DOC+'FILES.json'] = encoded(descriptor)
    for name, data in content.items():
        save(HERE/'candidate'/name, data)
        if name.endswith('.py'):
            ast.parse(data)
        if name.endswith(('.py', '.go', '.md', '.json')):
            assert data.endswith(b'\n') and not data.endswith(b'\n\n'), 'retained source EOF whitespace: '+name
            assert all(line == line.rstrip(b' \t') for line in data.splitlines()), 'retained source trailing whitespace: '+name
    prep = {'status': 'PREPARED_SOURCE_ONLY_NOT_PUBLISHED', 'files': len(content), 'bytes': sum(map(len, content.values())),
            'remoteMembers': len(remote), 'localMembers': len(local), 'plan': identity(plan_raw), 'payload': identity(payload_raw),
            'publisher': identity(actual), 'template': identity(template), 'validator': identity((HERE/'validate_public_evidence.py').read_bytes()),
            'reviewPatch': identity(patch.encode()), 'pureLocalEvidenceValidation': checked,
            'originalPublisher': {'path': str(OLD), 'sha256': OLD_SHA}, 'newRuntimeOrTestActions': 0}
    save(HERE/'PREPARATION.json', encoded(prep))
    print(json.dumps({key: value for key, value in prep.items() if key != 'pureLocalEvidenceValidation'}, sort_keys=True))


if __name__ == '__main__':
    main()

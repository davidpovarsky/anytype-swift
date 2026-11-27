#!/usr/bin/env python3
"""Assemble exact qualified Host sources and lossless evidence for one own-branch publication."""
import ast
import base64
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import re
import zlib

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
OUT = BASE / 'publication'
CANDIDATE = OUT / 'candidate'
TOOLS = 'Tools/AnyEngineValidation/bookmark_creation_contract_20261127'
VALIDATION = 'docs/validation/20261127-bookmark-creation-contract'
PARENT = '063d3ef0b16392f67e5044faa81cf8689a75dab2'
PARENT_TREE = 'ed8e302914a0e25eb848625eb8215ec7821a34d7'
BRANCH = 'codex/chatgpt-wave15-w1-bookmark-contract-20261127'
BEFORE = {
    'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeObjectCreator.swift': '7a641b9693803360603cb2df554eaa316fbeb1c59127795a6592404d437444f3',
    'docs/architecture/ordinary-file-attachment-contract-20261127.md': 'f234c05963617fca10bd417f2f050127899fd795773bc0a5579aa28741b27abb',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None):
    raw = Path(path).read_bytes()
    if expected is not None and sha(raw) != expected:
        raise RuntimeError('local original identity differs: ' + str(path))
    return raw


def put(relative, raw):
    target = CANDIDATE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != raw:
        raise RuntimeError('existing candidate differs: ' + relative)
    target.write_bytes(raw)


def document(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def file_row(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(CANDIDATE).as_posix(), 'mode': '100644', 'type': 'blob',
            'size': len(raw), 'sha256': sha(raw),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def main():
    if CANDIDATE.exists():
        raise RuntimeError('candidate is exclusive; review a changed input in a new preparation')
    CANDIDATE.mkdir(parents=True)
    original_raw = read(BASE/'qualification/actual-components-attempt1/result.json',
        '9aa1b527c5df731f27f103cdeab2d93f672ba5d13bd9061167826ce5ef6aa465')
    original = json.loads(original_raw)
    admission_raw = read(BASE/'qualification/actual-components-attempt1/compiled-source-inputs.json',
        '01c2db0d00d02e123c4697fcf034b4afe8214430fabf406e64192379af2da7c5')
    admission = json.loads(admission_raw)
    actual_raw = read(BASE/'qualification/http-continuation/actual-http10-attempt1-result.json',
        '8a4ca85c7b7c0349c03e50145554324b7670129d029adbb31fbf8040910d82d8')
    actual = json.loads(actual_raw)
    assert original['status'] == 'FAIL'
    assert actual['status'] == 'PASS_COMPONENT31_WITH_REUSED21_AND_NEW_HTTP10'
    assert actual['errors'] == actual['completionErrors'] == []
    assert actual['qualifiedComponentMethods']['total'] == 31
    assert actual['qualifiedComponentMethods']['reusedActualPasses'] == 21
    assert actual['qualifiedComponentMethods']['newActualPasses'] == 10
    assert actual['qualifiedComponentMethods']['skipped'] == 0
    assert actual['compilerInvocations'] == actual['priorPassingMethodsReplayed'] == 0
    assert actual['compiledSourceInputsUnchanged'] and actual['compiledProductsAndModesUnchanged']
    assert actual['currentCryptoClosureUnchanged'] and actual['isolatedSourceCopyModesUnchanged']
    assert admission['counts']['productionCompiledFiles'] == 33
    assert admission['counts']['compiledTestFiles'] == 3
    original_inputs = admission['originalInputs']
    copied_inputs = admission['isolatedCopies']
    source_bindings = []
    for kind in ['Sources', 'Tests']:
        sub = 'Sources/PinkhaAnyHost' if kind == 'Sources' else 'Tests/PinkhaAnyHostTests'
        for path in sorted((BASE/kind).glob('*.swift')):
            raw = read(path)
            row = {'bytes': len(raw), 'sha256': sha(raw)}
            originals = [name for name, value in original_inputs.items()
                         if name.endswith('/'+path.name) and value == row]
            copies = [name for name, value in copied_inputs.items()
                      if name.endswith('/'+path.name) and value == row]
            assert len(originals) == len(copies) == 1, path.name
            destination = 'Modules/PinkhaAnyHost/'+sub+'/'+path.name
            put(destination, raw)
            source_bindings.append({'path': destination, **row,
                'originalAdmittedPath': originals[0], 'compiledIsolatedCopy': copies[0]})
    assert len(source_bindings) == 5
    for path in sorted((BASE/'handoff/docs/architecture').glob('*.md')):
        put('docs/architecture/'+path.name, read(path))

    template_path = ROOT/'publish_upload_recovery.py'
    template = read(template_path, '1d630aa88b6122e9c70ca76fa4f39f120cd6fe59b5d88a5ca2db38c7d0de9593').decode()
    changed = template
    substitutions = {
        "PARENT = 'e96ba072887e7581ed6de20fdd81e0897c83763d'": "PARENT = '"+PARENT+"'",
        "PARENT_TREE = '0f0f558354cb2ceb7ad840e952d1cd5dafcc9a23'": "PARENT_TREE = '"+PARENT_TREE+"'",
        "BRANCH = 'codex/chatgpt-wave15-w1-upload-recovery-20261127'": "BRANCH = '"+BRANCH+"'",
        "OUT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/recovery-source-publication1')":
            "OUT = Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127/source-publication1')",
        "'declaredComponentMethods': 35": "'declaredComponentMethods': 31",
        "all six exact replacements required": "all declared exact replacements required",
        "Drain upload delegates and preserve scoped recovery receipts": "Bind Bookmark creation to exact native definitions and value bytes",
    }
    for before, after in substitutions.items():
        assert changed.count(before) == 1, before
        changed = changed.replace(before, after)
    changed, replacements = re.subn(r'^BEFORE_IMAGES = .*$', 'BEFORE_IMAGES = '+repr(BEFORE), changed, flags=re.M)
    assert replacements == 1
    put(TOOLS+'/publication/publish_bookmark_contract.template.py', changed.encode())
    patch = ''.join(difflib.unified_diff(template.splitlines(True), changed.splitlines(True),
        fromfile='qualified-1d630/publish_upload_recovery.py', tofile='bookmark/publish_bookmark_contract.template.py'))
    # Incomplete placeholders have identical syntax after benign substitutions.
    def functions(text):
        tree = ast.parse(text.replace('__FILE_COUNT__','0'))
        return {n.name: ast.dump(n, include_attributes=False) for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert functions(template) == functions(changed)
    (OUT/'publisher.review.patch').write_text(patch)

    encoded = []
    inputs = [
        (BASE/'qualification/run_bookmark_components.py', TOOLS+'/run_bookmark_components.py', False),
        (BASE/'qualification/bookmark-component-inputs.json', TOOLS+'/bookmark-component-inputs.json', False),
        (BASE/'qualification/qualify_current_c3_crypto.py', TOOLS+'/qualify_current_c3_crypto.py', False),
        (BASE/'qualification/qualify_bookmark_crypto_c3.py', TOOLS+'/qualify_bookmark_crypto_c3.py', False),
        (BASE/'qualification/crypto-header-source-manifest.json', TOOLS+'/crypto-header-source-manifest.json', False),
        (BASE/'qualification/owned_swift_commands.py', TOOLS+'/owned_swift_commands.py', False),
        (BASE/'qualification/http-continuation/run_bookmark_http_continuation.py', TOOLS+'/run_bookmark_http_continuation.py', False),
        (BASE/'qualification/http-continuation/install_source.py', TOOLS+'/http-install-source.py', False),
        (BASE/'installation/install_sources.template.py', TOOLS+'/source-install/install_sources.template.py', False),
        (BASE/'prepare_source_install.py', TOOLS+'/source-install/prepare_source_install.py', False),
        (BASE/'prepare_component_qualifier.py', TOOLS+'/source-install/prepare_component_qualifier.py', False),
        (BASE/'qualification/actual-components-attempt1/result.json', VALIDATION+'/original-attempt1-result.json', False),
        (BASE/'qualification/actual-components-attempt1/original.log', VALIDATION+'/original-attempt1.log', False),
        (BASE/'qualification/actual-components-attempt1/compiled-source-inputs.json', VALIDATION+'/compiled-source-inputs.json.gz', True),
        (BASE/'qualification/http-continuation/actual-http10-attempt1-result.json', VALIDATION+'/http10-attempt1-result.json.gz', True),
        (BASE/'qualification/http-continuation/actual-http10-attempt1-original.log', VALIDATION+'/http10-attempt1.log', False),
        (BASE/'installation/actual-prepared1-install-result.json', VALIDATION+'/original-source-install-result.json', False),
        (BASE/'qualification/http-continuation/actual-source-install-result.json', VALIDATION+'/http-source-install-result.json', False),
        (BASE/'originals/AnyNativeObjectCreator.swift', VALIDATION+'/original-AnyNativeObjectCreator.swift.gz', True),
        (BASE/'prepare_publication.py', TOOLS+'/publication/prepare_publication.py', False),
    ]
    for source, destination, compressed in inputs:
        raw = read(source)
        # Preserve immutable historical bytes. Do not rewrite trailing spaces
        # to make the publication's normal git diff --check pass.
        bad_whitespace = any(line.endswith((b' ', b'\t')) for line in raw.splitlines())
        compressed = compressed or bad_whitespace
        if compressed and not destination.endswith('.gz'):
            destination += '.gz'
        data = gzip.compress(raw, compresslevel=9, mtime=0) if compressed else raw
        if compressed:
            assert gzip.decompress(data) == raw
            encoded.append({'publishedPath': destination, 'encoding': 'gzip',
                'raw': {'bytes': len(raw), 'sha256': sha(raw)},
                'encoded': {'bytes': len(data), 'sha256': sha(data)}, 'inverseVerified': True})
        put(destination, data)
    put(VALIDATION+'/lossless-evidence-encoding.json', document({'schema':1, 'files':encoded}))
    put(VALIDATION+'/qualified-source-bindings.json', document({
        'schema':1, 'parentCommit':PARENT, 'completeOriginalAdmissionSHA256':sha(admission_raw),
        'originalFailedReceiptSHA256':sha(original_raw), 'actualContinuationReceiptSHA256':sha(actual_raw),
        'files':source_bindings, 'newSourceOrTestChangesAfterQualification':False,
        'qualifiedMethods':{'total':31,'retained':21,'newHTTP':10,'skipped':0},
        'noNativeOrAppleAcceptanceClaim':True}))
    readme = '''# Exact Bookmark definition contract and post-close recovery evidence

This Wave 1 handoff extends `PinkhaAnyHost`. Wave 3 owns application integration and the final branch; Wave 2 owns editor and owner-transition UI. Parent commit is `063d3ef0b16392f67e5044faa81cf8689a75dab2`.

## Source and behavior

The object creator now compares persisted string values and dictionary keys by exact UTF-8 bytes, including nested objects and ordered arrays. It continues to permit unrelated native top-level metadata. A canonically equivalent but byte-distinct value cannot verify an original mutation or justify a replacement dispatch.

The additive Bookmark frame reader obtains the typed, scoped condition from the current native capability and read-only frame endpoint. The immutable creation intent binds that condition and its original URL value. Nil conditions preserve legacy fingerprints. Unsupported capability is refused before journal reservation or object POST. The factory remains lazy for existing non-native workspace construction. Final cancellation and current authority are checked after awaited admission before delivering a known created ID.

Four additional post-close component tests exercise the already published attachment creator without changing its production bytes. They verify memory-only acknowledgement export through both fresh read-authority checks after modeled owner/journal closure, recovery through a new current native reader using the original reservation, and no retired I/O or second upload. Real protected-file and mounted application acceptance remain separate.

## Actual qualification

The original attempt built 33 production source files and three test files. Its 31 method starts yielded 21 passes and ten HTTP fixture setup failures. The empty fixture directory inherited mode 02700, while the unchanged test requires exactly 0700. Original receipt `9aa1b527c5df731f27f103cdeab2d93f672ba5d13bd9061167826ce5ef6aa465` remains FAIL.

The continuation creates a new explicit 0700 fixture root and reuses the same compiled product. Job `job_6fb54bac9c2d` ran on 27 November 2026 from 19:43:06 to 19:43:30 UTC. Ten new selected methods passed with zero skips. All 17 fixture servers ended with complete EOF/exit evidence in the original owned group. There were 66 GETs, ten read-only frame POSTs and zero object-creation POSTs. The sole new command ended normally and was positively absent, with no forced cleanup, signals or cleanup errors.

Receipt `8a4ca85c7b7c0349c03e50145554324b7670129d029adbb31fbf8040910d82d8` qualifies all 31 obligations as 21 retained plus ten new passes. No passing method, native account operation, compiler or dependency build was replayed. Original and copied sources, current Crypto inputs/products, source-copy modes and the later observed complete product/mode census remained unchanged. The later product census is not represented as a hash emitted by the original failed producer.

The complete 526,234-byte compiled-source admission is SHA-256 `01c2db0d00d02e123c4697fcf034b4afe8214430fabf406e64192379af2da7c5`. `qualified-source-bindings.json` binds each of the five delivered Swift files to its original admission and compiled isolated copy. `lossless-evidence-encoding.json` gives raw and gzip identities; decompression restores the exact original bytes, including historical whitespace. No qualified file was normalized to pass a formatting check.

## Integration limits and controls

The native Bookmark implementation, its 13 focused native tests and fresh bodyless warm/crash/cold proof are separate Wave 1 work. This commit does not assert their acceptance or enable an unqualified native capability. The original Bookmark importer and ordinary creation path retain separate evidence. Heart Native103/Swift23, original functional migration correspondence, large-file production cloud capacity and Apple application qualification also remain separately tracked.

The two architecture contracts describe scope/lifetime, exact value identity, the same-original-reservation rule, process-only acknowledgement export, module-qualified file reference types, current FilesV2 authority, quota behavior and the Bookmark frame. No Hanlin, MiniApps, Otzaria or final-integration application source is changed by this publication.

Primary raw Oracle evidence remains under `/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127`: `components-attempt1/result.json`, `components-attempt1/compiled-source-inputs.json`, `http10-attempt1/result.json`, and their original command logs. Exact controllers are retained under `Tools/AnyEngineValidation/bookmark_creation_contract_20261127`; absolute admission paths refer to those original Oracle inputs. The source-installation receipts establish source placement only. Publication uses the existing normal-commit/normal-push controller, exact before-images, complete parent/candidate tree comparison, normal diff checking and ordinary-user readability of every new Git object and the complete tree. It neither resets another branch nor changes shared repository permissions.
'''
    put(VALIDATION+'/README.md', readme.encode())
    manifest = {'schema':1,'parentCommit':PARENT,'files':[file_row(p) for p in sorted(CANDIDATE.rglob('*')) if p.is_file()]}
    manifest_raw = document(manifest)
    put(VALIDATION+'/candidate-manifest.json', manifest_raw)
    helper = read(BASE/'qualification/owned_swift_commands.py', 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56')
    files = []
    for p in sorted(CANDIDATE.rglob('*')):
        if p.is_file():
            files.append(dict(file_row(p), contentBase64=base64.b64encode(read(p)).decode()))
    assert set(BEFORE) <= {r['path'] for r in files}
    payload = {'files':files, 'helperBase64':base64.b64encode(helper).decode(),
               'helperSHA256':sha(helper), 'candidateManifestSHA256':sha(manifest_raw)}
    raw = document(payload)
    packed = zlib.compress(raw,9)
    assert len(raw) < 4*1024**2 and len(packed) < 4*1024**2
    publisher = changed.replace('__PAYLOAD__',base64.b64encode(packed).decode()).replace(
        '__PACKED_SHA__',sha(packed)).replace('__RAW_SHA__',sha(raw)).replace('__FILE_COUNT__',str(len(files)))
    ast.parse(publisher)
    (OUT/'publication-payload.json').write_bytes(raw)
    (OUT/'publication-payload.zlib').write_bytes(packed)
    (OUT/'publish_bookmark_contract.py').write_text(publisher)
    report = {'status':'PREPARED_SOURCE_ONLY_NOT_PUBLISHED','parent':PARENT,'parentTree':PARENT_TREE,'branch':BRANCH,
              'files':len(files),'sourceBytes':sum(r['size'] for r in files),'candidateManifestSHA256':sha(manifest_raw),
              'publisher':{'bytes':len(publisher.encode()),'sha256':sha(publisher.encode())},
              'payload':{'bytes':len(raw),'sha256':sha(raw)},'compressedPayload':{'bytes':len(packed),'sha256':sha(packed)},
              'publisherTemplate':{'bytes':len(changed.encode()),'sha256':sha(changed.encode())},
              'publisherPatch':{'bytes':len(patch.encode()),'sha256':sha(patch.encode())},
              'allPublisherFunctionsUnchanged':True,'newCompilerOrTestCommands':0}
    (OUT/'PREPARATION.json').write_bytes(document(report))
    print(json.dumps(report))


if __name__ == '__main__':
    main()

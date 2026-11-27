#!/usr/bin/env python3
"""Read the actual transport using the exact published consumer, without extraction."""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, sys, tarfile, time, zipfile

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence/pinkha-native8ac-stream-export-45972687659-1'
EXPECTED_ZIP = 'a100f09fcb7bc8a444b0ba81ef851437615d3e4a9f8adc3b20f1fbaf273bcf57'
EXPECTED_PAYLOAD = 'cc42f37c42c2ee1b860dae8395520482a857da725bd9e8923d3ac398cb032a35'
EXPECTED_MANIFEST = '31e96fce573e5e42698414c3f2a60923105af370f75ca6af8e006756aafb16a3'
EXPECTED_READER = 'e8aaf254140c06410813d5ab6f3b9168b71c1722dfe2ecdac8155a1bdc9d4d3c'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024**2), b''): h.update(b)
    return h.hexdigest()

def exact(path, expected, size=None):
    if path.is_symlink() or not path.is_file() or sha(path) != expected:
        raise ValueError('Exact original file mismatch: ' + str(path))
    if size is not None and path.stat().st_size != size:
        raise ValueError('Exact original size mismatch: ' + str(path))

def main():
    if sys.flags.optimize: raise RuntimeError('Assertions are required')
    result = {'schema': 'pinkha-root-downloaded-native8ac-qualification/v1',
              'runID': 45972687659, 'runAttempt': 1, 'artifactID': 15184549962,
              'controlCommit': '7feaa7bacc36ec4aefd928a79086a8de01640dfa',
              'testsExecuted': 0, 'nativeBuildsExecuted': 0, 'sourceFilesApplied': 0,
              'applicationAcceptance': False, 'new4905NativeAcceptance': False,
              'status': 'RUNNING', 'startedAt': time.time()}
    try:
        assert shutil.disk_usage(ROOT).free > 512 * 1024**2
        exact(ROOT / 'original-inputs.zip', EXPECTED_ZIP, 242676558)
        exact(ROOT / 'native_inputs.original.py', EXPECTED_READER, 13058)
        exact(EVIDENCE / 'payload-manifest.json', EXPECTED_MANIFEST, 1083562)
        exact(EVIDENCE / 'receipt.json', '98830b27f08b3182617cbae794060d250220cb95c2a8a71d05a0606ebc1fe576', 2221)
        receipt = json.loads((EVIDENCE / 'receipt.json').read_bytes())
        terminal = json.loads((EVIDENCE / 'producer-terminal.json').read_bytes())
        assert receipt['sourceBeforeEqualsAfter'] is True
        assert terminal['terminal'] == {'code': 0, 'signal': None}
        assert terminal['ownedGroup']['status'] == 'ABSENT_ESRCH_LATCHED'
        assert terminal['diagnostics']['first'] is None and not terminal['cleanupErrors']
        assert terminal['finalizedArtifactID'] == '15184549962'
        manifest = json.loads((EVIDENCE / 'payload-manifest.json').read_bytes())
        payload = ROOT / 'native8ac-inputs.original.tar.gz'
        with zipfile.ZipFile(ROOT / 'original-inputs.zip') as z:
            members = z.infolist()
            assert len(members) == 1 and members[0].filename == 'native8ac-inputs.tar.gz'
            assert members[0].file_size == 242676398 and members[0].compress_type == zipfile.ZIP_STORED
            with z.open(members[0]) as src, payload.open('xb') as dst:
                shutil.copyfileobj(src, dst, length=1024**2)
        exact(payload, EXPECTED_PAYLOAD, 242676398)
        spec = importlib.util.spec_from_file_location('exact_original_native8ac_consumer', ROOT / 'native_inputs.original.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The original reader validates every regular member, path, case-fold,
        # mode, size, hash and complete inventory. No destination is provided.
        checked = module.read_payload(payload, expected_manifest=EXPECTED_MANIFEST)
        assert checked['files'] == 4896
        small = {}
        with tarfile.open(payload, 'r:gz') as t:
            for member in t:
                if member.name == 'source-manifest.json' or member.name.startswith('native/'):
                    assert member.isfile() and member.size <= 2 * 1024**2
                    small[member.name] = t.extractfile(member).read()
        source_raw = small['source-manifest.json']
        assert hashlib.sha256(source_raw).hexdigest() == module.MANIFEST_SHA
        source = json.loads(source_raw)
        source_rows = {k.removeprefix('native-source/'): {'bytes': v['bytes'], 'sha256': v['sha256']}
                       for k, v in manifest['files'].items() if k.startswith('native-source/')}
        original_rows = {k: {'bytes': v['bytes'], 'sha256': v['sha256']} for k, v in source['files'].items()}
        assert source_rows == original_rows and len(source_rows) == 4868
        assert sum(v['bytes'] for v in source_rows.values()) == 89636647
        assert hashlib.sha256(small['native/framework-files.json']).hexdigest() == module.FRAMEWORK_SHA
        assert hashlib.sha256(small['native/receipt.json']).hexdigest() == module.ASSEMBLY_SHA
        slices = {}
        for kind, (receipt_sha, command_sha, binary_sha, platform) in module.SLICE_PINS.items():
            assert hashlib.sha256(small[f'native/{kind}/receipt.json']).hexdigest() == receipt_sha
            assert hashlib.sha256(small[f'native/{kind}/combined-gomobile-bind.command.json']).hexdigest() == command_sha
            row = manifest['files'][f'Lib.xcframework/{platform}/Lib.framework/Lib']
            assert row['sha256'] == binary_sha
            slices[kind] = {'bytes': row['bytes'], 'sha256': binary_sha, 'originalReceiptSHA256': receipt_sha}
        assert len([p for p in manifest['files'] if p.startswith('Lib.xcframework/')]) == 19
        target = ROOT / 'qualified-original-metadata'; target.mkdir(exist_ok=False)
        for name, raw in small.items():
            p = target / name; p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f: f.write(raw)
        result.update(status='PASS_DOWNLOADED_ORIGINAL_NATIVE8AC_PAYLOAD_MEMBERS_ONLY',
                      zipSHA256=EXPECTED_ZIP, payloadSHA256=EXPECTED_PAYLOAD,
                      originalConsumerSHA256=EXPECTED_READER, originalReaderResult=checked,
                      nativeSourceManifestSHA256=module.MANIFEST_SHA, sourceFiles=4868,
                      sourceBytes=89636647, frameworkFiles=19, originalSlices=slices,
                      fullSourceTreeExtracted=False, frameworkExtracted=False,
                      ownedProducerGroupAbsent=True)
    except BaseException as e:
        result.update(status='FAIL_DOWNLOADED_ORIGINAL_NATIVE8AC_QUALIFICATION',
                      error={'type': type(e).__name__, 'message': str(e)})
    finally:
        result['finishedAt'] = time.time()
        p = ROOT / 'root-downloaded-qualification.json'
        with p.open('x') as f: json.dump(result, f, sort_keys=True, indent=2); f.write('\n')
        print(json.dumps({'status': result['status'], 'receipt': str(p), 'sha256': sha(p),
                          'error': result.get('error'), 'files': result.get('originalReaderResult', {}).get('files')}))
    return 0 if result['status'].startswith('PASS_') else 1

if __name__ == '__main__': raise SystemExit(main())

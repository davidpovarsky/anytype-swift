#!/usr/bin/env python3
"""Restore exactly one of the four frozen compressed blobs, exclusively.

This never runs a compiler, native product or old decompression helper. The
compressed blob must be restored first; existing product restore scripts still
require their original compressed input paths. The Windows custody copy stays.
"""
from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, os, shutil, signal, stat, sys, time, uuid


def digest(path):
    h = hashlib.sha256()
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME), 'rb') as f:
        for part in iter(lambda: f.read(1024**2), b''): h.update(part)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--map-sha256', required=True)
    parser.add_argument('--blob-name', required=True, choices=['attempt2-cutover-core.test.xz', 'attempt4-cutover-core.test.xz', 'attempt5-cutover-core.test.xz', 'cutover-core.test.gz'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--oracle-hostname', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0 and os.uname().nodename == args.oracle_hostname
    if sys.flags.optimize: raise RuntimeError('acceptance assertions must remain enabled')
    assert args.map.is_absolute() and args.map.name == 'restoration-map.json'
    assert str(args.map).startswith('/var/lib/pinkha-w1-offhost-custody-20261127/')
    assert args.map.parent.resolve() == args.map.parent
    assert len(args.map_sha256) == 64 and digest(args.map) == args.map_sha256
    manifest = json.loads(args.map.read_bytes())
    assert manifest['protocol'] == 'four-frozen-compressed-native-restoration-map-v1'
    assert manifest['windowsHost'] == 'DAVID_AND_GOLDY' and manifest['oldBlobPathsWillBeAbsent'] is True
    controller = args.map.with_name('offhost_frozen_blobs.py')
    assert digest(controller) == manifest['controllerSHA256']
    assert digest(Path(__file__)) == manifest['restoreHelperSHA256']
    spec = importlib.util.spec_from_file_location('frozen_blob_custody', controller)
    module = importlib.util.module_from_spec(spec)
    # The caller supplies the retained manifest digest; that pins this imported
    # controller and this helper before either performs a remote operation.
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    assert manifest['nativePins'] == module.PINS
    assert len(manifest['blobs']) == 4
    pinned = {Path(p).name: (p, size, sha) for p, size, sha in module.BLOBS}
    assert len(pinned) == 4 and {x['name'] for x in manifest['blobs']} == set(pinned)
    for item in manifest['blobs']:
        assert (item['source'], item['bytes'], item['sha256']) == pinned[item['name']]
        assert item['windowsPath'] == manifest['windowsRoot'] + '\\' + item['name']
    token = manifest['token']
    assert len(token) == 32 and all(c in '0123456789abcdef' for c in token)
    assert manifest['windowsRoot'] == module.WIN_PARENT + '\\pinkha-frozen-e-20261127-' + token
    row = next(x for x in manifest['blobs'] if x['name'] == args.blob_name)
    source = Path(row['source'])
    assert source.parent.is_dir() and source.parent.resolve() == source.parent
    out = args.output
    assert out.is_absolute() and str(out).startswith('/var/lib/pinkha-w1-offhost-custody-20261127/')
    assert out.parent.resolve() == out.parent and out != args.map.parent
    os.umask(0o077); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {'protocol': 'four-frozen-compressed-native-exclusive-restore-v1', 'status': 'RUNNING', 'restorationMap': str(args.map), 'restorationMapSHA256': args.map_sha256, 'source': str(source), 'bytes': row['bytes'], 'sha256': row['sha256'], 'windowsCopyRetained': True, 'commands': [], 'errors': [], 'nativeRuns': 0, 'compilerRuns': 0, 'accountOpens': 0, 'decompressionRuns': 0, 'installed': False}
    tmp = source.with_name(source.name + '.restore-' + uuid.uuid4().hex)
    result['exclusiveTemporaryPath'] = str(tmp)
    def save():
        result['seconds'] = round(time.monotonic() - started, 3)
        module.atomic_json(out/'result.json', result)
    def guard():
        assert time.monotonic() - started < 600, 'bounded blob restoration'
        assert shutil.disk_usage('/var/lib').free >= 2*1024**3, 'unchanged root floor'
        assert shutil.disk_usage(source.parent).free >= 512*1024**2, 'unchanged development floor'
        assert not (out/'abort').exists(), 'owned restore abort'
        assert sum(p.stat().st_blocks*512 for p in out.iterdir() if p.is_file()) <= 4*1024**2
    def interrupted(*_): raise RuntimeError('owned exclusive blob restoration interrupted')
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM,signal.SIGINT})
    try:
        guard()
        assert shutil.disk_usage('/var/lib').free >= 2*1024**3 + 4*1024**2
        assert shutil.disk_usage(source.parent).free >= 512*1024**2 + row['bytes'] + 4*1024**2
        assert not os.path.lexists(source), 'existing destination is never overwritten'
        result['nativePinsBefore'] = {p: module.sha_file(p) for p in module.PINS}
        assert result['nativePinsBefore'] == module.PINS
        save()
        module.ssh_stream(module.ps_readback(manifest['windowsRoot'],token,row['name'],row['bytes']), 'restore-exact-compressed-blob', save, guard, result['commands'], expected_size=row['bytes'], expected_sha=row['sha256'], destination=tmp)
        assert module.sha_file(tmp) == row['sha256'] and tmp.stat().st_size == row['bytes']
        expected = row['metadata']
        assert expected['bytes'] == row['bytes'] and expected['links'] == 1
        os.chown(tmp, expected['uid'], expected['gid'], follow_symlinks=False)
        os.chmod(tmp, expected['mode'], follow_symlinks=False)
        for name in os.listxattr(tmp, follow_symlinks=False):
            if name not in expected['xattrs']: os.removexattr(tmp,name,follow_symlinks=False)
        for name,value in expected['xattrs'].items():
            os.setxattr(tmp,name,base64.b64decode(value,validate=True),follow_symlinks=False)
        os.utime(tmp, ns=(expected['atime_ns'],expected['mtime_ns']),follow_symlinks=False)
        fd = os.open(tmp, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
        try: os.fsync(fd)
        finally: os.close(fd)
        restored = module.metadata(tmp)
        fields = ('bytes','mode','uid','gid','atime_ns','mtime_ns','xattrs','links')
        assert all(restored[k] == expected[k] for k in fields)
        assert module.sha_file(tmp) == row['sha256']
        result['verifiedTemporaryMetadata'] = restored
        result['nativePinsBeforeInstall'] = {p: module.sha_file(p) for p in module.PINS}
        assert result['nativePinsBeforeInstall'] == module.PINS
        guard(); assert not os.path.lexists(source)
        assert all(x['status']=='PASS' and x.get('groupPositivelyAbsent') and not x['forcedCleanup'] and x['exitCode']==0 for x in result['commands'])
        result['installStage']='exclusive-link-intent'; save()
        # Atomic hard-link installation refuses regular files AND dangling
        # symlinks created between the preceding observation and this call.
        module.install_exclusively(tmp,source)
        result.update(installed=True,installStage='exclusive-install-complete'); save()
        assert module.sha_file(source)==row['sha256']
        actual=module.metadata(source);assert all(actual[k]==expected[k] for k in fields)
        result['restoredMetadata']=actual
        result['nativePinsAfter']={p:module.sha_file(p) for p in module.PINS}
        assert result['nativePinsAfter']==module.PINS
        result['status']='PASS_EXACT_COMPRESSED_BLOB_RESTORED_EXCLUSIVELY_NO_NATIVE_RUN'
    except BaseException as error:
        result['status']='FAIL_EXCLUSIVE_COMPRESSED_BLOB_RESTORE'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        result['allOwnedSSHGroupsAbsent']=all(x.get('groupPositivelyAbsent') for x in result['commands'])
        if not result['allOwnedSSHGroupsAbsent']: result['status']='FAIL_EXCLUSIVE_COMPRESSED_BLOB_RESTORE'
        # Preserve a partial temporary file and any installed destination on
        # every uncertain outcome. Do not unlink another writer's destination.
        result['temporaryPathPresent']=os.path.lexists(tmp)
        result['originalPathPresent']=os.path.lexists(source)
        result['originalDecompressionHelperExecuted']=False
        save()
    print(json.dumps({'status':result['status'],'receipt':str(out/'result.json'),'sha256':module.sha_file(out/'result.json'),'seconds':result['seconds']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__ == '__main__': raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only continuation after Docker reordered identical mount-array rows."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import time
import yaml

BASE = Path('/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network')
CONTROL = Path(__file__).with_name('provision_isolated_peer_network.py')

def digest(p):
    assert p.is_file() and not p.is_symlink()
    return hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(rows):
    result = json.loads(json.dumps(rows))
    for row in result:
        row['mounts'].sort(key=lambda m: (m['Destination'], m['Source'], m['Type']))
    return sorted(result, key=lambda row: row['id'])

def main():
    os.umask(0o077)
    out = BASE / 'qualification-attempt1'
    out.mkdir(mode=0o700)
    result = {'status': 'FAIL', 'commandsThatMutateNetwork': 0, 'accountsCreated': 0,
              'nativePeerAcceptance': False, 'startedAt': time.time()}
    try:
        assert digest(CONTROL) == '05921453594d5d1b4d97e900f62d8c3c0776227d31f119f93ee74dde7b88b781'
        original = BASE / 'provision-attempt1/receipt.json'
        assert digest(original) == '45187a9c2b7c55f332be143a7eb7304c95699e69d631d961fa168fdc40a54252'
        prior = json.loads(original.read_bytes())
        assert prior['status'] == 'FAIL'
        assert prior['error'] == {'message': 'old T2 identity/state changed externally during new-network setup', 'type': 'AssertionError'}
        assert len(prior['commands']) == 5 and all(r['exitCode'] == 0 for r in prior['commands'])
        spec = importlib.util.spec_from_file_location('network_original', CONTROL)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        before = json.loads((BASE / 'provision-attempt1/original-t2-containers-before.json').read_bytes())
        after = json.loads((BASE / 'provision-attempt1/original-t2-containers-after.json').read_bytes())
        current = module.metadata('pinkha-t2-20261125')
        assert canonical(before) == canonical(after) == canonical(current), 'any change except unordered container/mount rows remains a failure'
        assert subprocess.check_output(['git', '-C', str(module.SOURCE), 'rev-parse', 'HEAD'], timeout=10).decode().strip() == module.COMMIT
        assert not subprocess.check_output(['git', '-C', str(module.SOURCE), 'diff', '--name-only'], timeout=10).strip()
        owned = module.metadata(module.PROJECT)
        assert {r['service'] for r in owned} == set(module.IMAGE_IDS)
        assert len(owned) == len(module.IMAGE_IDS)
        for row in owned:
            assert row['image'] == module.IMAGE_IDS[row['service']]
            for bindings in row['ports'].values():
                assert all(b['HostIp'] == '127.0.0.1' for b in bindings)
            for mount in row['mounts']:
                if mount['Type'] == 'bind':
                    assert Path(mount['Source']).is_relative_to(module.SOURCE)
            if row['service'] == 'any-sync-coordinator_bootstrap':
                assert row['state'] == 'exited'
                detail = json.loads(subprocess.check_output(['sudo', '-n', 'docker', 'inspect', row['id']], timeout=10))[0]
                assert detail['State']['ExitCode'] == 0
            else:
                assert row['state'] == 'running'
            if row['service'] in {'mongo-1', 'redis', 'garage', 'netcheck'}:
                assert row['health'] == 'healthy'
        assert digest(BASE / 'runtime.compose.json') == prior['runtimeComposeSHA256']
        public = BASE / 'mac-public-nodeconf.yml'
        assert digest(public) == prior['macPublicNodeconfSHA256'] == 'fc43639b27c8c7ab50897542a99ecddd3266e85eedf575625d20391684e476e0'
        client = yaml.safe_load(public.read_bytes())
        assert len(client['nodes']) == 6
        assert [r['addresses'] for r in client['nodes']] == [['127.0.0.1:' + str(p)] for p in range(24001,24007)]
        (out / 'original-t2-current.json').write_text(json.dumps(current, indent=2, sort_keys=True)+'\n')
        (out / 'owned-containers.json').write_text(json.dumps(owned, indent=2, sort_keys=True)+'\n')
        result.update(status='PASS_REAL_ISOLATED_NETWORK_HEALTH_NOT_PEER_ACCEPTANCE',
                      originalFailureReceiptSHA256=digest(original),
                      normalization='Only order of Docker inspect mount-array rows and container rows; every field and entry must remain equal',
                      oldT2AllFieldsUnchanged=True, actualNativeNetcheckHealthy=True,
                      macPublicNodeconfSHA256=digest(public),
                      ownedContainerReceiptSHA256=digest(out/'owned-containers.json'),
                      sourceCommit=module.COMMIT, project=module.PROJECT)
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        result['finishedAt'] = time.time()
        (out / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        print(json.dumps(result), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())

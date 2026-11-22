import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zipfile

import argparse
parser = argparse.ArgumentParser(description='Replay only original peer evidence checks; no product tests.')
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--proof', type=Path, required=True)
parser.add_argument('--control-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
PROOF = args.proof.resolve()
SOURCE = args.control_root.resolve() / 'Tools/PinkhaNativeDerived/coherent_peers/contract.py'
spec = importlib.util.spec_from_file_location('qualified_peer_contract', SOURCE)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
checks = []

def check(name, value):
    if not value:
        raise AssertionError(name)
    checks.append(name)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(name):
    return json.loads((PROOF / name).read_bytes())

archive = args.archive.resolve()
check('original GitHub artifact digest', sha(archive) == 'baf78b78966cb46b29d9cbed47c51bab638ccf1d2f144a8ba43936792cb18a69')
with zipfile.ZipFile(archive) as z:
    check('39 distinct original files', len(z.namelist()) == len(set(z.namelist())) == 39)
    check('all original extracted bytes unchanged', all(z.read(n) == (PROOF / n).read_bytes() for n in z.namelist()))
r, b = read('receipt.json'), read('build.json')
check('source run and attempt', r['app_sha'] == b['app_sha'] == '7f42c6daf270f8e87f789ebc1491b4d8fcc74867'
      and r['run_id'] == b['run_id'] == '45033575598' and r['run_attempt'] == b['run_attempt'] == '1')
contract.validate_build(b, r['app_sha'], r['run_id'], r['run_attempt'])
check('exact coherent139 native build contract', True)
check('original build receipt bound', r['build_receipt_sha256'] == sha(PROOF / 'build.json'))
check('execution uses original fixture binary digest', r['binary_sha256'] == b['binary_sha256']
      and r['fixture_sha256'] == b['fixture_sha256'])
check('139 native sources unchanged through compile', read('native-source-before.json') == read('native-source-after.json')
      and len(read('native-source-before.json')) == 139)
control = read('build-control-source-before.json')
check('controller sources unchanged through build and execution', control == read('build-control-source-after.json') == read('peer-control-source-after.json'))
check('replayed decoder is exact tested source', control['Tools/PinkhaNativeDerived/coherent_peers/contract.py'] == sha(SOURCE))
check('no previous native test or protobuf regeneration', b['old_test_methods_executed'] == b['protobuf_generation_executed'] == r['old_test_methods_executed'] == 0)
check('three actual method passes no failures or skips', r['status'] == contract.PASS and r['actual_native_processes'] == r['actual_named_pass'] == 3 and r['actual_fail'] == r['actual_skip'] == 0)
check('all native commands completed', all(x['status'] == 'PASS_EXIT_0' for x in r['commands']) and all(x['status'] == 'PASS_EXIT_0' for x in b['commands']))
check('exact actual evidence files and hashes', set(r['evidence_export']['files']) == {str(x.relative_to(PROOF / 'actual')) for x in (PROOF / 'actual').rglob('*') if x.is_file()}
      and all(sha(PROOF / 'actual' / n) == h for n, h in r['evidence_export']['files'].items()))
check('original credential scan and owned cleanup passed', r['evidence_export']['status'] == 'PASS_EXACT_SYNTHETIC_SECRET_SCAN'
      and r['owned_cleanup'] == {'status': 'PASS', 'errors': []} and r['owned_data_cleanup'] == 'PASS')

a = read('actual/creator/ready.json')
raw_changes = a['raw_changes_sha256']
root_ids = set(raw_changes) - {a['change_id']}
check('one original private root and signed change', len(root_ids) == 1)
state = {'AccountID': a['account_id'], 'SpaceID': a['space_id'], 'DocumentID': a['object_id'],
         'BlockID': a['block_id'], 'RootID': next(iter(root_ids)), 'OperationID': a['operation_id'],
         'OperationSHA256': a['canonical_sha256'], 'ClaimID': a['claim_id'], 'ChangeID': a['change_id'],
         'RawChanges': dict(sorted(raw_changes.items())), 'Heads': a['heads']}
contract.validate_state(state)
state_bytes = json.dumps(state, separators=(',', ':'), ensure_ascii=False).encode()
check('exact public seed hash independently reconstructed', hashlib.sha256(state_bytes).hexdigest() == a['state_sha256'])
check('only account recovery key and public seed crossed stores', r['seed_files'] == ['account-key.private', 'state.json'])
check('two fresh independent stores and database inodes', r['independent_empty_roots'] is True and r['distinct_database_inodes'] is True)

rows = {}
for role, phase, name in [('creator', 'ready', 'ready'), ('recovered', 'ready', 'ready'),
                           ('recovered', 'offline', 'offline'), ('recovered', 'reopen', 'reopen')]:
    prefix = 'actual/' + role + '/' + name
    value, wire = read(prefix + '.json'), (PROOF / (prefix + '.pb')).read_bytes()
    contract.validate_report(value, phase, role, r['owner_nonce'], b, state, a['state_sha256'], wire)
    rows[(role, phase)] = value
    check(role + ' ' + phase + ': original protobuf identity, payload, provenance and scope', True)
contract.validate_pair(rows[('creator', 'ready')], rows[('recovered', 'ready')])
check('same signed variant on distinct simultaneous native peers', True)
check('all four successful raw responses identical', len({(PROOF / p).read_bytes() for p in
      ['actual/creator/ready.pb', 'actual/recovered/ready.pb', 'actual/recovered/offline.pb', 'actual/recovered/reopen.pb']}) == 1)
check('fresh recovered client never appended or primed ReadTarget', rows[('recovered', 'ready')]['active_append_count'] == 0
      and rows[('recovered', 'ready')]['read_target_count'] == 0)
check('actual daemon detach command succeeded', len([x for x in r['commands'] if x['name'] == 'detach-reader' and x['status'] == 'PASS_EXIT_0']) == 1)
check('detached native interface read is empty', rows[('recovered', 'offline')]['actual_ipv4'] == [])
check('cold native first private read has no retry', rows[('recovered', 'reopen')]['rpc_calls']['PinkhaTorahAuthorizedOperationRead'] == 1
      and rows[('recovered', 'reopen')]['actual_ipv4'] == [])
peers, cold = r['native_peers'], r['cold_process']
check('three distinct native host process identities', all(len({peers['creator'][k], peers['recovered'][k], cold[k]}) == 3
      for k in ['container_id', 'host_pid', 'namespace', 'sandbox_id']))
check('cold process keeps original recovered peer identity', cold['peer_id'] == peers['recovered']['peer_id'] != peers['creator']['peer_id'])

for key, role, initial, prefix in [('creator', 'creator', rows[('creator', 'ready')], ''),
                                 ('recovered', 'recovered', rows[('recovered', 'offline')], ''),
                                 ('reopened', 'recovered', rows[('recovered', 'reopen')], 'reopen-')]:
    base = 'actual/' + role + '/'
    final = read(base + prefix + 'final.json')
    wire = (PROOF / (base + prefix + 'stopped.pb')).read_bytes()
    log = (PROOF / (base + prefix + 'native.log')).read_text()
    contract.validate_final(final, wire, log, initial, reopened=(key == 'reopened'))
    result = r['native_results'][key]
    check(key + ': stopped denial has no payload; exactly one actual named PASS', True)
    check(key + ': every native call returned and original final/log hashes bound',
          result['final_sha256'] == sha(PROOF / (base + prefix + 'final.json'))
          and result['log_sha256'] == sha(PROOF / (base + prefix + 'native.log'))
          and result['passed'] == 1 and result['failed'] == result['skipped'] == 0)
check('full acceptance boundaries remain explicit', all(r[k] == v for k, v in contract.LIMITS.items()))

report = {'status': 'PASS_ORIGINAL_COHERENT_PEER_EVIDENCE_AUDIT', 'runID': 45033575598,
          'sourceCommit': r['app_sha'], 'artifactID': 14758218911, 'artifactSHA256': sha(archive),
          'originalFileCount': 39, 'checksPassed': len(checks), 'checksFailed': 0, 'checks': checks,
          'actualNativeProcesses': 3, 'actualNamedPasses': 3, 'actualFailures': 0, 'actualSkips': 0,
          'onlineReaderAuthorizedReadAttempts': rows[('recovered', 'ready')]['rpc_calls']['PinkhaTorahAuthorizedOperationRead'],
          'coldReaderAuthorizedReadAttempts': 1, 'successfulRawWireSHA256': a['wire_sha256'],
          'signedVariantSHA256': a['variant_sha256'], 'nativeBinarySHA256Reported': b['binary_sha256'],
          'nativeBinaryIndependentlyRehashed': False, 'productTestsRepeatedForAudit': 0,
          'limitations': ['Native executable was not archived; its digest is the checked runner build/execution receipt.',
                         'Docker inspection assertions are original controller observations, not a separately replayed live daemon.',
                         'Raw signed DAG changes are represented by hashes and native verification; this audit checks original response bytes and provenance, not independent signature replay.',
                         'Same-account devices only. Cross-account ACL transport, unknown offline revocation, mixed versions, iOS and physical iPad remain unproved.'],
          'acceptanceScope': contract.LIMITS}
output = args.output.resolve()
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'checksPassed', 'checksFailed', 'actualNativeProcesses',
                                      'actualNamedPasses', 'actualFailures', 'actualSkips', 'onlineReaderAuthorizedReadAttempts']}))

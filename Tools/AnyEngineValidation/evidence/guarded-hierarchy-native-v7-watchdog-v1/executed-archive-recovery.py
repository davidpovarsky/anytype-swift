"""Archive completed watchdog evidence; no process launch or native mutation."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT = Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
BUILD = ROOT / 'build/any-engine-port'
SOURCE = BUILD / 'guarded-hierarchy-native-v7-watchdog-v1'
TARGET = ROOT / 'Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v7-watchdog-v1'
ENGINE = BUILD / 'http-watchdog-engine-v4-20261119-215447-642343'
PROBE = BUILD / 'guarded-hierarchy-watchdog-components-v1'
CORRELATION_SHA = '5a8b4f10106be3a8661eacb08d8ebf577a91ae3484fbcc2d59a64975803e44ad'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def copy(source, relative, expected=None):
    if expected is not None and sha(source) != expected:
        raise RuntimeError('archive_source_pin_mismatch:' + str(source))
    destination = TARGET / relative
    if destination.exists():
        if sha(source) != sha(destination):
            raise RuntimeError('partial_archive_copy_mismatch:' + str(relative))
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha(source) != sha(destination):
        raise RuntimeError('archive_copy_hash_mismatch')

if not TARGET.exists() or (TARGET / 'checkpoint.json').exists():
    raise RuntimeError('only_unsealed_partial_archive_may_resume')
correlation = json.loads((SOURCE / 'correlation.json').read_text(encoding='utf8'))
if sha(SOURCE / 'correlation.json') != CORRELATION_SHA or correlation['passedCount'] != 13 or correlation['watchdogObservation']['actualActivations'] != 0:
    raise RuntimeError('exact_completed_watchdog_failure_required')
proof = json.loads((PROBE / 'result.json').read_text(encoding='utf8'))
if proof.get('status') != 'PASS_EXACT_SOURCE_COMPONENT_BUILD' or proof.get('unchangedTwentyAssertions') is not True:
    raise RuntimeError('source_bound_assertion_preserving_build_required')
TARGET.mkdir(parents=True, exist_ok=True)
for p in sorted(SOURCE.rglob('*')):
    if p.is_file():
        if p.name.endswith(('.exe', '.o', '.lib', '.dll')) or '.private.' in p.name or '.bak.' in p.name:
            raise RuntimeError('unexpected_runtime_archive_input')
        copy(p, p.relative_to(SOURCE))
for name in ('result.json', 'source-before.json', 'source-after.json', 'executed-builder.py',
             'executed-process-helper.py', 'Objects.LinkFileList', 'output-file-map.json',
             'Probe.arm-only.diff', 'reusable-watchdog-engine-v4.json', 'prepared.json',
             'build-receipt.json', 'AnyHTTPClient.watchdog-v4.diff'):
    copy(PROBE / name, Path('provenance/probe-build') / name)
for name in ('compile', 'wrap', 'link'):
    for p in sorted((PROBE / name).iterdir()):
        if p.is_file() and p.suffix in ('.log', '.json'):
            copy(p, Path('provenance/probe-build') / name / p.name)
for relative, expected in proof['diagnosticProbeInputs'].items():
    p = ROOT / relative
    copy(p, Path('provenance/ProbeSources') / p.name, expected)
for relative, expected in proof['sourceInputs'].items():
    copy(ROOT / relative, Path('provenance/CanonicalSources') / relative, expected)
trace = json.loads((ENGINE / 'reusable-watchdog-engine-v4.json').read_text(encoding='utf8'))
for name in ('reusable-watchdog-engine-v4.json', 'prepared.json', 'build-receipt.json',
             'AnyHTTPClient.watchdog-v4.diff', 'build.log'):
    copy(ENGINE / name, Path('provenance/engine-build') / name)
for name, expected in trace['copiedEngineSourceManifest'].items():
    copy(ENGINE / 'EngineSources' / name, Path('provenance/EngineSources') / name, expected)
engine_receipt = json.loads((ENGINE / 'build-receipt.json').read_text(encoding='utf8'))
for path_key, sha_key in (('runnerPath', 'runnerSHA256'), ('boundedRunnerPath', 'boundedRunnerSHA256')):
    p = ROOT / engine_receipt[path_key]
    copy(p, Path('provenance/engine-build') / p.name, engine_receipt[sha_key])
for name in ('launch_native_v7_watchdog_fixture.py', 'run_guarded_hierarchy_watchdog.py',
             'watchdog_python_control.py', 'collect_hierarchy_watchdog.py'):
    copy(BUILD / name, Path('provenance/runners') / name)
for name in ('native-document-metadata-v7-source.json', 'native-document-metadata-v7-any.patch',
             'native-document-metadata-v7-sdk.patch'):
    copy(ROOT / 'Tools/AnyEngineValidation/evidence' / name, Path('provenance/native-v7') / name)
for name in ('guarded-hierarchy-components-v1', 'guarded-hierarchy-components-v3'):
    p = BUILD / name
    for file in ('result.json', 'source-before.json', 'source-after.json'):
        copy(p / file, Path('provenance/earlier-producers') / name / file)
# Matching-toolchain source review; no claim that handler completion is a flush.
go = Path(r'C:\Users\DAVID\go\pkg\mod\golang.org\toolchain@v0.0.1-go1.27.1.windows-amd64')
if (go / 'VERSION').read_text().splitlines()[0] != 'go1.27.1':
    raise RuntimeError('matching_go_source_version_required')
server = go / 'src/net/http/server.go'
lines = server.read_text(encoding='utf8').splitlines()
review = {'scope': 'Read-only native final-flush boundary; matching embedded go1.27.1 toolchain source.',
    'goVersion': 'go1.27.1', 'sourcePath': str(server), 'sourceSHA256': sha(server),
    'nativeBinarySHA256': correlation['nativeBinarySHA256'],
    'observedBoundary': 'Echo access logging runs inside ServeHTTP after its handler returns. Go finishRequest is invoked after ServeHTTP returns; response and connection-buffer flushing therefore follow the access-log record.',
    'conclusion': 'Prompt native200 access completion does not prove socket delivery or Foundation completion. No native framing defect established.',
    'ranges': [{'firstLine': a, 'lastLine': b, 'source': '\n'.join(lines[a-1:b])} for a,b in ((377,424),(1650,1711),(2135,2150))]}
(TARGET / 'go-http-final-flush-review.json').write_text(json.dumps(review, indent=2) + '\n', encoding='utf8')
copy(BUILD / 'seal_hierarchy_watchdog_v1.py', 'executed-archive-sealer.py')
copy(Path(__file__), 'executed-archive-recovery.py')
(TARGET / 'archive-finalization-recovery.json').write_text(json.dumps({'originalArchiveJob':'job_e5d8eedb8c2d','archiveOnlyFailure':'UnicodeDecodeError reading UTF8 Go source with Windows cp1252 default','productRunRepeated':False,'existingCopiesComparedByteForByte':True,'failedSealerSHA256':sha(BUILD / 'seal_hierarchy_watchdog_v1.py')}, indent=2) + '\n', encoding='utf8')
files = {p.relative_to(TARGET).as_posix(): {'sha256':sha(p), 'bytes':p.stat().st_size}
         for p in sorted(TARGET.rglob('*')) if p.is_file()}
checkpoint = {'status':'FROZEN_FAILED_WATCHDOG_DIAGNOSTIC', 'createdAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'passedCount':13, 'requiredCount':20, 'failedAssertion':'guarded_bin_exact_retry_preserves_native_version',
    'originalHTTPRequestsCompleted':1131, 'originalHTTPAwaitErrors':0, 'watchdogActivations':0,
    'sameProcessControlRequests':0, 'independentPythonControlRequests':0,
    'transportFailureResolved':False, 'nativeOverlayUnchanged':True,
    'nativeBinarySHA256':correlation['nativeBinarySHA256'], 'nativeManifestSHA256':correlation['nativeManifestSHA256'],
    'probeSHA256':correlation['probeSHA256'], 'files':files,
    'historicalBeforeAfterVersionsAvailable':False,
    'limits':['Exact failed equality preserved; historical before/after native version values were not emitted.',
              'No watchdog activation occurred, so this run does not isolate the earlier intermittent transport failure.',
              'No private process handshake/log, wallet/recovery material or response payload is archived.']}
path=TARGET / 'checkpoint.json'
path.write_text(json.dumps(checkpoint, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status':checkpoint['status'], 'passedCount':13, 'requiredCount':20, 'files':len(files),
                  'checkpointSHA256':sha(path), 'prefix':TARGET.relative_to(ROOT).as_posix()}))

#!/usr/bin/env python3
"""Bounded portable controls of the exact new Foundation demand barrier."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from datetime import datetime, timezone

CASES = [
    'no-demand-is-not-ready', 'forwarded-demand-admits',
    'terminal-before-acknowledgment-wins', 'terminal-after-demand-invalidates',
    'cancelled-waiter-closes-readiness', 'pending-wait-receives-demand',
    'one-of-two-terminated-does-not-admit', 'concurrent-end-remains-terminal',
]
MODEL = 'Anytype/Sources/ApplicationLayer/AppCoordinator/ApplicationCoordinatorViewModel.swift'
def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.output.resolve()
    out.mkdir(exist_ok=False)
    result = {'schema': 1, 'status': 'FAIL', 'scope': 'EXACT_FOUNDATION_BARRIER_ONLY_NOT_COMBINE_UI_AUTH_OR_NATIVE',
              'base': 'd1ca51352734bd21a4943e7e094ac3ae95519c1e', 'commands': [],
              'required_cases': CASES, 'passed': [], 'apple_execution': False,
              'combine_execution': False, 'ui_execution': False, 'native_account_execution': False}
    def run(label, argv, limit):
        stdout = out / (label + '.stdout')
        stderr = out / (label + '.stderr')
        timed = False
        with stdout.open('wb') as a, stderr.open('wb') as b:
            child = subprocess.Popen(argv, cwd=repo, stdout=a, stderr=b, start_new_session=True)
            try: code = child.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
                code = child.returncode
        result['commands'].append({'label': label, 'argv': argv, 'returncode': code,
            'timed_out': timed, 'child_reaped': child.poll() is not None,
            'stdout_sha256': sha(stdout.read_bytes()), 'stderr_sha256': sha(stderr.read_bytes())})
        return code, stdout.read_text()
    try:
        source = (repo / MODEL).read_bytes()
        text = source.decode()
        a = text.index('final class OriginalApplicationConsumerDemand:')
        b = text.index('/// An observation-only forwarder', a)
        exact = text[a:b]
        assert 'Publisher' not in exact.replace('AsyncPublisher', '')
        harness = Path(__file__).with_name('ReadinessControls.swift').read_bytes()
        combined = 'import Foundation\nimport Dispatch\n\n' + exact + '\n' + harness.decode()
        path = out / 'ExactFoundationReadinessControls.swift'
        path.write_text(combined)
        result.update(model_sha256=sha(source), extracted_original_bytes=len(exact.encode()),
                      extracted_original_sha256=sha(exact.encode()), harness_sha256=sha(harness),
                      combined_sha256=sha(path.read_bytes()), source_replacements=[],
                      excluded_real_combine_forwarders='Retained in original source; Apple Combine controls remain required.')
        (out / 'EXTRACTION.json').write_text(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2)+'\n')
        assert run('swift-version', ['swift','--version'],20)[0] == 0
        assert run('unprojected-model-parse', ['swiftc','-frontend','-parse',str(repo/MODEL)],30)[0] == 0
        binary = out / 'readiness-controls'
        assert run('portable-compile', ['swiftc','-swift-version','6','-parse-as-library',str(path),'-o',str(binary)],90)[0] == 0
        result['binary_sha256'] = sha(binary.read_bytes())
        for i,name in enumerate(CASES):
            code,stdout = run('case-'+str(i+1),[str(binary),name],15)
            assert code == 0 and stdout.startswith('PASS '+name+' assertions='), name
            result['passed'].append({'name':name,'actual_output':stdout.strip()})
        assert len(result['passed']) == len(CASES)
        result['status'] = 'PASS'
    except BaseException as error:
        result['error_type']=type(error).__name__;result['error']=str(error)
        raise
    finally:
        result['finished_utc']=datetime.now(timezone.utc).isoformat()
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2))

if __name__ == '__main__': main()

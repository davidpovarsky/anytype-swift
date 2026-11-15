"""Verify actual OS 27/Xcode 27 hardware before any UI acceptance build."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


def select_pairs(inventory):
    runtimes = [r for r in inventory['runtimes'] if r.get('isAvailable')
                and r.get('version', '').split('.')[0] == '27' and 'iOS' in r.get('name', '')]
    # Prefer stable, ordinary iPhone+iPad support over an experimental Duo-only runtime.
    runtimes.sort(key=lambda r: tuple(map(int, r['version'].split('.'))))
    for runtime in runtimes:
        supported = {d['identifier'] if isinstance(d, dict) else d
                     for d in runtime.get('supportedDeviceTypes', [])}
        choices = {}
        for kind in ['iphone', 'ipad']:
            candidates = [d for d in inventory['devicetypes']
                          if d['name'].startswith('iPhone' if kind == 'iphone' else 'iPad')
                          and 'Duo' not in d['name']
                          and (not supported or d['identifier'] in supported)]
            if candidates:
                choices[kind] = candidates[0]
        if len(choices) == 2:
            return runtime, choices
    raise RuntimeError('Actual available OS27 runtime supporting BOTH ordinary iPhone and iPad is required')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='FAIL', phase='PREFLIGHT', ui_tests_executed=0,
                   started_at=datetime.now(timezone.utc).isoformat(),
                   run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                   source_sha=os.environ.get('GITHUB_SHA'))
    try:
        if platform.system() != 'Darwin' or platform.machine() != 'arm64':
            raise RuntimeError('Actual Apple silicon Mac is required, not a Windows or Intel substitute')
        if sys.version_info < (3, 12):
            raise RuntimeError('Python3.12 or newer is required for verified artifact handling')
        xcode = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
        if not re.match(r'Xcode 27(?:\.|\s)', xcode):
            raise RuntimeError('Actual Xcode27 is required: ' + xcode)
        inventory = json.loads(subprocess.check_output(['xcrun', 'simctl', 'list', '--json']))
        (args.evidence / 'simulator-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
        runtime, devices = select_pairs(inventory)
        selected = {}
        for kind, device in devices.items():
            name = 'Pinkha-UI27-' + str(receipt['run_id']) + '-' + kind
            udid = subprocess.check_output(['xcrun', 'simctl', 'create', name, device['identifier'],
                                            runtime['identifier']], text=True).strip()
            if not re.fullmatch(r'[A-Fa-f0-9-]{36}', udid):
                raise RuntimeError('Invalid created disposable simulator identity')
            selected[kind] = dict(udid=udid, device=device, runtime=runtime, name=name)
        receipt.update(status='PREFLIGHT_PASS_UI_NOT_RUN', xcode=xcode,
                       host_architecture=platform.machine(), selected=selected, python=sys.version,
                       developer_dir=os.environ.get('DEVELOPER_DIR'),
                       swift=subprocess.check_output(['swift', '--version'], text=True).strip(),
                       sdks=subprocess.check_output(['xcodebuild', '-showsdks'], text=True).strip())
        with open(os.environ['GITHUB_ENV'], 'a') as output:
            for kind, selection in selected.items():
                output.write('PINKHA_UI27_' + kind.upper() + '_UDID=' + selection['udid'] + '\n')
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    (args.evidence / 'preflight.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    return 0 if receipt['status'] == 'PREFLIGHT_PASS_UI_NOT_RUN' else 1


if __name__ == '__main__':
    raise SystemExit(main())

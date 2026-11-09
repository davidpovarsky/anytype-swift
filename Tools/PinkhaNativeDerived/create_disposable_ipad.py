"""Create and boot a fresh iPad on a compatible installed iOS runtime."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=True)
data = json.loads(subprocess.check_output(['xcrun', 'simctl', 'list', '--json']))
(args.evidence / 'simulator-inventory.json').write_text(json.dumps(data, indent=2) + '\n')
runtimes = sorted(
    (r for r in data['runtimes'] if r.get('isAvailable') and 'iOS' in r['name']),
    key=lambda r: tuple(map(int, re.findall(r'\d+', r.get('version') or r['name']))), reverse=True
)
name = 'Pinkha-Native-Derived-' + os.environ['GITHUB_RUN_ID']
attempts = []
selected = None
for runtime in runtimes:
    supported = {d['identifier'] if isinstance(d, dict) else d for d in (runtime.get('supportedDeviceTypes') or [])}
    for device in data['devicetypes']:
        if 'iPad Pro' not in device['name'] or (supported and device['identifier'] not in supported):
            continue
        created = subprocess.run(['xcrun', 'simctl', 'create', name, device['identifier'], runtime['identifier']], capture_output=True, text=True)
        if created.returncode == 0:
            selected = (created.stdout.strip(), runtime, device)
            break
        attempts.append(dict(runtime=runtime['identifier'], device=device['identifier'], error=created.stderr.strip()))
    if selected:
        break
if not selected:
    (args.evidence / 'simulator-failures.json').write_text(json.dumps(attempts, indent=2) + '\n')
    raise RuntimeError('No compatible installed iPad/iOS simulator pair')
udid, runtime, device = selected
subprocess.run(['xcrun', 'simctl', 'boot', udid], check=True)
subprocess.run(['xcrun', 'simctl', 'bootstatus', udid, '-b'], check=True)
with open(os.environ['GITHUB_ENV'], 'a') as stream:
    stream.write('PINKHA_NATIVE_IPAD_UDID=' + udid + '\n')
(args.evidence / 'disposable-simulator.json').write_text(json.dumps(dict(udid=udid, name=name, device=device, runtime=runtime, attempts=attempts), indent=2) + '\n')
print(json.dumps(dict(udid=udid, runtime=runtime['name'], device=device['name'])))

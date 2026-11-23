import hashlib, json
from pathlib import Path
packet = Path('docs/pinkha/torah-integration/evidence/original-editor-signed-consumer-20261123')
receipt = json.loads((packet / 'FOCUSED_CONTROLS.json').read_bytes())
assert receipt['status'] == 'PASS'
assert receipt['tests_run'] == len(receipt['passed_ids']) == len(set(receipt['passed_ids'])) == 12
assert sorted(receipt['passed_ids']) == sorted(receipt['started_ids']) == sorted(receipt['expected_ids'])
assert not receipt['failures'] and not receipt['errors'] and not receipt['skipped']
for path, expected in receipt['source_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
for path, expected in receipt['log_sha256'].items():
    assert hashlib.sha256((packet / path).read_bytes()).hexdigest() == expected, path
print('Retained 12 source-bound controls; no test replay and no Apple runtime credit.')

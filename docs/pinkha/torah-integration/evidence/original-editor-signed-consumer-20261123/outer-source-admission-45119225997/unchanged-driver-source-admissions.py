require(command('control-head', ['git', 'rev-parse', 'HEAD']) == current['control_sha'], 'Control source differs')
command('producer-ancestor', ['git', 'merge-base', '--is-ancestor', producer['source_sha'], 'HEAD'])
delta = command('control-diff', ['git', 'diff', '--name-only', producer['source_sha'], 'HEAD']).splitlines()
require(all(path in CONTROL_FILES or path.startswith(PACKET) for path in delta), 'Unowned product source changed')
require(not command('control-status', ['git', 'status', '--porcelain', '--untracked-files=all', '--', 'Tools', '.github']),
        'Uncommitted control input')
for path, expected in inputs['source_trees'].items():
    require(command('tree-' + path.replace('/', '-'), ['git', 'rev-parse', 'HEAD:' + path]) == expected,
            'Original application/module tree changed')
for path in ['Anytype.xcodeproj', 'OriginalEditorFramework']:
    require(not command('original-' + path, ['git', 'diff', '--name-only', producer['source_sha'], 'HEAD', '--', path]),
            'Original project or facade changed')
control_packet = root / PACKET
controls = json.loads((control_packet / 'METADATA_CONTROLS.json').read_bytes())
require(controls['status'] == 'PASS' and controls['tests_run'] == len(set(controls['passed_ids'])) == 6
        and controls['failed'] == controls['errors'] == controls['skipped'] == 0,
        'Exact upload metadata controls did not pass')
for relative, expected in controls['source_sha256'].items():
    require(digest(root / relative) == expected, 'Upload proof control source differs: ' + relative)
for relative, expected in controls['log_sha256'].items():
    require(digest(control_packet / relative) == expected, 'Upload proof control log differs: ' + relative)
capture_controls = json.loads((control_packet / 'RAW_CAPTURE_CONTROLS.json').read_bytes())
require(capture_controls['status'] == 'PASS'
        and capture_controls['tests_run'] == len(set(capture_controls['passed_ids'])) == 2
        and capture_controls['failed'] == capture_controls['errors'] == capture_controls['skipped'] == 0,
        'Raw original log capture controls did not pass')
for relative, expected in capture_controls['source_sha256'].items():
    require(digest(root / relative) == expected, 'Raw capture source differs: ' + relative)
for relative, expected in capture_controls['log_sha256'].items():
    require(digest(control_packet / relative) == expected, 'Raw capture log differs: ' + relative)
role_controls = json.loads((control_packet / 'framework-role-admission/FRAMEWORK_ROLE_CONTROLS.json').read_bytes())
require(role_controls['status'] == 'PASS'
        and role_controls['tests_run'] == len(set(role_controls['passed_ids'])) == 6
        and role_controls['failed'] == role_controls['errors'] == role_controls['skipped'] == 0,
        'Original framework role controls did not pass')
for relative, expected in role_controls['source_sha256'].items():
    require(digest(root / relative) == expected, 'Framework role control source differs: ' + relative)
for relative, expected in role_controls['log_sha256'].items():
    require(digest(control_packet / 'framework-role-admission' / relative) == expected,
            'Framework role control log differs: ' + relative)

python3 - <<'PY'
import ast, hashlib, json, os
from pathlib import Path
packet = Path(os.environ['CONTINUATION_PACKET'])
result = json.loads((packet / 'controls/RESULT.json').read_bytes())
assert result['status'] == 'PASS_NEW_CONTINUATION_BOUNDARY_CONTROLS'
tree = ast.parse(Path('Tools/OriginalEditor/runtime_continuation_controls.py').read_text())
expected = [method.name for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'ContinuationBoundaries'
            for method in item.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')]
assert result['tests_run'] == len(result['expected_ids']) == len(expected) == 24
assert sorted(result['expected_ids']) == sorted(expected)
assert sorted(result['passed_ids']) == sorted(result['expected_ids'])
assert len(set(result['passed_ids'])) == result['tests_run']
assert not result['failures'] and not result['errors'] and not result['skipped']
binding = json.loads((packet / 'controls/SOURCE_BINDING.json').read_bytes())
assert hashlib.sha256((packet / 'controls/RESULT.json').read_bytes()).hexdigest() == binding['executed_result_sha256']
assert set(binding['files']) == set(result['source_sha256'])
instrumented = packet / 'instrumented'
runner_inverse = json.loads((instrumented / 'RUNNER_EXACT_INVERSE.json').read_bytes())
for path, commitment in result['source_sha256'].items():
    item = binding['files'][path]
    raw = Path(item['current_path']).read_bytes()
    if item['current_path'] == 'Tools/OriginalEditor/run_runtime_continuation.py':
        assert hashlib.sha256(raw).hexdigest() == runner_inverse['current_sha256']
        current_text = raw.decode()
        lines = current_text.splitlines(keepends=True)
        for edit in reversed(runner_inverse['edits']):
            assert lines[edit['current_start']:edit['current_end']] == edit['current_lines']
            lines[edit['current_start']:edit['current_end']] = edit['previous_lines']
        previous_text = ''.join(lines)
        def functions(source):
            return {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != 'main'}
        assert functions(current_text) == functions(previous_text)
        assert len(functions(previous_text)) == 10
        raw = previous_text.encode()
        assert hashlib.sha256(raw).hexdigest() == runner_inverse['previous_sha256']
    assert hashlib.sha256(raw).hexdigest() == item['current_sha256'], path
    if 'inverse' in item:
        inverse = item['inverse']
        assert raw.count(inverse['current'].encode()) == inverse['count'] == 1
        raw = raw.replace(inverse['current'].encode(), inverse['executed'].encode())
    assert hashlib.sha256(raw).hexdigest() == commitment == item['executed_sha256'], path
for row in json.loads((packet / 'ORIGINAL_HELPER_BINDINGS.json').read_bytes()):
    source = Path('Tools/OriginalEditor') / row['path']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == row['sha256'], row['path']
focused = json.loads((instrumented / 'controls/RESULT.json').read_bytes())
assert focused['status'] == 'PASS_NEW_INSTRUMENTED_RUNTIME_BOUNDARIES'
focused_source = instrumented / 'controls/instrumented_runtime_controls.py'
focused_tree = ast.parse(focused_source.read_text())
focused_ids = [method.name for node in focused_tree.body
               if isinstance(node, ast.ClassDef) and node.name == 'InstrumentedRuntimeBoundaries'
               for method in node.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')]
assert len(focused_ids) == len(set(focused_ids)) == focused['tests_run'] == 14
assert sorted(focused_ids) == sorted(focused['expected_ids']) == sorted(focused['started_ids']) == sorted(focused['passed_ids'])
assert not focused['errors'] and not focused['failures'] and not focused['skipped']
assert focused['old_control_bodies_replayed'] == focused['apple_commands_executed'] == 0
routes = {name: Path('Tools/OriginalEditor') / name for name in [
    'run_runtime_continuation.py', 'runtime_continuation_observation.py', 'runtime_continuation_process.py',
    'product_inventory.py', 'framework_profile.py', 'pbx_source.py']}
routes['instrumented_runtime_controls.py'] = focused_source
assert {Path(row['path']).name for row in focused['source_inputs']} == set(routes)
assert len(focused['source_inputs']) == len(routes)
for row in focused['source_inputs']:
    assert hashlib.sha256(routes[Path(row['path']).name].read_bytes()).hexdigest() == row['sha256']
Path('build').mkdir(exist_ok=True)
Path('build/runtime-continuation-control-admission.json').write_text(json.dumps({
    'status': 'SOURCE_BOUND_NEW_CONTROLS_RETAINED_WITHOUT_REPLAY',
    'control_sha': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
    'retained_new_control_count': result['tests_run'], 'prior_source_controls_replayed': 0,
    'retained_instrumented_control_count': focused['tests_run'],
    'new_control_bodies_replayed': 0,
    'result_sha256': hashlib.sha256((packet / 'controls/RESULT.json').read_bytes()).hexdigest(),
}, indent=2, sort_keys=True) + '\n')
PY

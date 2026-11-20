"""Read only: verify sealed preparation/Git bytes and declarations; never run tests."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

def require(value, message):
    if not value:
        raise RuntimeError(message)

def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    index = json.loads((here / 'PUBLISH_INDEX.json').read_bytes())
    for row in index['files']:
        path = here / row['path']
        require(path.is_file() and not path.is_symlink(), 'Missing/aliased packet file: ' + row['path'])
        raw = path.read_bytes()
        require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
                and blob(raw) == row['git_blob'], 'Packet bytes differ: ' + row['path'])
    inverse = json.loads((here / 'SOURCE_INVERSE.json').read_bytes())
    changes = json.loads((here / 'EXACT_REVERSE_EDITS.json').read_bytes())
    proof = json.loads((here / 'SOURCE_TREE_PROOF.json').read_bytes())
    declared = json.loads((here / 'STATIC_TEST_MEMBERSHIP.json').read_bytes())
    source, parent = inverse['source_commit'], inverse['base_sha']
    inputs = json.loads((here / 'SOURCE_INPUTS.json').read_bytes())
    def git(*arguments):
        return subprocess.check_output(['git', '-C', str(args.repository), *arguments])
    require(inputs['count'] == len(inputs['inputs']) == 30, 'Execution input closure differs')
    for row in inputs['inputs']:
        raw = git('show', source + ':' + row['path'])
        require(blob(raw) == row['git_blob'] and len(raw) == row['bytes']
                and hashlib.sha256(raw).hexdigest() == row['sha256'], 'Execution input bytes differ: ' + row['path'])
    require(git('rev-parse', source + '^').decode().strip() == parent, 'Source parent differs')
    require(git('rev-parse', source + '^{tree}').decode().strip() == proof['source_tree'], 'Source tree differs')
    def leaves(commit):
        result = {}
        for record in git('ls-tree', '-r', '-z', commit).split(b'\0'):
            if not record:
                continue
            metadata, path = record.split(b'\t', 1)
            mode, kind, sha = metadata.decode().split()
            result[path.decode()] = {'mode': mode, 'type': kind, 'sha': sha}
        return result
    before, after = leaves(parent), leaves(source)
    actual_changes = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    require(actual_changes == set(inverse['files']), 'Source path/mode closure differs')
    for path, row in inverse['files'].items():
        raw = git('show', source + ':' + path)
        require(blob(raw) == row['candidate_blob'] and len(raw) == row['candidate_bytes']
                and hashlib.sha256(raw).hexdigest() == row['candidate_sha256'], 'Source bytes differ: ' + path)
        if row['new_file']:
            require(path not in before and path in changes['new_files'], 'Unexpected new file')
            continue
        old = git('show', parent + ':' + path)
        require(blob(old) == row['base_blob'], 'Base blob differs: ' + path)
        restored = raw.decode()
        for edit in changes['files'][path]:
            require(restored.count(edit['old']) == edit['count'], 'Inverse occurrence differs: ' + path)
            restored = restored.replace(edit['old'], edit['new'])
        require(restored.encode() == old, 'Whole inverse differs: ' + path)
    for row in proof['protected_trees']:
        require(git('rev-parse', source + ':' + row['path']).decode().strip() == row['sha']
                and git('rev-parse', parent + ':' + row['path']).decode().strip() == row['sha'],
                'Protected product tree differs')
    ids = []
    for path, row in declared['files'].items():
        raw = git('show', source + ':' + path)
        require(blob(raw) == row['blob'], 'Test source blob differs: ' + path)
        module = Path(path).stem
        parsed = ast.parse(raw, filename=path)
        direct = []
        for owner in parsed.body:
            if not isinstance(owner, ast.ClassDef):
                continue
            if [ast.unparse(base) for base in owner.bases] != ['unittest.TestCase']:
                continue
            for method in owner.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith('test_'):
                    direct.append(module + '.' + owner.name + '.' + method.name)
        all_methods = [node for node in ast.walk(parsed)
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')]
        require(len(all_methods) == len(direct), 'Test outside actual direct TestCase scope: ' + path)
        require(sorted(direct) == sorted(row['method_ids']), 'Test declaration membership differs: ' + path)
        ids.extend(direct)
    require(len(ids) == len(set(ids)) == 143 and sorted(ids) == declared['ids'],
            'The exact 143 source declarations differ')
    runner = ast.parse(git('show', source + ':Tools/OriginalEditor/run_source_controls.py'))
    expected = next(ast.literal_eval(node.value) for node in runner.body
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EXPECTED_IDS' for t in node.targets))
    require(list(expected) == sorted(ids), 'Dynamic qualifier identity manifest differs')
    print(json.dumps({'status': 'VERIFIED_PREPARATION_BYTES_AND_DECLARATIONS_ONLY',
                      'source_commit': source, 'source_tree': proof['source_tree'],
                      'sealed_files': len(index['files']), 'source_paths': len(actual_changes),
                      'declarations': 143, 'new_controls_executed': 0,
                      'apple_execution': 'NOT_RUN'}, sort_keys=True))

if __name__ == '__main__':
    main()

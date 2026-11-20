"""Exact original43 plus six actual document-constructor Apple methods."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import original_editor_profile as original

BRANCH = 'codex/otzaria-original-document-constructor49-reviewed-20261120'
REPOSITORY = 'davidpovarsky/anytype-swift'
WORKFLOW = '.github/workflows/pinkha-original-document-constructor.yml'
MANIFEST_PATH = Path(__file__).with_name('original_document_constructor_profile.json')
SUITE = 'PreparedDocumentConstructorTests'

def require(value, message):
    if not value:
        raise ValueError(message)

def canonical(path):
    return path.read_bytes().replace(b'\r\n', b'\n')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    require(data['profile'] == 'original-constructors' and data['required_methods'] == 49,
            'Unreviewed constructor profile')
    require(digest(canonical(Path(original.__file__))) == data['original_profile_module_sha256']
            and digest(canonical(original.MANIFEST_PATH)) == data['original_profile_manifest_sha256'],
            'Original43 validator or manifest changed')
    old = original.manifest()
    require(data['original_suites'] == old['suites'] and data['heart'] == old['heart'],
            'Original43 method/source or Heart contract changed')
    item = data['constructor_suite']
    require(item['name'] == SUITE and len(item['methods']) == len(set(item['methods'])) == 6,
            'Constructor method inventory changed')
    require(sum(len(x['methods']) for x in old['suites'].values()) == 43,
            'Original method inventory changed')
    require(set(data['application_trees']) == {'AnyTypeTests', 'Anytype', 'Anytype.xcodeproj', 'AnytypeTests', 'Modules'},
            'Application tree scope changed')
    require(set(data['constructor_sources']) == {
        'Anytype/Sources/Models/Documents/Document/BaseDocument.swift',
        'Anytype/Sources/Models/Documents/Events/DocumentViewModelSetter.swift'},
        'Constructor source scope changed')
    return data

def suite_counts():
    data = manifest()
    return {**original.suite_counts(), SUITE: len(data['constructor_suite']['methods'])}

def require_identity(head, expected_sha, branch, expected_branch, run_id, attempt):
    require(branch == expected_branch == BRANCH, 'Wrong constructor acceptance branch')
    require(re.fullmatch(r'[0-9a-f]{40}', expected_sha or '') and head == expected_sha,
            'Constructor source differs from actual workflow checkout')
    require(re.fullmatch(r'[1-9][0-9]*', run_id or '')
            and re.fullmatch(r'[1-9][0-9]*', attempt or ''), 'Missing constructor run/attempt')

def require_workflow_environment(environment):
    require(environment.get('GITHUB_EVENT_NAME') == 'push', 'Constructor acceptance requires exact push route')
    require(environment.get('GITHUB_REPOSITORY') == REPOSITORY, 'Wrong constructor repository')
    require(environment.get('GITHUB_REF') == 'refs/heads/' + BRANCH, 'Wrong constructor workflow ref')
    require(environment.get('GITHUB_WORKFLOW_REF') == REPOSITORY + '/' + WORKFLOW + '@refs/heads/' + BRANCH,
            'Wrong constructor workflow path/ref')

def git(app, *args):
    return subprocess.check_output(['git', '-C', str(app), *args]).decode('utf-8').strip()

def validate_constructor_declarations(text, expected):
    require(re.search(r'@MainActor\s+final\s+class\s+' + SUITE + r'\s*:\s*XCTestCase\s*\{', text),
            'Original XCTest constructor class is missing')
    declarations = re.findall(r'\bfunc\s+(test\w+)\s*\(([^)]*)\)', text)
    require(len(declarations) == len(expected) == 6
            and {name for name, _ in declarations} == set(expected)
            and len({name for name, _ in declarations}) == len(declarations),
            'Constructor XCTest names/count changed')
    require(all(not parameters.strip() for _, parameters in declarations),
            'Constructor XCTest parameterization changed')
    return {SUITE + '/' + name for name, _ in declarations}

def expected_methods(app):
    app = app.resolve()
    data = manifest()
    for path, expected in data['application_trees'].items():
        require(git(app, 'rev-parse', 'HEAD:' + path) == expected,
                'Constructor application source tree changed: ' + path)
    for path in ('Tools/Hanlin/original_editor_profile.py', 'Tools/Hanlin/original_editor_profile.json',
                 'Tools/Hanlin/original_document_constructor_profile.py',
                 'Tools/Hanlin/original_document_constructor_profile.json'):
        require(subprocess.check_output(['git', '-C', str(app), 'show', 'HEAD:' + path])
                == canonical(app / path), 'Profile runtime differs from actual Git checkout: ' + path)
    require(Path(__file__).resolve() == app / 'Tools/Hanlin/original_document_constructor_profile.py'
            and Path(original.__file__).resolve() == app / 'Tools/Hanlin/original_editor_profile.py',
            'Imported profile runtime is outside actual checkout')
    tracked = git(app, 'ls-files', '-z').split('\0')

    def checked_source(path, expected_hash):
        require([p for p in tracked if p.casefold() == path.casefold()] == [path],
                'Missing or case-colliding reviewed constructor source: ' + path)
        source = app / path
        require(source.is_file() and not source.is_symlink(), 'Missing original synchronized source: ' + path)
        raw = canonical(source)
        require(digest(raw) == expected_hash
                and digest(subprocess.check_output(['git', '-C', str(app), 'show', 'HEAD:' + path])) == expected_hash,
                'Constructor source bytes differ from reviewed Git input: ' + path)
        return raw

    for path, expected in data['constructor_sources'].items():
        checked_source(path, expected)
    methods, files = set(), {}
    for suite, item in data['original_suites'].items():
        raw = checked_source(item['path'], item['sha256'])
        methods.update(original.validate_declarations(raw.decode('utf-8'), suite, item['methods']))
        files[item['path']] = digest((app / item['path']).read_bytes())
    item = data['constructor_suite']
    raw = checked_source(item['path'], item['sha256'])
    methods.update(validate_constructor_declarations(raw.decode('utf-8'), item['methods']))
    files[item['path']] = digest((app / item['path']).read_bytes())
    require(len(methods) == 49 and len(files) == 8, 'Incomplete actual constructor selection')
    return methods, files

def validate_execution(tree, expected):
    data = manifest()
    old_expected = {suite + '/' + method for suite, item in data['original_suites'].items()
                    for method in item['methods']}
    new_expected = {SUITE + '/' + method for method in data['constructor_suite']['methods']}
    require(expected == old_expected | new_expected and len(expected) == 49,
            'Execution is not the complete original43 plus new6 selection')
    nodes = []
    def visit(value):
        if isinstance(value, dict):
            if value.get('nodeType') == 'Test Case':
                nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(tree)
    require(len(nodes) == 49, 'Missing or extra constructor execution nodes')
    old_nodes, new_nodes, seen = [], [], set()
    for node in nodes:
        identifier = node.get('nodeIdentifier')
        matches = [name for name in expected if identifier in {
            name + '()', 'AnytypeTests/' + name + '()',
            *({name, 'AnytypeTests/' + name} if name in new_expected else set())}]
        require(len(matches) == 1 and matches[0] not in seen and node.get('result') == 'Passed',
                'Unrecognized, repeated or nonpassing constructor method')
        seen.add(matches[0])
        (old_nodes if matches[0] in old_expected else new_nodes).append(node)
    require(seen == expected, 'Incomplete constructor methods')
    # These are the untouched actual original nodes, not a fabricated per-scope
    # aggregate or substituted execution result.
    old_result = original.validate_execution({'testNodes': old_nodes}, old_expected)
    def descendant(value):
        require(isinstance(value, dict) and value.get('nodeType') in {'Repetition', 'Test Case Run'}
                and value.get('result') == 'Passed', 'Unreviewed constructor execution descendant')
        children = value.get('children', [])
        require(isinstance(children, list), 'Malformed constructor execution descendants')
        for child in children:
            descendant(child)
    for node in new_nodes:
        children = node.get('children', [])
        require(isinstance(children, list), 'Malformed constructor method descendants')
        for child in children:
            descendant(child)
    return {'actual_method_count': 49, 'declared_case_count': 49,
            'original43': old_result, 'actual_constructor_methods': sorted(new_expected),
            'scope': 'Original43 components plus actual BaseDocument/DocumentViewModelSetter constructor/projection methods; no account, object-open or mounted UI'}

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--expected-app-branch', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    app = args.app.resolve()
    require_workflow_environment(os.environ)
    require_identity(git(app, 'rev-parse', 'HEAD'), os.environ.get('GITHUB_SHA'),
                     git(app, 'branch', '--show-current'), args.expected_app_branch,
                     os.environ.get('GITHUB_RUN_ID'), os.environ.get('GITHUB_RUN_ATTEMPT'))
    require(not git(app, 'diff', '--name-only', 'HEAD'), 'Tracked source changed before constructor gate')
    methods, files = expected_methods(app)
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'status': 'SOURCE_SELECTION_PASS_APPLE_NOT_RUN', 'source_sha': os.environ['GITHUB_SHA'],
               'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
               'methods': sorted(methods), 'test_source_sha256': files,
               'constructor_source_sha256': manifest()['constructor_sources'],
               'profile_manifest_sha256': digest(MANIFEST_PATH.read_bytes()), 'ui_executed': 0}
    (args.evidence / 'original-constructors-selection.json').write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()

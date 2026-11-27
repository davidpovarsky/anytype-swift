#!/usr/bin/env python3
"""Local byte-only assembly. Never imports a runner or invokes a toolchain."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
BASE = '9f0cbdffbda45520124ee1f0b50961641c5c49b1'
PRODUCT = '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'
CORE = '26beca175d64a4d34e3567f2bbb4bf308d714478'
PRIOR = WORK / 'wave2-property-unicode-audit/component-preparation/whole-source-intake.json'
RENAME = WORK / 'interfaces_work/hierarchy-title-exact'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Do not overwrite changed source: ' + str(path)
    else:
        path.write_bytes(raw)


def json_save(path, value):
    save(path, (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode())


directory_entries = {}
for name in ('integration-directory', 'engine-directory', 'kit-hierarchy-directory',
             'kit-editor-directory', 'kit-torah-directory', 'core-directory'):
    path = HERE / 'primary' / (name + '.response.json')
    response = json.loads(path.read_text())
    assert not response.get('isError', False)
    for row in json.loads(response['structuredContent']['content']):
        if row['type'] == 'file':
            directory_entries[row['path']] = (row, ref(path))


def primary_file(name):
    path = HERE / 'primary' / (name + '.response.json')
    response = json.loads(path.read_text())
    assert not response.get('isError', False)
    value = response['structuredContent']
    assert value['encoding'] == 'utf-8'
    raw = value['content'].encode('utf-8')
    assert blob(raw) == value['sha'], name
    return raw, value, ref(path)


rows = []
prior = json.loads(PRIOR.read_text())
modules = {'TorahInspectorCore', 'PinkhaKit', 'PinkhaAnyEngine', 'PinkhaAnyIntegration'}
for old in prior['files']:
    if old['path'].split('/')[1] not in modules:
        continue
    observed, custody = directory_entries[old['repositoryPath']]
    if old['path'].endswith('/AnyNativeFileUploadResponse.swift'):
        raw, primary, custody = primary_file('native-file-upload-response')
        assert primary['sha'] == observed['sha']
        note = 'Current immutable base whole body; differs from retained Property4 input.'
        old_ref = ref(Path(old['localSource']))
    else:
        raw = Path(old['localSource']).read_bytes()
        assert digest(raw) == old['sha256'] and len(raw) == old['bytes']
        assert blob(raw) == old['gitBlob'] == observed['sha']
        note = 'Retained whole body independently matches current immutable directory Git blob.'
        old_ref = ref(Path(old['localSource']))
    local = HERE / 'source' / old['path']
    save(local, raw)
    rows.append({'path': old['path'], 'repository': old['repository'],
                 'repositoryPath': old['repositoryPath'], 'bytes': len(raw),
                 'sha256': digest(raw), 'gitBlob': blob(raw), 'localSource': str(local),
                 'sourceCommit': CORE if old['repository'] == 'davidpovarsky/TorahInspectorKit' else BASE,
                 'availableAtPublishedProductCommit': PRODUCT,
                 'wholeOriginalFile': True, 'currentPrimary': custody,
                 'previousWholeInput': old_ref, 'sourceBinding': note})

assert len(rows) == 50

for name, repo_path, output in (
    ('hierarchy-archive-request', 'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift', 'Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift'),
    ('published-repository', 'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift', 'Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift'),
    ('published-tests', 'Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift', 'Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift'),
):
    raw, primary, custody = primary_file(name)
    if name.startswith('published-'):
        assert raw == (RENAME / 'candidate' / repo_path).read_bytes()
    else:
        assert blob(raw) == directory_entries[repo_path][0]['sha']
    local = HERE / 'source' / output
    save(local, raw)
    rows.append({'path': output, 'repository': 'davidpovarsky/anytype-swift',
                 'repositoryPath': repo_path, 'bytes': len(raw), 'sha256': digest(raw),
                 'gitBlob': blob(raw), 'localSource': str(local),
                 'sourceCommit': PRODUCT if name.startswith('published-') else BASE,
                 'availableAtPublishedProductCommit': PRODUCT, 'wholeOriginalFile': True,
                 'currentPrimary': custody, 'sourceBinding': 'Full immutable primary body, Git blob independently verified.'})

for name in ('AnyHTTPHierarchyRecordStore.swift', 'AnyGuardedHTTPHierarchyRecordStore.swift'):
    repo_path = 'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/' + name
    original = RENAME / 'execution-seam/source' / name
    raw = original.read_bytes()
    expected, custody = directory_entries[repo_path]
    assert blob(raw) == expected['sha']
    output = 'Sources/PinkhaAnyIntegration/' + name
    local = HERE / 'source' / output
    save(local, raw)
    rows.append({'path': output, 'repository': 'davidpovarsky/anytype-swift',
                 'repositoryPath': repo_path, 'bytes': len(raw), 'sha256': digest(raw),
                 'gitBlob': blob(raw), 'localSource': str(local), 'sourceCommit': BASE,
                 'availableAtPublishedProductCommit': PRODUCT, 'wholeOriginalFile': True,
                 'currentPrimary': custody, 'retainedWholePrimary': ref(original),
                 'sourceBinding': 'Real protocol-owning HTTP implementation; complete body matches immutable Git blob.'})

rows.sort(key=lambda row: row['path'])
assert len(rows) == 55 and len({x['path'] for x in rows}) == 55
module_inventory = {}
for row in rows:
    group = module_inventory.setdefault(row['path'].split('/')[1], {'files': 0, 'bytes': 0})
    group['files'] += 1
    group['bytes'] += row['bytes']

original_test = (RENAME / 'originals/Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift')
if not original_test.exists():
    original_test = RENAME / 'original/Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift'
test = (HERE / 'source/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift').read_bytes()
assert digest(test[:30174]) == '306aaa783a635eba2123c3403f572ccc104f951f4ce11574f6700cea28b5eaec'
assert digest(test[30174:]) == '2d00953acad46f6a99fe13cac7968b0cdfb7e99aafaf2e42974176df45218484'

package_records = {}
for name in ('kit-package', 'engine-package'):
    raw, primary, custody = primary_file(name)
    local = HERE / 'reference' / (name + '.swift')
    save(local, raw)
    package_records[name] = {**ref(local), 'gitBlob': blob(raw), 'primary': custody}
integration_package = RENAME / 'execution-seam/source/Package.swift'
save(HERE / 'reference/integration-package.swift', integration_package.read_bytes())
package_records['integration-package'] = {**ref(integration_package), 'gitBlob': blob(integration_package.read_bytes())}
assert CORE.encode() in (HERE / 'reference/kit-package.swift').read_bytes()
assert b'exact: "3.12.3"' in (HERE / 'reference/engine-package.swift').read_bytes()

intake = {'schema': 'pinkha-hierarchy-rename-whole-source-intake/v1',
          'status': 'SOURCE_BOUND_PREPARATION_ONLY', 'base': BASE, 'publishedProductCommit': PRODUCT,
          'coreDependencyCommit': CORE, 'originalPackages': package_records,
          'priorWholeSourceIntake': ref(PRIOR), 'priorRootSource': 'Property4 source selection, with Host27 and full Host test excluded.',
          'currentSourceChangesFromPrior': ['AnyNativeFileUploadResponse.swift current immutable whole body',
                                            'Four additional complete Integration bodies: repository, both protocol-owning HTTP stores, archive request',
                                            'Whole published AnyHierarchyTests instead of NativePropertyStoreTests'],
          'productionWholeSwiftFiles': 54, 'testWholeSwiftFiles': 1,
          'sourceBytes': sum(x['bytes'] for x in rows), 'moduleInventory': module_inventory,
          'sourceBodiesChangedForComponent': 0, 'conditionalCompilationGuardsRemoved': 0,
          'productionDeclarationsExtracted': 0, 'projectTypesSynthesized': 0,
          'originalTestPrefix': {'bytes': 30174, 'sha256': digest(test[:30174]), 'methods': 23},
          'newSuiteSuffix': {'bytes': len(test)-30174, 'sha256': digest(test[30174:]), 'methods': 4, 'argumentCases': 8},
          'fullTestMethods': 27, 'selectedSuite': 'AnyHierarchyRawTitleTests', 'oldMethodsSelected': 0,
          'runtimeReady': False, 'compiledSourceClosure': None,
          'staticAnalysisLimit': 'Complete source custody and textual dependency inspection are not compiler/typecheck acceptance.',
          'files': rows}
json_save(HERE / 'whole-source-intake.json', intake)

imports = []
declared = set()
referenced = set()
for row in rows:
    text = Path(row['localSource']).read_text()
    declarations = re.findall(r'\b(?:struct|class|actor|enum|protocol|typealias)\s+([A-Za-z_][A-Za-z_0-9]*)', text)
    declared.update(declarations)
    names = set(re.findall(r'\b(?:Any[A-Z][A-Za-z_0-9]*|Pinkha[A-Z][A-Za-z_0-9]*|Torah[A-Z][A-Za-z_0-9]*)\b', text))
    referenced.update(names)
    imports.append({'path': row['path'], 'sha256': row['sha256'],
                    'importLines': [x for x in text.splitlines() if re.match(r'\s*(?:@testable\s+|public\s+)?import\s+', x)],
                    'conditionalLines': [x for x in text.splitlines() if re.match(r'\s*#(?:if|elseif|else|endif)\b', x)],
                    'declaredTypes': sorted(set(declarations)), 'projectNameTokens': sorted(names)})
unresolved = sorted(referenced-declared-set(module_inventory))
json_save(HERE / 'whole-source-imports.json', {
    'schema': 'pinkha-hierarchy-rename-textual-import-inventory/v1', 'scope': 'Textual inventory only, includes comment/string tokens; not Swift typecheck.',
    'sourceIntake': ref(HERE / 'whole-source-intake.json'), 'moduleIdentities': sorted(module_inventory),
    'originalExternalDependency': 'Crypto3.12.3, exact retained102-file import/header/object closure required at any future run.',
    'bodiesChanged': 0, 'conditionalGuardsRemoved': 0, 'files': imports,
    'unresolvedProjectSpellingTokens': unresolved})
print(json.dumps({'sourceFiles': len(rows), 'sourceBytes': intake['sourceBytes'], 'modules': module_inventory,
                  'intake': ref(HERE / 'whole-source-intake.json'), 'imports': ref(HERE / 'whole-source-imports.json'),
                  'unresolvedProjectSpellingTokens': unresolved}, indent=2))

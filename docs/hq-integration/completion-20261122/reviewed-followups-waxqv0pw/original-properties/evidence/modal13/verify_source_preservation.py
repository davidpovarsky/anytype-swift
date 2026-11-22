"""Bounded source-preservation audit; this is not a Swift/Apple/runtime test."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent


def masked(source):
    # Preserve offsets while ignoring Swift comments and ordinary string
    # literals in these pinned files when locating a method's closing brace.
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"'
    return re.sub(pattern, lambda m: ' ' * len(m.group()), source)


def body(source, signature):
    text = masked(source)
    start = source.index(signature)
    opening = text.index('{', start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(signature)


def canonical(source):
    return ''.join(source.split())


checks = []


def record(name, condition, **evidence):
    if not condition:
        raise AssertionError(name)
    checks.append({'id': name, 'result': 'PASS_SOURCE_PRESERVATION', **evidence})


def pair(path):
    return ((ROOT / 'base' / path).read_text(), (ROOT / 'source' / path).read_text())


unchanged = {
    'Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift': [
        'func discoverManifestObjectId(', 'func loadManifest(', 'func saveManifest('
    ],
    'Modules/Services/Sources/Services/SearchService/SearchMiddleService.swift': ['public func search(data: SearchRequest)'],
    'Anytype/Sources/PresentationLayer/AddNewRelation flow/CreateNewRelation/ViewModel/PropertyInfoViewModel.swift': [
        'func createRelation(', 'func updateRelation(', 'func onSuccessfullAction(', 'func handleFormatUpdate('
    ],
    'Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/RelationCreation/PropertyCreationViewModel.swift': [
        'func onExistingPropertyTap(', 'func addPropertyToType(', 'func addPropertyToDataview('
    ],
}
for path, signatures in unchanged.items():
    old, new = pair(path)
    for signature in signatures:
        before, after = body(old, signature), body(new, signature)
        record('unchanged:' + signature, before == after, path=path,
               body_sha256=hashlib.sha256(before.encode()).hexdigest())

path = 'Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/RelationCreation/PropertyCreationViewModel.swift'
old, new = pair(path)
for signature in ['func search(text:', 'func retryNativeLookup(', 'func onRowTap(',
                  'func onNewPropertyTap(', 'func didPressConfirm(']:
    before, after = body(old, signature), body(new, signature)
    record('legacy_suffix:' + signature, canonical(after).endswith(canonical(before)), path=path,
           original_body_sha256=hashlib.sha256(before.encode()).hexdigest())

path = 'Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift'
old, new = pair(path)
start = new.index('enum OriginalEditorPropertyModalError:')
end = new.index('@MainActor\nextension PropertyModuleConfiguration', start)
without_increment = new[:start] + new[end:]
without_increment = without_increment.replace('import PinkhaKit\n', '', 1)
record('existing_scope_and_value_configuration_byte_exact', without_increment == old, path=path)

manifest = json.loads((ROOT / 'CANDIDATE_INPUTS.json').read_text())
paths = {row['path'] for row in manifest['files']}
for suffix in ['EditorDocumentWriteOwner.swift', 'PreparedEditorPageSessionFactory.swift',
               'Invocation.swift', 'SlashMenuActionHandler.swift', 'PropertiesService.swift',
               'PropertiesListCoordinatorViewModel.swift']:
    record('protected_source_unchanged:' + suffix, not any(path.endswith('/' + suffix) for path in paths))

record('no_generated_heart_or_runtime_edits', not any(
    '/Generated/' in path or '/Heart/' in path or path.endswith('.pb.swift') for path in paths))

report = {
    'status': 'SOURCE_PRESERVATION_VERIFIED',
    'patch_sha256': manifest['patch_sha256'],
    'checks': checks,
    'check_count': len(checks),
    'swift_parse': 'NOT_RUN',
    'apple_semantic_compile': 'NOT_RUN',
    'native_ui': 'NOT_RUN',
    'runtime': 'NOT_RUN',
}
(ROOT / 'SOURCE_PRESERVATION_RECEIPT.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'checks'}, indent=2))

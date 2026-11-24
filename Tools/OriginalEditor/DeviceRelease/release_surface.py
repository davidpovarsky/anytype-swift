"""Inspect all real Release compiler graphs: public API64 and absent Debug SPI22."""
from pathlib import Path
import json
from urllib.parse import urlparse, unquote
from framework_profile import TARGET
from pbx_source import require

def verify_public_surface(graphs, source_root, host_contract):
    """Inspect the actual compiler graph for this target, not imported APIs."""
    source_root = Path(source_root).resolve()
    editor = source_root / 'Anytype/Sources/PresentationLayer/TextEditor'
    app_source = source_root / 'Anytype/Sources'
    facade = source_root / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift'
    reviewed_facades, required, debug_required = {}, set(), set()
    debug_locations = set()
    if host_contract is not None:
        require(host_contract.get('schema') == 2 and len(host_contract.get('facades', {})) == 6,
                'Malformed reviewed Host surface contract')
        for path, contract in host_contract['facades'].items():
            location = (source_root / path).resolve()
            require(location.is_relative_to(source_root / 'OriginalEditorFramework')
                    and isinstance(contract.get('roots'), list) and contract['roots']
                    and isinstance(contract.get('required'), list) and contract['required']
                    and contract.get('scope', 'PUBLIC') in {'PUBLIC', 'DEBUG_SIMULATOR_SPI_ONLY'},
                    'Unreviewed facade source/root requirement')
            if contract.get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY':
                debug_locations.add(location)
                debug_required.update((location, tuple(c)) for c in contract['required'])
            else:
                reviewed_facades[location] = contract
                required.update((location, tuple(components)) for components in contract['required'])
        require(len(required) == 64 and len(debug_required) == 22 and len(reviewed_facades) == 5
                and len(debug_locations) == 1, 'Incomplete production/Debug absence surface contract')
    debug_paths = {components for _, components in debug_required}
    production_roots = {name for value in reviewed_facades.values() for name in value['roots']}
    debug_roots = {name for value in host_contract['facades'].values()
                   if value.get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY' for name in value['roots']} - production_roots
    found_inspection = False
    own_symbols = []
    imported_count = 0
    blocked = []
    unsafe_names = ('EditorPage', 'PreparedEditor', 'EditorDocumentWrite', 'DocumentOwned', 'BaseDocument',
                    'OwnedOriginalEditor', 'OwnedQualificationSpace', 'AnytypeOriginalEditorNativeFixture',
                    'AnytypeOriginalEditorRestoreQualification')
    observed_required = set()
    for graph in graphs:
        if graph.get('module', {}).get('name') != TARGET:
            imported_count += len(graph.get('symbols', []))
            continue
        require(isinstance(graph.get('symbols'), list), 'Malformed actual target symbol graph')
        for symbol in graph['symbols']:
            require(symbol.get('accessLevel') in {'public', 'open'}, 'Compiler graph has unexpected access scope')
            components = symbol.get('pathComponents', [])
            require(isinstance(components, list) and all(isinstance(item, str) for item in components),
                    'Malformed public symbol path')
            uri = symbol.get('location', {}).get('uri')
            location = None
            if uri:
                parsed = urlparse(uri)
                require(parsed.scheme == 'file', 'Unrecognized compiler symbol source URI')
                location = Path(unquote(parsed.path)).resolve()
            precise = symbol.get('identifier', {}).get('precise', '')
            our_identifier = precise.startswith('s:' + str(len(TARGET)) + TARGET)
            own_app_source = location is not None and location.is_relative_to(app_source)
            own_facade = location == facade or location in reviewed_facades or location in debug_locations
            # Imported/re-exported package symbols are not our target's public
            # constructors and must not be confused with an editing API.
            if not own_app_source and not own_facade and not our_identifier:
                imported_count += 1
                continue
            require(location not in debug_locations and (location, tuple(components)) not in debug_required
                    and tuple(components) not in debug_paths and not (components and components[0] in debug_roots)
                    and symbol.get('spi', False) is False,
                    'Debug qualification or SPI declaration leaked into the Release product')
            own_symbols.append({'path': components, 'identifier': precise, 'location': uri,
                                'spi': symbol.get('spi', False)})
            if own_facade and components[:1] == ['AnytypeOriginalEditorModule'] and components[-1:] == ['inspectResources()']:
                found_inspection = True
            if location in reviewed_facades:
                require(components and components[0] in reviewed_facades[location]['roots'],
                        'Unexpected public declaration in a reviewed Host facade: ' + repr(components))
                expected_spi = False
                require(type(symbol.get('spi', False)) is bool
                        and symbol.get('spi', False) is expected_spi,
                        'Actual compiler public/SPI scope differs from the reviewed facade: ' + repr(components))
                observed_required.add((location, tuple(components)))
                require(not (components[0] in host_contract['nonconstructible_types']
                             and any(item.startswith('init(') for item in components[1:])),
                        'Public constructor grants an unowned original Host/session capability')
            if (host_contract is not None and location is not None
                    and location.is_relative_to(source_root / 'OriginalEditorFramework')
                    and location not in reviewed_facades):
                blocked.append({'path': components, 'identifier': precise, 'location': uri})
            if ((location is not None and location.is_relative_to(editor))
                    or any(item.startswith(unsafe_names) for item in components)):
                blocked.append({'path': components, 'identifier': precise, 'location': uri})
    require(found_inspection, 'Actual compiler graph does not expose the reviewed inspection facade')
    require(not blocked, 'Unqualified original editor/document/writer declaration is public: ' + json.dumps(blocked))
    require(required <= observed_required, 'Missing actual compiled Host or qualification SPI declaration: ' +
            repr(sorted((str(location), components) for location, components in required - observed_required)))
    return {'status': 'ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED', 'target': TARGET,
            'own_public_symbols': own_symbols, 'imported_dependency_symbols_not_rejected': imported_count,
            'public_original_editor_or_writer_declarations': [],
            'reviewed_host_and_spi_requirements_observed': len(required),
            'debug_qualification_requirements_absent': len(debug_required),
            'debug_qualification_symbols_observed': [],
            'qualification_spi_scope_verified': host_contract is not None,
            'public_host_scope_verified': host_contract is not None,
            'editable_mount_api': 'EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN' if host_contract is not None else 'NOT_EXPOSED'}

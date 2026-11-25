"""New Host admission controls; synthetic graphs are never compiler evidence."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from framework_profile import HERE, APP_TARGET, TARGET, read_manifest, verify_project
from framework_products import verify_public_surface
from pbx_source import loads, object_text, render

ROOT = HERE.parents[1]
CONTRACT = json.loads((HERE / 'public_host_contract.json').read_text())


class HostFrameworkContractControls(unittest.TestCase):
    def graph(self):
        symbols = []
        for path, item in CONTRACT['facades'].items():
            for components in item['required']:
                symbols.append({'accessLevel': 'public', 'pathComponents': components,
                    'identifier': {'precise': 's:21AnytypeOriginalEditorSynthetic' + str(len(symbols))},
                    'location': {'uri': (ROOT / path).as_uri()},
                    **({'spi': True} if item.get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY' else {})})
        return {'module': {'name': TARGET}, 'symbols': symbols}

    def verify(self, graph):
        return verify_public_surface([graph], ROOT, host_contract=CONTRACT)

    def test_all_reviewed_public_and_spi_paths_are_required_without_ui_credit(self):
        result = self.verify(self.graph())
        self.assertEqual(result['reviewed_host_and_spi_requirements_observed'], 127)
        self.assertEqual(result['editable_mount_api'], 'EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN')
        self.assertEqual(len(result['own_public_symbols']), 127)
        self.assertTrue(result['qualification_spi_scope_verified'])
        self.assertTrue(result['public_host_scope_verified'])
        self.assertEqual(sum(symbol['spi'] for symbol in result['own_public_symbols']), 22)

    def test_qualification_declarations_require_actual_spi_scope(self):
        original = self.graph()
        for index, symbol in enumerate(original['symbols']):
            if symbol.get('spi') is not True:
                continue
            for remove in [False, True]:
                with self.subTest(path=symbol['pathComponents'], absent=remove):
                    graph = copy.deepcopy(original)
                    if remove:
                        graph['symbols'][index].pop('spi')
                    else:
                        graph['symbols'][index]['spi'] = False
                    with self.assertRaises(ValueError): self.verify(graph)

    def test_regular_host_declarations_cannot_be_hidden_as_spi(self):
        original = self.graph()
        for index, symbol in enumerate(original['symbols']):
            if symbol.get('spi') is True:
                continue
            with self.subTest(path=symbol['pathComponents']):
                graph = copy.deepcopy(original)
                graph['symbols'][index]['spi'] = True
                with self.assertRaises(ValueError): self.verify(graph)

    def test_malformed_spi_marker_does_not_grant_qualification_scope(self):
        for marker in [None, 'true', 1, [], {}]:
            with self.subTest(marker=marker):
                graph = self.graph()
                symbol = next(item for item in graph['symbols'] if item.get('spi') is True)
                symbol['spi'] = marker
                with self.assertRaises(ValueError): self.verify(graph)

    def test_missing_real_capture_entrypoint_rejects_inspection_only_surface(self):
        graph = self.graph()
        graph['symbols'] = [symbol for symbol in graph['symbols']
                            if symbol['pathComponents'][-1] != 'captureNativeSnapshot(maximumBodyBytes:)']
        with self.assertRaises(ValueError): self.verify(graph)

    def test_same_spelling_from_a_foreign_source_is_not_a_host_capability(self):
        graph = self.graph()
        symbol = next(s for s in graph['symbols'] if s['pathComponents'] == ['AnytypeOriginalEditorHost'])
        symbol['location']['uri'] = (ROOT / 'Modules/Unrelated/Host.swift').as_uri()
        with self.assertRaises(ValueError): self.verify(graph)

    def test_public_unowned_host_constructor_is_rejected(self):
        graph = self.graph()
        graph['symbols'].append({'accessLevel': 'public',
            'pathComponents': ['AnytypeOriginalEditorHost', 'init()'],
            'identifier': {'precise': 's:21AnytypeOriginalEditorUnownedConstructor'},
            'location': {'uri': (ROOT / 'OriginalEditorFramework/AnytypeOriginalEditorHost.swift').as_uri()}})
        with self.assertRaises(ValueError): self.verify(graph)

    def test_local_session_and_capture_cannot_be_publicly_fabricated(self):
        path = ROOT / 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift'
        for name in ['AnytypeOriginalEditorLocalAnnotationSession',
                     'AnytypeOriginalEditorLocalAnnotationCapture']:
            with self.subTest(name=name):
                graph = self.graph()
                graph['symbols'].append({'accessLevel': 'public',
                    'pathComponents': [name, 'init()'],
                    'identifier': {'precise': 's:21AnytypeOriginalEditorUnownedLocalConstructor'},
                    'location': {'uri': path.as_uri()}})
                with self.assertRaises(ValueError): self.verify(graph)

    def test_public_raw_runtime_helper_is_not_the_qualified_spi(self):
        graph = self.graph()
        graph['symbols'].append({'accessLevel': 'public',
            'pathComponents': ['OwnedOriginalEditorQualificationRuntime', 'init()'],
            'identifier': {'precise': 's:21AnytypeOriginalEditorUnownedRuntime'},
            'location': {'uri': (ROOT / 'OriginalEditorFramework/AnytypeOriginalEditorQualificationRuntime.swift').as_uri()}})
        with self.assertRaises(ValueError): self.verify(graph)

    def test_new_resume_context_fields_and_operations_cannot_be_missing(self):
        additions = [['AnytypeOriginalEditorProcessResumeContext'], ['AnytypeOriginalEditorProcessResumeContext', 'init(workspaceNamespace:legacyAnnotationID:payloadDigest:)'], ['AnytypeOriginalEditorProcessResumeContext', 'workspaceNamespace'], ['AnytypeOriginalEditorProcessResumeContext', 'legacyAnnotationID'], ['AnytypeOriginalEditorProcessResumeContext', 'payloadDigest'], ['AnytypeOriginalEditorProcessResumeReceipt'], ['AnytypeOriginalEditorProcessResumeReceipt', 'runtimeNonce'], ['AnytypeOriginalEditorProcessResumeReceipt', 'accountID'], ['AnytypeOriginalEditorProcessResumeReceipt', 'spaceID'], ['AnytypeOriginalEditorProcessResumeReceipt', 'objectID'], ['AnytypeOriginalEditorProcessResumeReceipt', 'preparedProcessID'], ['AnytypeOriginalEditorProcessResumeReceipt', 'currentProcessID'], ['AnytypeOriginalEditorProcessResumeReceipt', 'credentialConsumed'], ['AnytypeOriginalEditorQualificationSession', 'processResumeReceipt'], ['AnytypeOriginalEditorQualificationSession', 'prepareProcessResume(host:snapshot:currentSource:context:sourceIsCurrent:)'], ['AnytypeOriginalEditorModule', 'cleanupOwnedProcessResumeCredential()'], ['AnytypeOriginalEditorModule', 'resumeEditableAcceptance(source:snapshot:context:sourceIsCurrent:)']]
        original = self.graph()
        for components in additions:
            with self.subTest(path=components):
                graph = copy.deepcopy(original)
                graph["symbols"] = [row for row in graph["symbols"] if row["pathComponents"] != components]
                with self.assertRaises(ValueError):
                    self.verify(graph)

    def test_returned_process_receipt_cannot_be_publicly_constructed(self):
        graph = self.graph()
        graph["symbols"].append({
            "accessLevel": "public", "spi": True,
            "pathComponents": ["AnytypeOriginalEditorProcessResumeReceipt", "init()"],
            "identifier": {"precise": "s:21AnytypeOriginalEditorUnownedProcessReceipt"},
            "location": {"uri": (ROOT / "OriginalEditorFramework/AnytypeOriginalEditorQualification.swift").as_uri()}
        })
        with self.assertRaises(ValueError):
            self.verify(graph)

    def test_every_account_and_import_public_boundary_is_required(self):
        added = {'OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift',
                 'OriginalEditorFramework/AnytypeOriginalAnnotationImport.swift',
                 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift'}
        original = self.graph()
        for index, symbol in enumerate(original['symbols']):
            if not any(symbol['location']['uri'] == (ROOT / path).as_uri() for path in added):
                continue
            with self.subTest(path=symbol['pathComponents']):
                graph = copy.deepcopy(original)
                del graph['symbols'][index]
                with self.assertRaises(ValueError):
                    self.verify(graph)

    def test_account_identity_presentation_import_history_and_attempt_have_no_public_constructor(self):
        for path, components in [
            ('AnytypeOriginalEditorAccountSession.swift', ['AnytypeOriginalEditorAccountSession']),
            ('AnytypeOriginalEditorAccountSession.swift', ['AnytypeOriginalEditorAccountSession', 'Identity']),
            ('AnytypeOriginalEditorAccountSession.swift', ['AnytypeOriginalEditorAccountSession', 'Presentation']),
            ('AnytypeOriginalAnnotationImport.swift', ['AnytypeOriginalAnnotationImportHistory']),
            ('AnytypeOriginalAnnotationImport.swift', ['AnytypeOriginalAnnotationImportAttempt']),
            ('AnytypeOriginalAnnotationImport.swift', ['AnytypeOriginalAnnotationImportReceipt']),
            ('AnytypeOriginalAnnotationImport.swift', ['AnytypeOriginalAnnotationImportReceipt', 'ObjectMapping']),
        ]:
            with self.subTest(path=components):
                graph = self.graph()
                graph['symbols'].append({'accessLevel': 'public', 'pathComponents': components + ['init()'],
                    'identifier': {'precise': 's:21AnytypeOriginalEditorUnownedContinuation'},
                    'location': {'uri': (ROOT / 'OriginalEditorFramework' / path).as_uri()}})
                with self.assertRaises(ValueError):
                    self.verify(graph)

    def mutation(self, identifier, change):
        raw = (ROOT / 'Anytype.xcodeproj/project.pbxproj').read_text()
        objects = loads(raw)['objects']
        change(objects[identifier])
        raw = raw.replace(object_text(raw, identifier),
                          '\t\t' + identifier + ' = ' + render(objects[identifier], 2) + ';\n', 1).encode()
        profile = copy.deepcopy(read_manifest())
        profile['candidate_project_sha256'] = hashlib.sha256(raw).hexdigest()
        return raw, profile

    def test_different_shared_package_pin_rejected_even_with_updated_project_hash(self):
        raw, profile = self.mutation('5333421A262E249100238121',
                                    lambda value: value['requirement'].update(version='2.8.3'))
        with self.assertRaises(ValueError):
            verify_project(raw, (HERE / 'original_project.pbxproj').read_bytes(), profile)

    def test_symbol_graph_emission_cannot_spill_into_original_application(self):
        objects = loads((ROOT / 'Anytype.xcodeproj/project.pbxproj').read_text())['objects']
        configuration = objects[objects[APP_TARGET]['buildConfigurationList']]['buildConfigurations'][0]
        raw, profile = self.mutation(configuration,
            lambda value: value['buildSettings'].update(ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS='-emit-symbol-graph'))
        with self.assertRaises(ValueError):
            verify_project(raw, (HERE / 'original_project.pbxproj').read_bytes(), profile)


if __name__ == '__main__':
    unittest.main(verbosity=2)

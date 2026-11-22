"""Materialize source-bound inputs only. Never invokes Swift or runs controls."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent
SHARED = ROOT.parent
MODAL = SHARED / "original_editor_property_modal_waxqv0pw_20261122"
JOIN = SHARED / "original_editor_property_join_waxqv0pw_20261122"
PRIOR = SHARED / "anytype_publishing_join_waxqv0pw_20261122/validation/portable-inputs"
OUT = ROOT / "portable-inputs"
PRODUCTION = ROOT / "production"
BASE = "fc03fcd713e2c449ad97c5d1e604a9433c2a309b"
MODAL_PATCH = "377ef209aa567db9f95728f54be101726befea96b2e2cc36b28d0ca3a8bb729d"
JOIN_PATCH = "90605b0cb2576c87c3102729ef4784733fc4e24989045acd756b3b9d1f6d5a25"
SCOPE = "Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift"
STORE = "Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift"
POLICY = "Anytype/Sources/Pinkha/Torah/Properties/PinkhaTorahPropertyPolicy.swift"
MANIFEST = "Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSpaceManifest.swift"
ROLE = "Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def materialize(*, prepare_only: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PRODUCTION.mkdir(parents=True, exist_ok=True)
    inputs: list[dict] = []
    regions: list[dict] = []
    source_records: list[dict] = []

    modal_manifest = json.loads((MODAL / "CANDIDATE_INPUTS.json").read_text())
    join_manifest = json.loads((JOIN / "SOURCE_MANIFEST.json").read_text())
    assert modal_manifest["base"] == BASE
    assert modal_manifest["patch_sha256"] == MODAL_PATCH
    assert sha((MODAL / "original-property-modal-owner.patch").read_bytes()) == MODAL_PATCH
    assert join_manifest["compatible_frozen_producer"] == BASE
    assert join_manifest["combined_patch"]["sha256"] == JOIN_PATCH
    assert sha((JOIN / join_manifest["combined_patch"]["path"]).read_bytes()) == JOIN_PATCH
    assert len(modal_manifest["files"]) == 13 and len(join_manifest["files"]) == 16
    # Identity verification for this control packet, not a repeated test suite.
    for entry in modal_manifest["files"]:
        data = (MODAL / "source" / entry["path"]).read_bytes()
        assert sha(data) == entry["candidate_sha256"]
        assert blob(data) == entry["candidate_git_blob"]
        joined = next(row for row in join_manifest["files"] if row["path"] == entry["path"])
        assert joined["source_sha256"] == entry["candidate_sha256"]

    def source(path: str, local: Path, expected_blob: str) -> bytes:
        data = local.read_bytes()
        assert blob(data) == expected_blob, (path, blob(data), expected_blob)
        target = PRODUCTION / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        source_records.append({"path": path, "git_blob": expected_blob, "sha256": sha(data), "bytes": len(data)})
        return data

    def add(name: str, data: bytes | str, *, provenance: str, transformation: str = "none", **extra) -> None:
        if isinstance(data, str):
            data = data.encode()
        (OUT / name).write_bytes(data)
        inputs.append({"name": name, "sha256": sha(data), "bytes": len(data),
                       "provenance": provenance, "transformation": transformation, **extra})

    def region(data: bytes, start: bytes, end: bytes, *, path: str, label: str) -> bytes:
        assert data.count(start) == 1, (label, "non-unique start")
        first = data.index(start)
        last = data.index(end, first)
        selected = data[first:last]
        assert selected
        regions.append({"label": label, "source_path": path, "source_sha256": sha(data),
                        "start_byte": first, "end_byte_exclusive": last,
                        "region_sha256": sha(selected), "region_bytes": len(selected),
                        "transformation": "exact bytes, no semantic or whitespace edit"})
        return selected

    prior_manifest = json.loads((PRIOR / "INPUTS.json").read_text())
    core_sources = {
        "Lifetime.swift": ("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteLifetime.swift",
                           SHARED / "anytype_writer_qualification/candidate/Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteLifetime.swift",
                           "19f81f5e1bb51b48a7fd46d30476a99105d9aea2"),
        "Operation.swift": ("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOperation.swift",
                            SHARED / "anytype_writer_qualification/candidate/Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOperation.swift",
                            "fdfa2a427044e6ea395f02dbda43d244b1fbe4af"),
        "Binding.swift": ("Modules/ProtobufMessages/Sources/InvocationDispatchBinding.swift",
                          SHARED / "anytype_writer_qualification/candidate/Modules/ProtobufMessages/Sources/InvocationDispatchBinding.swift",
                          "7f6862925605de7a15220f6c44dbf4d6d884113d"),
        "Owner.swift": ("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift",
                        MODAL / "references/Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift",
                        "c90dd7f2ee0577d3496d81fd164fc238b79ea364"),
        "PreparedEditorPageDocument.swift": ("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/PreparedEditorPageDocument.swift",
                                             PRIOR / "PreparedEditorPageDocument.swift", "37ff035f30c0b2f17c2ce75b4c7a7f1acbbb78a2")
    }
    for name, (path, local, expected) in core_sources.items():
        canonical = source(path, local, expected)
        previous = next(row for row in prior_manifest["files"] if row["name"] == name)
        staged = (PRIOR / name).read_bytes()
        assert sha(staged) == previous["staged_sha256"]
        assert canonical.replace(b"import ProtobufMessages\n", b"") == staged
        add(name, staged, provenance=path, canonical_sha256=sha(canonical), canonical_git_blob=expected,
            transformation="remove only ProtobufMessages import when present; original bodies unchanged",
            reused_without_previous_test_execution=True)
    value_name = "OriginalTypePermissionProbe.swift"
    values = (PRIOR / value_name).read_bytes()
    assert sha(values) == "0708d577f19f0c382cec913b990e949716c543536c4166575ed60e96f5c33f6a"
    add(value_name, values, provenance="unchanged explicit disposable model inputs from prior portable harness",
        transformation="none; these values do not implement a store, factory or RPC", production_source=False)
    participants = source(ROLE, SHARED / "anytype_channel_pin_role_qualification/source" / ROLE,
                          "953cf70be87282dde644d0a4e4b10c1e2f04edc0")
    role_start = participants.index(b"// ORIGINAL_CHANNEL_PIN_PERMISSION_BEGIN")
    role_end = participants.index(b"// ORIGINAL_CHANNEL_PIN_PERMISSION_END", role_start) + len(b"// ORIGINAL_CHANNEL_PIN_PERMISSION_END")
    role_region = participants[role_start:role_end]
    add("RoleSource.swift", b"import Foundation\n" + role_region + b"\n", provenance=ROLE,
        transformation="exact marked production region plus Foundation import; required by Owner; no role controls rerun",
        region_sha256=sha(role_region), canonical_sha256=sha(participants))

    scope_entry = next(row for row in modal_manifest["files"] if row["path"] == SCOPE)
    scope = source(SCOPE, MODAL / "source" / SCOPE, scope_entry["candidate_git_blob"])
    store_entry = next(row for row in modal_manifest["files"] if row["path"] == STORE)
    store = source(STORE, MODAL / "source" / STORE, store_entry["candidate_git_blob"])
    policy = source(POLICY, MODAL / "references" / POLICY, "8a5abc0a225ab9ca2d3db9fe9670b5f35753886e")
    pure_inputs = [
        ("PinkhaSpaceManifest.swift", MANIFEST, MODAL / "references" / MANIFEST, "69220b20ad4a55b9b4d10c62793c66b9521ce1af"),
        ("PinkhaRuntime.swift", "Modules/PinkhaKit/Sources/PinkhaKit/Domain/PinkhaRuntime.swift", None, "41733085a76c45b3ff916c047e1839cdf96184eb"),
        ("PinkhaSchemaRoles.swift", "Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSchemaRoles.swift", None, "83e42de4bf880d13ce20a841410681c6e6fa0f8d"),
        ("BundledPropertyKey.swift", "Modules/Services/Sources/Generated/BundledPropertyKey.swift", None, "582d3789fe7390a09791a2694f5b61b70db43c46")
    ]
    for name, path, local, expected in pure_inputs:
        canonical = source(path, local or ROOT / "references" / path, expected)
        add(name, canonical, provenance=path, canonical_git_blob=expected)
    identity_region = region(policy, b"public struct PinkhaInternalPropertyIdentities:", b"public enum InternalIdentityStatus:",
                             path=POLICY, label="original_internal_identity_value_and_matcher")
    add("PinkhaInternalPropertyIdentities.swift", b"import Foundation\n\n" + identity_region,
        provenance=POLICY, transformation="exact original struct only plus Foundation import; policy/cache/bootstrap omitted")

    static_permissions = region(scope, b"    static let valuePermissions:", b"\n\n    let preparedSession:", path=SCOPE, label="original_property_named_permissions")
    with_current = region(scope, b"    func withCurrent<Value>(", b"    /// The original callback", path=SCOPE, label="original_scope_current_boundary")
    with_callback = region(scope, b"    func withActionCallback<Value>(", b"    /// Reserve on the actual UI callback", path=SCOPE, label="original_scope_action_callback")
    prepare_action = region(scope, b"    func prepareAction(", b"    func perform<Value:", path=SCOPE, label="original_scope_synchronous_action_reservation")
    modal_error = region(scope, b"enum OriginalEditorPropertyModalError:", b"/// Per-operation metadata", path=SCOPE, label="new_modal_error_enum")
    identity_snapshot = region(scope, b"struct OriginalEditorPropertyIdentitySnapshot:", b"@MainActor\nextension OriginalEditorPropertyScope", path=SCOPE, label="new_modal_identity_snapshot")
    load_start = scope.index(b"    func loadModalPropertyIdentity()")
    load_end = scope.index(b"    func requireModalProperty(", load_start)
    load = scope[load_start:load_end]
    validation_start = load.index(b"        return try withCurrent {")
    validation_end = load.rindex(b"    }")
    validator = load[validation_start:validation_end]
    regions.append({"label": "new_post_canonical_read_validator", "source_path": SCOPE,
                    "source_sha256": sha(scope), "start_byte": load_start + validation_start,
                    "end_byte_exclusive": load_start + validation_end, "region_sha256": sha(validator),
                    "region_bytes": len(validator), "transformation": "exact body; explicit already-read manifest input replaces service acquisition only"})
    require_identity = region(scope, b"    private func requireModalIdentity(", b"    private static func requireModalProperty(",
                              path=SCOPE, label="new_snapshot_scope_identity_guard")
    probe = b'''import Foundation

// Portable envelope only: the real owner and explicit document input are
// supplied directly. No PreparedSession, Factory, service or acquisition is
// implemented. Every copied production body below is byte-verified by region.
@MainActor
final class OriginalEditorPropertyScope {
''' + static_permissions + b'''

    let owner: EditorDocumentWriteOwner
    let objectId: String
    let spaceId: String
    private let document: any BaseDocumentProtocol

    init(owner: EditorDocumentWriteOwner, objectId: String, spaceId: String,
         document: any BaseDocumentProtocol) {
        self.owner = owner
        self.objectId = objectId
        self.spaceId = spaceId
        self.document = document
    }

''' + with_current + with_callback + prepare_action + b'''
    // Test-only signature supplies the actual canonical read's decoded result.
    // The following return block is exactly the production post-await block.
    func probeValidateCanonicalResult(
        _ manifest: PinkhaSpaceManifest?, enabled: Bool = PinkhaRuntime.enabled
    ) throws -> OriginalEditorPropertyIdentitySnapshot {
''' + validator + b'''    }

''' + require_identity + b'''
    // Test visibility only, preserving the original private guard unchanged.
    func probeRequireIdentity(_ identity: OriginalEditorPropertyIdentitySnapshot) throws {
        try withCurrent { try requireModalIdentity(identity) }
    }

    func probeInternalIdentities(_ identity: OriginalEditorPropertyIdentitySnapshot) throws -> PinkhaInternalPropertyIdentities? {
        try withCurrent {
            try requireModalIdentity(identity)
            return identity.internalIdentities
        }
    }
}

''' + modal_error + identity_snapshot
    add("OriginalPropertyScopeProbe.swift", probe, provenance=SCOPE,
        transformation="exact listed production regions in explicit owner/document envelope; test-only result argument and visibility methods")

    discovery = region(store, b"        let valid = candidates.values.filter", b"\n    }\n\n    private enum ManifestDiscoveryError:",
                       path=STORE, label="original_canonical_discovery_filter_and_ambiguity")
    discovery_error = region(store, b"    private enum ManifestDiscoveryError:", b"\n\n    public func loadManifest(",
                             path=STORE, label="original_canonical_ambiguity_error")
    discovery_probe = b'''import Foundation

// Explicit already-decoded response projections. These do not search, decode
// protobufs or impersonate ObjectDetails/Lib. The original final discovery
// filter below consumes exactly these three fields and the string projection.
struct CanonicalDiscoveryValue: Sendable { let stringValue: String }
struct CanonicalDiscoveryCandidate: Sendable {
    let id: String
    let spaceId: String
    let values: [String: CanonicalDiscoveryValue]
}

enum OriginalManifestDiscoveryProbe {
    static func discover(candidates: [String: CanonicalDiscoveryCandidate], spaceId: String) throws -> String? {
''' + discovery + b'''
    }

''' + discovery_error + b'''

    static func isAmbiguous(_ error: Error) -> Bool {
        guard case .ambiguous? = error as? ManifestDiscoveryError else { return false }
        return true
    }
}
'''
    add("OriginalManifestDiscoveryProbe.swift", discovery_probe, provenance=STORE,
        transformation="exact original final filter/error; already-decoded response projections; real search/ObjectShow not executed")

    composition = region(scope, b"    func withSelectedModalProperty<Value:", b"    static func modalPropertySnapshot(",
                         path=SCOPE, label="production_parent_child_composition_source_binding_only")
    ordered = [b"let identity = try await loadModalPropertyIdentity()",
               b"let child = try await preparation.prepare(",
               b"let selected = try Self.modalPropertySnapshot(",
               b"try await beforeMutation?(selected)",
               b"let result = try await child.owner.performDocumentAction(",
               b"        try withCurrent {}\n        return result"]
    offsets = [composition.index(item) for item in ordered]
    assert offsets == sorted(offsets) and len(set(offsets)) == len(offsets)
    source_order = {"kind": "BOUNDED_SOURCE_ORDER_ASSERTION_NOT_RUNTIME_TEST",
                    "source_region_sha256": sha(composition),
                    "anchors_in_order": [item.decode() for item in ordered],
                    "byte_offsets": offsets,
                    "not_executed": "Actual child Factory, services, native returned property values and UI callbacks"}

    write_json(ROOT / "PRODUCTION_REGIONS.json", {"modal_patch_sha256": MODAL_PATCH,
               "combined_patch_sha256": JOIN_PATCH, "regions": regions, "composition_source_order": source_order})
    write_json(ROOT / "PRODUCTION_INPUTS.json", {"base": BASE, "sources": source_records})
    write_json(ROOT / "EXTRACTED_INPUTS.json", {"files": inputs, "compiler_invoked": False, "controls_executed": False})
    if prepare_only:
        print(json.dumps({"status": "EXACT_INPUTS_MATERIALIZED_NOT_COMPILED", "inputs": len(inputs), "regions": len(regions)}))
        return

    expected_ids: list[str] = []
    for name in ["CanonicalModalControls.swift", "OwnerModalControls.swift"]:
        data = (ROOT / name).read_bytes()
        match = re.search(r"static let expectedIDs = (\[[\s\S]*?\])\n", data.decode())
        assert match is not None
        expected_ids.extend(json.loads(match.group(1)))
        add(name, data, provenance="new portable controls only", production_source=False)
    assert len(expected_ids) == len(set(expected_ids))
    entry = '''import Foundation

@main
private struct PropertyModalControlMain {
    @MainActor static func main() async throws {
        let canonical = try await CanonicalModalControls.run()
        let owner = try await OwnerModalControls.run()
        let passed = canonical + owner
        let expected = CanonicalModalControls.expectedIDs + OwnerModalControls.expectedIDs
        guard passed == expected, Set(passed).count == passed.count else {
            throw NSError(domain: "PropertyModalControls", code: 1)
        }
        let report: [String: Any] = [
            "status": "PASS_NEW_PORTABLE_PROPERTY_MODAL_CONTROLS",
            "passed": passed, "expected": expected, "executed": passed.count,
            "failed": 0, "skipped": 0,
            "modal_patch_sha256": "''' + MODAL_PATCH + '''",
            "combined_patch_sha256": "''' + JOIN_PATCH + '''",
            "prior_suites_rerun": false,
            "apple_typecheck": "NOT_RUN_BY_THIS_EXECUTABLE",
            "native_editor": "NOT_RUN",
            "canonical_network_read": "NOT_RUN",
            "native_mutation_dispatch": "NOT_RUN_DISPOSABLE_EFFECT_ONLY"
        ]
        let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }
}
'''
    add("PropertyModalControlMain.swift", entry, provenance="explicit result entry point, not production", production_source=False)
    manifest = {
        "status": "FROZEN_NEW_CONTROL_INPUTS_NOT_COMPILED_OR_EXECUTED",
        "base": BASE, "modal_patch_sha256": MODAL_PATCH, "combined_patch_sha256": JOIN_PATCH,
        "scope": "Exact post-read canonical validator, original manifest model/identity matcher/discovery filter, and real current Owner/lifetime/operation/permit composition using explicit immutable document/effect inputs.",
        "excluded": ["UIKit and SwiftUI", "PreparedEditorPageSessionFactory acquisition", "actual SearchMiddleService/ObjectSearch/ObjectShow requests", "protobuf response decoding", "ObjectCreateRelation/ObjectRelationAdd/ObjectSetDetails/Archive bodies", "Heart/Lib", "actual event delivery and saved storage", "full PropertiesInteractor/coordinator execution"],
        "prior_suites_rerun": False, "compiler_invoked": False, "controls_executed": False,
        "expected_control_ids": expected_ids, "expected_controls": len(expected_ids),
        "production_regions_sha256": sha((ROOT / "PRODUCTION_REGIONS.json").read_bytes()),
        "production_inputs_sha256": sha((ROOT / "PRODUCTION_INPUTS.json").read_bytes()),
        "compiler_policy": {"jobs": 1, "dependencies": "Foundation only; no external dependency build", "invocation_owner": "root after review"},
        "files": inputs
    }
    write_json(OUT / "INPUTS.json", manifest)
    write_json(ROOT / "INPUTS.json", manifest)
    for name in ["PRODUCTION_REGIONS.json", "PRODUCTION_INPUTS.json"]:
        (OUT / name).write_bytes((ROOT / name).read_bytes())
    (OUT / "README.md").write_bytes((ROOT / "README.md").read_bytes())
    archive = ROOT / "property-modal-controls.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in sorted(OUT.iterdir()):
            item = ZipInfo(path.name, (2026, 11, 22, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = ZIP_DEFLATED
            zipped.writestr(item, path.read_bytes())
    with ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        members = [{"name": name, "sha256": sha(zipped.read(name)), "bytes": len(zipped.read(name))}
                   for name in zipped.namelist()]
    write_json(ROOT / "PACKET_RECEIPT.json", {
        "archive": archive.name, "sha256": sha(archive.read_bytes()), "bytes": archive.stat().st_size,
        "deterministic_timestamp": "2026-11-22T00:00:00", "crc": "PASS", "members": members,
        "status": "PACKAGED_NOT_COMPILED_NOT_EXECUTED", "production_changed": False,
        "modal_patch_sha256": MODAL_PATCH, "combined_patch_sha256": JOIN_PATCH,
        "build_controls_sha256": sha(Path(__file__).read_bytes())
    })
    print(json.dumps({"status": "PACKAGED_NOT_COMPILED_NOT_EXECUTED", "archive": str(archive),
                      "sha256": sha(archive.read_bytes()), "bytes": archive.stat().st_size,
                      "swift_inputs": len(inputs), "crc": "PASS"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    materialize(prepare_only=parser.parse_args().prepare_only)

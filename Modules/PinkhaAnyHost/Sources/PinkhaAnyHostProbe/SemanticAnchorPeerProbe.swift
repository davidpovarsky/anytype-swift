import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

/// A real native peer probe. The Python owner supplies isolated accounts,
/// genuine network discovery and the separate OS-offline process. This code
/// uses the same marker codec, conditional editor and signed claim repository
/// as the application; it never substitutes an unsigned JSON property.
private struct SemanticPeerFixture: Codable, Sendable {
    let version: Int
    let spaceID: String
    let creatorAccountID: String
    let objectID: String
    let blockID: String
    let title: String
    let anchor: PinkhaSemanticTextAnchor
    let originalBody: String
    let editedBody: String
    let style: AnyJSON?
    let navigation: AnyJSON?
    let semanticItem: TorahAssociationItem
    let unrelatedItem: TorahAssociationItem
    let linkedCanonical: Data
    let unlinkedCanonical: Data

    var location: TorahAssociationLocation {
        .init(spaceId: spaceID, target: .object(objectId: objectID))
    }
}

private func semanticPeerCanonical(_ records: [TorahStoredAssociationRecord]) throws -> Data {
    try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
        records: records.sorted { $0.item.id < $1.item.id }))
}

private func verifySemanticPeerDocument(_ read: AnyEditorRead, fixture: SemanticPeerFixture,
                                        edited: Bool) throws {
    try require(read.snapshot.spaceID == fixture.spaceID && read.snapshot.objectID == fixture.objectID
        && read.snapshot.title == fixture.title && read.snapshot.depthFirstIDs == [fixture.blockID]
        && read.snapshot.unreachableIDs.isEmpty && read.snapshot.blocks.count == 1,
        "complete original peer document identity and hierarchy")
    guard let block = read.snapshot.blocks.first else { throw ProbeError.failed("missing original block") }
    try require(block.id == fixture.blockID && block.type == "paragraph"
        && block.text.utf8.elementsEqual((edited ? fixture.editedBody : fixture.originalBody).utf8)
        && block.native["style"] == fixture.style && block.native["nav"] == fixture.navigation,
        "exact native body, stable block ID, styles and navigation across peers")
    let projected = try AnyInlineMarkdown(block.text).semanticText()
    let expectedText = edited ? "Changed" : "Anchor"
    let expectedRange = NSRange(location: "לפני ".utf16.count, length: expectedText.utf16.count)
    try require(projected.text == "לפני " + expectedText + " אחרי"
        && projected.marks == [.init(anchor: fixture.anchor, range: expectedRange)],
        "shared codec exact display text and one original marker")
    guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(fixture.anchor, read: read) else {
        throw ProbeError.failed("original semantic identity did not resolve on this native peer")
    }
    try require(fragments.count == 1 && fragments[0].blockID == fixture.blockID
        && fragments[0].range == expectedRange && fragments[0].text == expectedText,
        "actual current native resolution, without old-offset or visible-word fallback")
}

private func verifySemanticPeerState(fixture: SemanticPeerFixture, edited: Bool, linked: Bool,
    workspace: AnyTorahWorkspace, documents: AnyEditorDocumentStore,
    associations: AnyTorahAssociationRepository, owner: AnyApplicationSession) async throws {
    try require(workspace.spaceID == fixture.spaceID && fixture.version == 1
        && fixture.anchor.belongsTo(spaceID: fixture.spaceID, objectID: fixture.objectID),
        "fixture belongs to the actual shared native Space and object")
    try await owner.perform { lease in
        let before = try await documents.read(objectID: fixture.objectID, lease: lease)
        try verifySemanticPeerDocument(before, fixture: fixture, edited: edited)
        let snapshot = try await associations.snapshot(target: fixture.location.target, spaceID: workspace.spaceID)
        try require(snapshot.conflicts.isEmpty && snapshot.records.count == (linked ? 2 : 1),
                    "complete unambiguous canonical native claims")
        let canonical = try semanticPeerCanonical(snapshot.records)
        try require(canonical == (linked ? fixture.linkedCanonical : fixture.unlinkedCanonical),
                    "independently read canonical payload bytes equal the original input contract")
        for record in snapshot.records {
            try require(record.location == fixture.location, "canonical record owner must stay exact")
            let target = try TorahSemanticAnchorAssociation.decoding(record.item, location: record.location)
            if record.item.id == fixture.semanticItem.id {
                try require(linked && record.item == fixture.semanticItem && target?.anchor == fixture.anchor,
                            "canonical item identity and decoded semantic owner are exact")
            } else {
                try require(record.item == fixture.unrelatedItem && target == nil,
                            "unrelated canonical association stays byte-for-byte meaningful")
            }
        }
        let after = try await documents.read(objectID: fixture.objectID, lease: lease)
        try verifySemanticPeerDocument(after, fixture: fixture, edited: edited)
        try require(before.nativeVersion == after.nativeVersion && before.generation == after.generation
            && before.engineStartedAt == after.engineStartedAt,
            "native document remained stable around the canonical read")
        try await lease.validate()
    }
}

func runSemanticAnchorPeerProbe(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                                owner: AnyApplicationSession, arguments: [String]) async throws {
    guard let modeIndex = arguments.firstIndex(of: "--semantic-peer"), modeIndex + 1 < arguments.count,
          let fixtureIndex = arguments.firstIndex(of: "--semantic-fixture"), fixtureIndex + 1 < arguments.count else {
        throw ProbeError.usage
    }
    let mode = arguments[modeIndex + 1]
    let modes = ["prepare", "read-linked", "edit", "read-edited", "unlink", "read-unlinked"]
    try require(modes.contains(mode), "one explicit semantic native peer phase")
    if ["prepare", "edit", "unlink"].contains(mode) {
        try require(arguments.contains("--allow-disposable-writes"), "explicit disposable native writes required")
    }
    let fixturePath = arguments[fixtureIndex + 1]
    try require(fixturePath.hasPrefix("/"), "absolute private fixture path required")
    let fixtureURL = URL(fileURLWithPath: fixturePath)
    let documents = try AnyEditorDocumentStore(client: client, workspace: workspace,
        allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let operations = try AnyGuardedTorahOperationStore(client: client, workspace: workspace)
    let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
        allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let associations = try AnyTorahAssociationRepository(workspace: workspace, store: operations, access: access)
    var checks: [String] = []
    do {
        let fixture: SemanticPeerFixture
        if mode == "prepare" {
            try require(!FileManager.default.fileExists(atPath: fixturePath), "never overwrite an original peer fixture")
            let capability = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
            try require(capability["currentWriterObjectCreate"]?.integer == 1
                && capability["currentWriterBlockCreate"]?.integer == 1
                && capability["nativeDocumentTypePolicy"]?.integer == 1,
                "actual native guarded creation and document capabilities")
            let journal = CreationProbeJournal(workspace: workspace)
            let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
                allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
            let nonce = creationProbeMutationID()
            let title = "Semantic peer " + nonce
            fixture = try await owner.perform { lease in
                try await operations.repository.install { try await lease.validate() }
                let intent = try AnyNativeObjectCreationIntent(workspace: workspace, mutationID: nonce,
                    typeID: "page", initialProperties: .object(["any": .object(["name": .string(title)])]))
                let objectID = try await objects.ensureObject(intent, authorize: { try await lease.validate() })
                let blockIntent = try AnyNativeBlockCreationIntent(workspace: workspace,
                    mutationID: creationProbeMutationID(), objectID: objectID, type: "paragraph",
                    text: "לפני **Anchor** אחרי",
                    style: .object(["pinkhaWritingDirection": .string("rightToLeft"),
                        "semanticPeerUnknown": .object(["preserve": .bool(true)])]),
                    position: AnyLexicographicPosition.middle)
                let blockID = try await blocks.ensureBlock(blockIntent, authorize: { try await lease.validate() })
                let before = try await documents.read(objectID: objectID, lease: lease)
                let anchor = try PinkhaSemanticTextAnchor(spaceID: workspace.spaceID, objectID: objectID)
                let capture = try AnySemanticAnchorCapture(read: before, blockID: blockID,
                    range: NSRange(location: "לפני ".utf16.count, length: "Anchor".utf16.count), anchor: anchor)
                let prepared = try capture.prepare(current: before, documents: documents)
                let receipt = try await documents.apply(prepared, lease: lease)
                try require(receipt.readback == .verifiedCurrent, "real conditional marker native receipt")
                let captured = try await documents.read(objectID: objectID, lease: lease)
                try capture.verifyReadback(captured)
                guard let block = captured.snapshot.blocks.first(where: { $0.id == blockID }) else {
                    throw ProbeError.failed("captured original native block missing")
                }
                let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: .object(objectId: objectID))
                let time = Date(timeIntervalSince1970: 1_700_000_000)
                let source = TorahAssociationItem(id: "semantic-" + nonce, kind: .ref, role: .context,
                    providerID: "sefaria", externalID: "Genesis 1:1", canonicalKey: "Genesis 1:1",
                    labelHe: "בראשית א:א", labelEn: "Genesis 1:1", providerPayload: #"{"source":"native-peer-fixture"}"#,
                    createdAt: time, updatedAt: time, customMetadata: ["preserved": "שלום"],
                    unknownFields: ["futureItem": .object(["preserve": .bool(true)])])
                let semantic = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: source, location: location)
                let unrelated = TorahAssociationItem(id: "unrelated-" + nonce, kind: .ref, role: .context,
                    providerID: "sefaria", externalID: "Exodus 1:1", canonicalKey: "Exodus 1:1",
                    labelHe: "שמות א:א", createdAt: time, updatedAt: time)
                try require(try await associations.apply(semantic, target: location.target, spaceId: workspace.spaceID,
                    authorize: { try await lease.validate() }) == semantic, "native canonical semantic write")
                try require(try await associations.apply(unrelated, target: location.target, spaceId: workspace.spaceID,
                    authorize: { try await lease.validate() }) == unrelated, "native unrelated canonical write")
                let edited = try AnyInlineMarkdown(block.text).replacing(
                    displayRange: NSRange(location: "לפני ".utf16.count, length: "Anchor".utf16.count),
                    withLiteral: "Changed")
                return SemanticPeerFixture(version: 1, spaceID: workspace.spaceID,
                    creatorAccountID: workspace.accountID, objectID: objectID, blockID: blockID, title: title,
                    anchor: anchor, originalBody: capture.replacement, editedBody: edited,
                    style: block.native["style"], navigation: block.native["nav"], semanticItem: semantic,
                    unrelatedItem: unrelated,
                    linkedCanonical: try semanticPeerCanonical([.init(location: location, item: semantic),
                        .init(location: location, item: unrelated)]),
                    unlinkedCanonical: try semanticPeerCanonical([.init(location: location, item: unrelated)]))
            }
            try await verifySemanticPeerState(fixture: fixture, edited: false, linked: true,
                workspace: workspace, documents: documents, associations: associations, owner: owner)
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
            try encoder.encode(fixture).write(to: fixtureURL, options: .withoutOverwriting)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: fixturePath)
            checks.append("actual_guarded_native_marker_and_signed_canonical_claims")
        } else {
            let data = try Data(contentsOf: fixtureURL)
            try require(data.count <= 65_536, "bounded original private peer fixture")
            fixture = try JSONDecoder().decode(SemanticPeerFixture.self, from: data)
            if mode == "edit" {
                try require(workspace.accountID != fixture.creatorAccountID, "edit must use the independently invited writer")
                try await verifySemanticPeerState(fixture: fixture, edited: false, linked: true,
                    workspace: workspace, documents: documents, associations: associations, owner: owner)
                try await owner.perform { lease in
                    let before = try await documents.read(objectID: fixture.objectID, lease: lease)
                    try verifySemanticPeerDocument(before, fixture: fixture, edited: false)
                    let prepared = try documents.prepareTextEdit(before, blockID: fixture.blockID,
                        inlineMarkdown: fixture.editedBody)
                    let receipt = try await documents.apply(prepared, lease: lease)
                    try require(receipt.readback == .verifiedCurrent, "independent writer conditional native edit")
                }
                checks.append("distinct_invited_account_real_conditional_edit_preserves_marker")
            } else if mode == "unlink" {
                try require(workspace.accountID == fixture.creatorAccountID, "unlink must return to the original owner")
                try await verifySemanticPeerState(fixture: fixture, edited: true, linked: true,
                    workspace: workspace, documents: documents, associations: associations, owner: owner)
                try await owner.perform { lease in
                    try await associations.removeAssociation(associationId: fixture.semanticItem.id,
                        target: fixture.location.target, spaceId: workspace.spaceID,
                        authorize: { try await lease.validate() })
                }
                checks.append("original_owner_removes_only_exact_semantic_association")
            }
            try await verifySemanticPeerState(fixture: fixture, edited: mode != "read-linked",
                linked: !["unlink", "read-unlinked"].contains(mode), workspace: workspace,
                documents: documents, associations: associations, owner: owner)
        }
        checks.append("authoritative_native_body_marker_and_canonical_payload_equality")
        await owner.revokeAndDrain()
        checks.append("native_application_lease_drained")
        let result: AnyJSON = .object(["status": .string("PASS"), "phase": .string(mode),
            "scope": .string("shared_semantic_codec_and_signed_native_repository_on_actual_peer"),
            "uiAcceptance": .bool(false), "physicalDevice": .bool(false),
            "networkAndColdProcessProof": .string("required_from_independent_controller"),
            "checks": .array(checks.map(AnyJSON.string))])
        print(String(decoding: try JSONEncoder().encode(result), as: UTF8.self))
    } catch {
        await owner.revokeAndDrain()
        throw error
    }
}

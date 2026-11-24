import Foundation
import CryptoKit
import Services
import SwiftProtobuf
import ProtobufMessages

/// The only writers used to construct a private draft are the original native
/// ObjectCreate/block commands or the original closed Annotation.Import owner.
/// A returned ID becomes a private observation only after actual native drain
/// and a fresh ObjectShow in the independently selected account and Space.
@MainActor
internal enum OriginalEditorLocalAnnotationMaterialization {
    static func materialize(
        canonical: OriginalEditorLocalAnnotationCanonical,
        source: AnytypeOriginalEditorLocalAnnotationSource,
        draft: OriginalEditorLocalAnnotationJournal.Draft,
        accountID: String,
        selection: OriginalActiveSpaceSelection,
        annotationTypeID: String,
        binding: EditorDocumentWriteSourceBinding,
        sourceIsCurrent: @escaping @MainActor () throws -> Void
    ) async throws -> String {
        try sourceIsCurrent()
        try selection.validate()
        let spaceID = selection.accountInfo.accountSpaceId
        guard draft.phase == "materialization_may_have_dispatched",
              draft.spaceID == spaceID, draft.spaceViewID == selection.accountInfo.spaceViewId,
              draft.profile == source.hostProfileID, draft.annotationUUID == source.annotationUUID,
              draft.revision == source.expectedRevision,
              draft.sourceSHA256 == source.sourceWitnessSHA256,
              draft.payloadSHA256 == source.payloadSHA256,
              draft.canonicalSHA256 == canonical.digest,
              selection.accountID == accountID, !annotationTypeID.isEmpty else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidJournal
        }

        let objectID: String
        switch canonical.body {
        case .plainText(let text):
            let drain = OriginalEditorLocalAnnotationDrain()
            objectID = try await binding.performOperation(
                rpcNames: ["ObjectCreate", "ObjectShow", "BlockCreate", "BlockTextSetText"],
                onDrained: { drain.finish() }
            ) {
                try await createPlain(text: text, source: source, spaceID: spaceID,
                                      annotationTypeID: annotationTypeID)
            }
            await drain.wait()
            guard drain.count == 1 else {
                throw AnytypeOriginalEditorLocalAnnotationError.uncertainNativeOperation
            }
        case .nativeSnapshot(let snapshot):
            let drain = OriginalEditorLocalAnnotationImportDrain()
            let attempt = try binding.prepareOriginalAnnotationImport(
                selection: selection, sourceSpaceID: snapshot.provenance.spaceID,
                sourceRootID: snapshot.provenance.objectID, archive: snapshot.nativeArchiveBytes,
                onDrained: { drain.receive($0) }
            )
            // The journal transition above was persisted before preparing this
            // one-use handle. No guessed process ID or global ImportFinish event
            // stands in for its actual import and optional cancellation drains.
            let returned = try await attempt.invoke()
            await drain.signal.wait()
            guard drain.signal.count == 1, let history = drain.history,
                  history.responseCopyError == nil, history.cancellationCopyError == nil,
                  !history.cancellationWasScheduled, !history.cancellationAwaitFailed,
                  history.cancellationResponse == nil, history.response == returned,
                  attempt.drainedHistory?.response == returned else {
                throw AnytypeOriginalEditorLocalAnnotationError.invalidNativeImport
            }
            objectID = try observedImport(returned, snapshot: snapshot,
                accountID: accountID, targetSpaceID: spaceID, source: source)
        }

        try sourceIsCurrent()
        try selection.validate()
        let readDrain = OriginalEditorLocalAnnotationDrain()
        let view = try await binding.performRead(rpcNames: ["ObjectShow"],
                                                onDrained: { readDrain.finish() }) {
            try await show(objectID: objectID, spaceID: spaceID)
        }
        await readDrain.wait()
        guard readDrain.count == 1 else {
            throw AnytypeOriginalEditorLocalAnnotationError.uncertainNativeOperation
        }
        try sourceIsCurrent()
        try selection.validate()
        try requireIdentity(view, objectID: objectID, spaceID: spaceID,
                            annotationTypeID: annotationTypeID, source: source)
        return objectID
    }

    private static func createPlain(text: String, source: AnytypeOriginalEditorLocalAnnotationSource,
                                    spaceID: String, annotationTypeID: String) async throws -> String {
        let created = try await ClientCommands.objectCreate(.with {
            $0.spaceID = spaceID
            $0.objectTypeUniqueKey = OriginalAnnotationNativeMetadata.originalTypeUniqueKey
            $0.details = privateDetails(source: source)
            // Keep original annotation type/layout. No page promotion, template
            // override, select-type or delete-empty editor flags are introduced.
        }).invoke()
        guard created.error.code == .null, !created.objectID.isEmpty, created.hasDetails,
              OriginalEditorLocalAnnotationNativeBody.string(created.details, "id") == created.objectID,
              OriginalEditorLocalAnnotationNativeBody.string(created.details, "spaceId") == spaceID else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        let objectID = created.objectID
        let initial = try await show(objectID: objectID, spaceID: spaceID)
        try requireIdentity(initial, objectID: objectID, spaceID: spaceID,
                            annotationTypeID: annotationTypeID, source: source)
        let paragraphs = initial.blocks.filter {
            guard case .text(let value)? = $0.content else { return false }
            return value.style == .paragraph
        }
        // A newly created original annotation may have its native empty text
        // block already. Adopt only that observed empty block; never overwrite
        // an unexpected native template/user body to make seeding succeed.
        guard paragraphs.count <= 1, initial.blocks.allSatisfy({ block in
            guard case .text(let value)? = block.content else { return true }
            return value.text.isEmpty && value.marks.marks.isEmpty
        }) else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        let textID: String
        if let paragraph = paragraphs.first {
            textID = paragraph.id
            let changed = try await ClientCommands.blockTextSetText(.with {
                $0.contextID = objectID; $0.blockID = paragraph.id; $0.text = text
            }).invoke()
            guard changed.error.code == .null else {
                throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
            }
        } else {
            let block = try await ClientCommands.blockCreate(.with {
                $0.contextID = objectID; $0.targetID = objectID; $0.position = .inner
                $0.block = .with { $0.text = .with { $0.text = text } }
            }).invoke()
            guard block.error.code == .null, !block.blockID.isEmpty else {
                throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
            }
            textID = block.blockID
        }
        let observed = try await show(objectID: objectID, spaceID: spaceID)
        try requireIdentity(observed, objectID: objectID, spaceID: spaceID,
                            annotationTypeID: annotationTypeID, source: source)
        let matching = observed.blocks.filter { $0.id == textID }
        guard matching.count == 1, case .text(let actual)? = matching.first?.content,
              actual.style == .paragraph, actual.text.utf8.elementsEqual(text.utf8),
              actual.marks.marks.isEmpty,
              observed.blocks.allSatisfy({ block in
                  guard block.id != textID, case .text(let value)? = block.content else { return true }
                  return value.text.isEmpty
              }) else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        return objectID
    }

    private static func privateDetails(source: AnytypeOriginalEditorLocalAnnotationSource) -> Google_Protobuf_Struct {
        let fields: [String: String] = [
            "name": "",
            OriginalAnnotationMetadataField.schemaProtocol.rawValue: OriginalAnnotationNativeMetadata.protocolValue,
            OriginalAnnotationMetadataField.classification.rawValue: "annotation",
            OriginalAnnotationMetadataField.namespace.rawValue: "otzaria.local.annotation",
            OriginalAnnotationMetadataField.annotationUUID.rawValue: source.annotationUUID.uuidString,
            OriginalAnnotationMetadataField.creationDestination.rawValue: "otzaria.local.draft:" + source.hostProfileID
        ]
        return .with { details in
            for (key, value) in fields { details.fields[key] = .with { $0.stringValue = value } }
        }
    }

    private static func observedImport(_ response: Anytype_Rpc.Annotation.Import.Response,
                                       snapshot: AnytypeOriginalEditorSnapshot,
                                       accountID: String, targetSpaceID: String,
                                       source: AnytypeOriginalEditorLocalAnnotationSource) throws -> String {
        let inputDigest = Data(SHA256.hash(data: snapshot.nativeArchiveBytes))
        guard response.error.code == .null, response.importProtocol == "pinkha.annotation.import.v1",
              response.registered, response.operationDone, response.copyDisposition == .complete,
              !response.nativeErrorPresent, response.nativeErrorCategory == .none,
              !response.cancellationRequested, response.hasOutcome, response.hasMapping, response.hasReadback else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidNativeImport
        }
        let mapping = response.mapping, readback = response.readback
        guard response.outcome.targetSpaceID == targetSpaceID, response.outcome.objectsCount > 0,
              response.outcome.files.allSatisfy({ !$0.nativeErrorPresent && $0.nativeErrorCategory == .none }),
              mapping.observed, mapping.completeForSelectedSnapshots, !mapping.traceID.isEmpty,
              mapping.targetSpaceID == targetSpaceID,
              !mapping.nonInjectiveDestinations, mapping.problems.isEmpty,
              readback.observed,
              // Exact original Heart OwnedAnnotationBodyMatched (iota 3),
              // reached only after its full native graph/body/file comparison.
              readback.stage == 3, readback.accountID == accountID, readback.spaceID == targetSpaceID,
              !readback.rootID.isEmpty, readback.sourceArchiveSha256 == inputDigest,
              readback.nativeArchiveSha256 == Data(SHA256.hash(data: readback.nativeArchive)),
              readback.sourceSnapshots > 0, readback.annotationPages > 0,
              readback.hasExportReport, readback.exportReport.status == .success,
              readback.exportReport.succeed > 0, readback.exportReport.objectErrors == 0,
              readback.exportReport.fileErrors == 0, readback.exportReport.issues.isEmpty else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidNativeImport
        }
        let assigned = mapping.sourceAssignments.filter {
            $0.sourceSpaceID == snapshot.provenance.spaceID && $0.sourceObjectID == snapshot.provenance.objectID
        }
        guard assigned.count == 1, let root = assigned.first,
              root.sourceArchiveSha256 == inputDigest, root.nativeID == readback.rootID,
              root.memberPath == "objects/" + snapshot.provenance.objectID + ".pb",
              !root.converterID.isEmpty else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidNativeImport
        }
        // Parse the genuine same-operation export as data. It is never framed
        // as a new saved snapshot, nor used as current selected-Space authority.
        let archive = try OriginalAnnotationNativeArchiveComparison(
            archiveBytes: readback.nativeArchive, rootID: readback.rootID,
            spaceID: targetSpaceID, formatVersion: AnytypeOriginalEditorSnapshot.formatVersion,
            reportedObjectCount: readback.exportReport.succeed)
        try OriginalEditorLocalAnnotationNativeBody.requireMarkers(archive.rootSnapshot.details, source: source)
        return readback.rootID
    }

    private static func show(objectID: String, spaceID: String) async throws -> Anytype_Model_ObjectView {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
        }).invoke()
        guard response.error.code == .null, response.hasObjectView else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        return response.objectView
    }

    private static func requireIdentity(_ view: Anytype_Model_ObjectView, objectID: String,
                                        spaceID: String, annotationTypeID: String,
                                        source: AnytypeOriginalEditorLocalAnnotationSource) throws {
        let details = view.details.filter { $0.id == objectID }
        let blockIDs = view.blocks.map(\.id)
        guard view.rootID == objectID, details.count == 1, let detail = details.first,
              detail.hasDetails, !blockIDs.isEmpty, !blockIDs.contains(""),
              Set(blockIDs).count == blockIDs.count, blockIDs.contains(objectID),
              OriginalEditorLocalAnnotationNativeBody.string(detail.details, "id") == objectID,
              OriginalEditorLocalAnnotationNativeBody.string(detail.details, "spaceId") == spaceID,
              case .listValue(let types)? = detail.details.fields["type"]?.kind,
              types.values.count == 1,
              case .stringValue(let type)? = types.values.first?.kind, type == annotationTypeID else {
            throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
        }
        try OriginalEditorLocalAnnotationNativeBody.requireMarkers(detail.details, source: source)
        for key in ["isArchived", "isDeleted"] {
            guard let field = detail.details.fields[key] else { continue }
            guard case .boolValue(false)? = field.kind else {
                throw AnytypeOriginalEditorLocalAnnotationError.wrongNativeIdentity
            }
        }
    }
}

/// The real original onDrained callback is the only completion signal. A timer,
/// cancelled Swift waiter, guessed empty native index or ImportFinish event can
/// neither set it nor release the original native admissions.
@MainActor
private final class OriginalEditorLocalAnnotationDrain {
    private(set) var count = 0
    private var waiter: CheckedContinuation<Void, Never>?
    func finish() {
        count += 1
        let continuation = waiter
        waiter = nil
        continuation?.resume()
    }
    func wait() async {
        guard count == 0 else { return }
        await withCheckedContinuation { waiter = $0 }
    }
}

@MainActor
private final class OriginalEditorLocalAnnotationImportDrain {
    let signal = OriginalEditorLocalAnnotationDrain()
    private(set) var history: OriginalAnnotationImportCallHistory?
    func receive(_ actual: OriginalAnnotationImportCallHistory) {
        if history == nil { history = actual }
        signal.finish()
    }
}

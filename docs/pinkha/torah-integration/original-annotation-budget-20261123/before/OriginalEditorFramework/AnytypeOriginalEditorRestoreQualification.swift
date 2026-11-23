#if DEBUG && targetEnvironment(simulator)
import Foundation
import ProtobufMessages
import SwiftProtobuf

/// A real imported candidate with original completion and root-map evidence.
/// The acceptance consumer must still reopen/mount it through the original
/// Host and compare its native blocks, marks, links and file bytes. This value
/// alone does not claim that a full editor round trip has passed.
internal struct AnytypeOriginalEditorImportedCandidate: Sendable {
    let accountID: String
    let spaceID: String
    let objectID: String
    let originalObjectID: String
    let capturedProvenance: AnytypeOriginalEditorSnapshot.Provenance
    let runtimeNonce: UUID
    let rootCollectionID: String
    let importProcessID: String
    let nativeObjectViewBytes: Data
    let retainedEvidenceDirectory: URL
}

internal enum AnytypeOriginalEditorRestoreQualificationError: Error, Sendable {
    case invalidQualificationScope, alreadyPresent, ambiguousRoot
    case incompleteImport, unrelatedImport, duplicateCompletion, nativeIdentityMismatch
    case completionTimeout, eventEvidenceLimit
}

internal struct AnytypeOriginalEditorRestoreQualificationFailure: Error {
    let retainedEvidenceDirectory: URL
    let underlyingError: any Error
}

/// Qualification-only import. OwnedQualificationSpace has no public initializer:
/// the original runtime mints it only from a new private Space in its exclusively
/// created local-only acceptance account. No caller-supplied Space is admitted.
internal enum AnytypeOriginalEditorRestoreQualification {
    @MainActor
    static func importCandidate(
        snapshot: AnytypeOriginalEditorSnapshot,
        into target: OwnedQualificationSpace,
        timeoutSeconds: Int = 90
    ) async throws -> AnytypeOriginalEditorImportedCandidate {
        try target.validateCurrentRuntime()
        let accountID = target.accountID
        let spaceID = target.spaceID
        let runtimeNonce = target.runtimeNonce
        let source = snapshot.provenance
        guard timeoutSeconds > 0, timeoutSeconds <= 120,
              source.accountID.utf8.elementsEqual(accountID.utf8),
              !source.spaceID.utf8.elementsEqual(spaceID.utf8),
              [source.spaceID, source.objectID].allSatisfy({
                  !$0.isEmpty && !$0.contains("/") && !$0.contains("\\") && !$0.utf8.contains(0)
              }) else {
            throw AnytypeOriginalEditorRestoreQualificationError.invalidQualificationScope
        }
        try target.claimForImport()
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        let archiveURL = directory.appendingPathComponent("original-native-import.zip")
        do {
            try snapshot.nativeArchiveBytes.write(to: archiveURL, options: .withoutOverwriting)
            let expectedSourcePath = source.spaceID + "/" + source.objectID
            // The runtime reservation spans the asynchronous import's REAL
            // completion, not merely the immediately returning Lib RPC. On any
            // failure this one-use Space remains consumed and retained.
            let candidate = try await target.performRPCs(
                rpcNames: ["ObjectImport", "ObjectSearch", "ObjectShow"]
            ) {
                // Native existing-object matching checks oldAnytypeID and then
                // uniqueKey even with updateExistingObjects=false. Refuse a
                // collision independently for both keys before any import.
                for key in ["oldAnytypeID", "uniqueKey"] {
                    let before = try await search(
                        spaceID: spaceID, equalities: [(key, source.objectID)]
                    )
                    try retain(before, named: "before-" + key + ".pb", in: directory)
                    guard before.total == 0, before.records.isEmpty else {
                        throw AnytypeOriginalEditorRestoreQualificationError.alreadyPresent
                    }
                }
                let originalBytes = try OriginalEditorArchiveFiles.readArchive(
                    archiveURL, in: directory, maximumBytes: 65_536
                )
                guard originalBytes == snapshot.nativeArchiveBytes else {
                    throw AnytypeOriginalEditorSnapshotError.archiveChanged
                }
                let observer = OriginalImportCompletionObserver(spaceID: spaceID, directory: directory)
                ServiceMessageHandlerAdapter.shared.addHandler(handler: observer)
                let accepted = try await ClientCommands.objectImport(.with {
                    $0.spaceID = spaceID
                    $0.type = .pb
                    $0.mode = .allOrNothing
                    $0.updateExistingObjects = false
                    $0.isMigration = false
                    $0.isNewSpace = false
                    // A real progress process produces a scoped final native
                    // notification; noProgress=true would suppress that proof.
                    $0.noProgress = false
                    $0.pbParams = .with {
                        $0.path = [archiveURL.path]
                        $0.noCollection = false
                        $0.importType = .space
                    }
                }).invoke()
                try retain(accepted, named: "import-rpc-accepted-not-complete.pb", in: directory)
                let completion = try await waitForCompletion(observer, timeoutSeconds: timeoutSeconds)

                // ImportFinish itself has no Space or process ID. Require its
                // collection to exist in exactly the freshly owned target.
                let collectionSearch = try await search(
                    spaceID: spaceID, equalities: [("id", completion.finish.rootCollectionID)]
                )
                try retain(collectionSearch, named: "finish-collection-query.pb", in: directory)
                let collection = try uniqueRecord(collectionSearch)
                try requireString(collection, "id", equals: completion.finish.rootCollectionID)
                try requireString(collection, "spaceId", equals: spaceID)

                let mappedSearch = try await search(
                    spaceID: spaceID,
                    equalities: [("oldAnytypeID", source.objectID), ("sourceFilePath", expectedSourcePath)]
                )
                try retain(mappedSearch, named: "imported-root-query.pb", in: directory)
                let mapped = try uniqueRecord(mappedSearch)
                let objectID = try string(mapped, "id")
                try requireString(mapped, "spaceId", equals: spaceID)
                try requireString(mapped, "oldAnytypeID", equals: source.objectID)
                try requireString(mapped, "sourceFilePath", equals: expectedSourcePath)
                let shown = try await ClientCommands.objectShow(.with {
                    $0.contextID = objectID
                    $0.objectID = objectID
                    $0.spaceID = spaceID
                }).invoke()
                try retain(shown, named: "original-restored-object-show.pb", in: directory)
                guard shown.hasObjectView,
                      shown.objectView.rootID.utf8.elementsEqual(objectID.utf8),
                      !shown.objectView.blocks.isEmpty else {
                    throw AnytypeOriginalEditorRestoreQualificationError.nativeIdentityMismatch
                }
                let rootDetails = shown.objectView.details.filter { $0.id.utf8.elementsEqual(objectID.utf8) }
                guard rootDetails.count == 1, rootDetails[0].hasDetails else {
                    throw AnytypeOriginalEditorRestoreQualificationError.nativeIdentityMismatch
                }
                try requireString(rootDetails[0].details, "spaceId", equals: spaceID)
                try requireString(rootDetails[0].details, "oldAnytypeID", equals: source.objectID)
                try requireString(rootDetails[0].details, "sourceFilePath", equals: expectedSourcePath)
                guard try OriginalEditorArchiveFiles.readArchive(
                    archiveURL, in: directory, maximumBytes: 65_536
                ) == originalBytes else {
                    throw AnytypeOriginalEditorSnapshotError.archiveChanged
                }
                let receipt: [String: Any] = [
                    "scope": "original native import completed and unique root mapped; editor/file round-trip acceptance still required",
                    "runtimeNonce": runtimeNonce.uuidString,
                    "accountID": accountID, "targetSpaceID": spaceID,
                    "sourceSpaceID": source.spaceID, "sourceObjectID": source.objectID,
                    "mappedObjectID": objectID,
                    "rootCollectionID": completion.finish.rootCollectionID,
                    "importProcessID": completion.notification.import.processID,
                    "objectsCount": completion.finish.objectsCount,
                    "archiveSHA256": snapshot.nativeArchiveSHA256,
                    "capturedAgainstRevision": source.capturedAgainstRevision,
                ]
                try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys, .withoutEscapingSlashes])
                    .write(to: directory.appendingPathComponent("native-root-map.json"), options: .withoutOverwriting)
                return AnytypeOriginalEditorImportedCandidate(
                    accountID: accountID, spaceID: spaceID, objectID: objectID,
                    originalObjectID: source.objectID, capturedProvenance: source, runtimeNonce: runtimeNonce,
                    rootCollectionID: completion.finish.rootCollectionID,
                    importProcessID: completion.notification.import.processID,
                    nativeObjectViewBytes: try shown.objectView.serializedData(),
                    retainedEvidenceDirectory: directory
                )
            }
            try target.validateCurrentRuntime()
            return candidate
        } catch {
            // No cleanup, rollback, second import or automatic account switch.
            throw AnytypeOriginalEditorRestoreQualificationFailure(
                retainedEvidenceDirectory: directory, underlyingError: error
            )
        }
    }

    private static func search(
        spaceID: String, equalities: [(String, String)]
    ) async throws -> Anytype_Rpc.Object.Search.Response {
        try await ClientCommands.objectSearch(.with {
            $0.spaceID = spaceID
            $0.limit = 2
            $0.needTotal = true
            $0.keys = ["id", "spaceId", "oldAnytypeID", "sourceFilePath", "uniqueKey"]
            $0.filters = equalities.map { key, value in
                .with {
                    $0.relationKey = key
                    $0.condition = .equal
                    $0.value = .with { $0.stringValue = value }
                }
            }
        }).invoke()
    }

    private static func uniqueRecord(_ response: Anytype_Rpc.Object.Search.Response) throws -> Google_Protobuf_Struct {
        guard response.total == 1, response.records.count == 1 else {
            throw AnytypeOriginalEditorRestoreQualificationError.ambiguousRoot
        }
        return response.records[0]
    }

    private static func string(_ record: Google_Protobuf_Struct, _ key: String) throws -> String {
        guard let value = record.fields[key], case .stringValue(let text)? = value.kind, !text.isEmpty else {
            throw AnytypeOriginalEditorRestoreQualificationError.nativeIdentityMismatch
        }
        return text
    }

    private static func requireString(_ record: Google_Protobuf_Struct, _ key: String, equals expected: String) throws {
        guard try string(record, key).utf8.elementsEqual(expected.utf8) else {
            throw AnytypeOriginalEditorRestoreQualificationError.nativeIdentityMismatch
        }
    }

    private static func retain<M: SwiftProtobuf.Message>(_ message: M, named name: String, in directory: URL) throws {
        try message.serializedData().write(to: directory.appendingPathComponent(name), options: .withoutOverwriting)
    }

    private static func waitForCompletion(
        _ observer: OriginalImportCompletionObserver, timeoutSeconds: Int
    ) async throws -> OriginalImportCompletion {
        try await withThrowingTaskGroup(of: OriginalImportCompletion.self) { group in
            group.addTask {
                for try await completion in observer.completions { return completion }
                throw AnytypeOriginalEditorRestoreQualificationError.incompleteImport
            }
            group.addTask {
                try await Task.sleep(nanoseconds: UInt64(timeoutSeconds) * 1_000_000_000)
                throw AnytypeOriginalEditorRestoreQualificationError.completionTimeout
            }
            defer { group.cancelAll() }
            guard let completion = try await group.next() else {
                throw AnytypeOriginalEditorRestoreQualificationError.incompleteImport
            }
            return completion
        }
    }
}

private struct OriginalImportCompletion: Sendable {
    let notification: Anytype_Model_Notification
    let finish: Anytype_Event.Import.Finish
}

/// Additive observer of the original serialized FIFO event adapter. Notification
/// delivery runs on the native process monitor and may arrive before OR after
/// ImportFinish; neither event is inferred from the other or from RPC return.
private actor OriginalImportCompletionObserver: ServiceEventsHandlerProtocol {
    nonisolated let completions: AsyncThrowingStream<OriginalImportCompletion, any Error>
    private let continuation: AsyncThrowingStream<OriginalImportCompletion, any Error>.Continuation
    private let spaceID: String
    private let directory: URL
    private var notification: Anytype_Model_Notification?
    private var finish: Anytype_Event.Import.Finish?
    private var eventCount = 0
    private var finished = false

    init(spaceID: String, directory: URL) {
        self.spaceID = spaceID
        self.directory = directory
        let pair = AsyncThrowingStream<OriginalImportCompletion, any Error>.makeStream(bufferingPolicy: .bufferingOldest(1))
        completions = pair.stream
        continuation = pair.continuation
    }

    func handle(_ event: Anytype_Event) async {
        guard !finished else { return }
        do {
            for message in event.messages {
                switch message.value {
                case .notificationSend(let sent)?:
                    guard sent.hasNotification,
                          case .import(let detail)? = sent.notification.payload,
                          detail.importType == .pb else { continue }
                    try retain(event)
                    guard detail.spaceID.utf8.elementsEqual(spaceID.utf8) else {
                        throw AnytypeOriginalEditorRestoreQualificationError.unrelatedImport
                    }
                    guard notification == nil else {
                        throw AnytypeOriginalEditorRestoreQualificationError.duplicateCompletion
                    }
                    guard !sent.notification.id.isEmpty, !detail.processID.isEmpty,
                          detail.errorCode == .null, detail.issuesCount == 0, detail.reportObjectID.isEmpty else {
                        throw AnytypeOriginalEditorRestoreQualificationError.incompleteImport
                    }
                    notification = sent.notification
                case .importFinish(let result)? where result.importType == .pb:
                    try retain(event)
                    guard finish == nil else {
                        throw AnytypeOriginalEditorRestoreQualificationError.duplicateCompletion
                    }
                    guard !result.rootCollectionID.isEmpty, result.objectsCount > 0,
                          result.issuesCount == 0, result.reportObjectID.isEmpty else {
                        throw AnytypeOriginalEditorRestoreQualificationError.incompleteImport
                    }
                    finish = result
                default:
                    continue
                }
            }
            if let notification, let finish {
                finished = true
                continuation.yield(.init(notification: notification, finish: finish))
                continuation.finish()
            }
        } catch {
            finished = true
            continuation.finish(throwing: error)
        }
    }

    private func retain(_ event: Anytype_Event) throws {
        guard eventCount < 8 else { throw AnytypeOriginalEditorRestoreQualificationError.eventEvidenceLimit }
        let bytes = try event.serializedData()
        guard bytes.count <= 262_144 else { throw AnytypeOriginalEditorRestoreQualificationError.eventEvidenceLimit }
        let filename = String(format: "import-event-%02d.pb", eventCount)
        try bytes.write(to: directory.appendingPathComponent(filename), options: .withoutOverwriting)
        eventCount += 1
    }
}
#endif

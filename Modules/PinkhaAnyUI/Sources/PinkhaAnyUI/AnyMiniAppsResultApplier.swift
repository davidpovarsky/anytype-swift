#if canImport(UIKit) && canImport(HanlinMiniAppsBridge)
import Foundation
import CryptoKit
import UniformTypeIdentifiers
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaHanlinUI
import HanlinMiniAppsBridge

enum AnyMiniAppsResultApplier {
    @MainActor
    static func apply(request: MiniAppInvocation, result: MiniAppResult,
                      document: AnyDocumentPresentation, store: MiniAppBridgeStore) async throws -> Bool {
        guard result.status == .success, request.id == result.requestID,
              AnyMiniAppsCodec.matches(request, document: document) else { throw MiniAppBridgeError.wrongSource }
        let workspace = document.workspace, objectID = document.objectID
        let documents = document.documents, client = document.client
        let journal = try AnyMiniAppsJournal(request: request, result: result, workspace: workspace, objectID: objectID)
        let preserved = try await document.performMiniAppsMutation { lease, authorize in
            var record: AnyMiniAppsJournalRecord
            if let existing = try journal.load() { record = existing }
            else {
                record = .init(requestDigest: journal.requestDigest, resultDigest: journal.resultDigest,
                               plan: try PinkhaMiniAppsEditPlanner.make(request: request, result: result))
                try journal.save(record)
            }
            guard record.plan.requestID == request.id else { throw MiniAppBridgeError.conflictingResult }
            var current = try await documents.read(objectID: objectID, lease: lease)
            if record.plan.completed { return (record.plan.preservedNewerContent, current, nil) }

            // Preserve newer content in full before the first write. A partially
            // applied plan never repeats its output merely to hide a conflict.
            var changed = false
            for mutation in record.plan.mutations where !record.plan.appliedBlocks.contains(mutation.before.id) {
                let before = try JSONDecoder().decode(AnyMiniAppsBlockMetadata.self, from: mutation.before.marks)
                let expected = try before.replacing(mutation)
                guard let block = current.snapshot.blocks.first(where: { $0.id == mutation.before.id }),
                      current.snapshot.depthFirstIDs.contains(block.id) else { changed = true; continue }
                let actual = AnyMiniAppsBlockMetadata(block)
                if actual != before && actual != expected { changed = true }
            }
            if changed {
                guard record.plan.appliedBlocks.isEmpty, record.plan.insertedBlocks.isEmpty, record.files.isEmpty else {
                    throw MiniAppBridgeError.selectionChanged
                }
                record.plan.mutations = []
                record.plan.additions = result.items
                record.plan.preservedNewerContent = true
                try journal.save(record)
            }

            var lastUndo: AnyPreparedBlockEdit?
            for mutation in record.plan.mutations where !record.plan.appliedBlocks.contains(mutation.before.id) {
                try await authorize(); try await lease.validate()
                current = try await documents.read(objectID: objectID, lease: lease)
                guard let block = current.snapshot.blocks.first(where: { $0.id == mutation.before.id }),
                      current.snapshot.depthFirstIDs.contains(block.id) else { throw MiniAppBridgeError.selectionChanged }
                let before = try JSONDecoder().decode(AnyMiniAppsBlockMetadata.self, from: mutation.before.marks)
                let expected = try before.replacing(mutation)
                let actual = AnyMiniAppsBlockMetadata(block)
                if actual == before {
                    let edit = try documents.prepareTextEdit(current, blockID: block.id, inlineMarkdown: expected.inlineMarkdown)
                    let receipt = try await documents.apply(edit, lease: lease, authorize: authorize)
                    guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                    current = try await documents.read(objectID: objectID, lease: lease)
                    guard let verified = current.snapshot.blocks.first(where: { $0.id == block.id }),
                          AnyMiniAppsBlockMetadata(verified) == expected else { throw AnyHostError.writeUncertain }
                    record.nativeVersions[block.id] = receipt.nativeVersionID
                    lastUndo = receipt.undo
                } else if actual == expected {
                    // A lost prior reply may be reconciled only with the exact
                    // stored source, formatting and requested native result.
                    record.nativeVersions[block.id] = current.nativeVersion
                    lastUndo = nil
                } else { throw MiniAppBridgeError.selectionChanged }
                record.plan.appliedBlocks.insert(block.id)
                try journal.save(record)
            }

            if !record.plan.additions.isEmpty {
                let native = try await AnyNativePreparedMigration.open(client: client, workspace: workspace, authorize: authorize)
                if let prior = record.nativeStoreID, prior != native.capabilities.storeID {
                    throw AnyPreparedMigrationError.changedStore
                }
                record.nativeStoreID = native.capabilities.storeID
                try journal.save(record)
                let planID = try AnyMiniAppsCodec.digest(["pinkha-any-miniapps/v1", workspace.accountID,
                    workspace.spaceID, objectID, request.id.uuidString.lowercased()])
                let binding = try AnyPreparedMigrationPlanBinding(workspace: workspace,
                    storeID: native.capabilities.storeID, planID: planID,
                    planSHA256: try AnyMiniAppsCodec.digest([journal.requestDigest, journal.resultDigest]))

                for (index, item) in record.plan.additions.enumerated() {
                    let key = "miniapps-result-\(index)"
                    try await authorize(); try await lease.validate()
                    if item.kind == .file {
                        if record.files[key] != nil { continue }
                        let receipt = try await attachFile(item, key: key, binding: binding, objectID: objectID,
                            client: client, store: store, lease: lease, authorize: authorize)
                        record.files[key] = receipt
                        try journal.save(record)
                        lastUndo = nil
                        continue
                    }
                    if record.plan.insertedBlocks[key] != nil { continue }
                    let text: String
                    switch item.kind {
                    case .text, .json: text = AnyInlineMarkdown.escapeLiteral(item.text ?? "")
                    case .url:
                        guard let url = item.url, ["http", "https", "mailto"].contains(url.scheme?.lowercased() ?? "") else {
                            throw MiniAppBridgeError.invalidURL
                        }
                        // A native text value keeps the original URL intact;
                        // no local control-server URL or credentials are stored.
                        text = AnyInlineMarkdown.escapeLiteral(url.absoluteString)
                    case .file: throw MiniAppBridgeError.invalidAttachment
                    }
                    let intent: AnyNativeBlockCreationIntent
                    if let existing = record.blockIntents[key] { intent = existing }
                    else {
                        current = try await documents.read(objectID: objectID, lease: lease)
                        let placement = try AnyNativeBlockInsertionPosition.resolve(
                            snapshot: current.snapshot, policy: .afterLastVisibleBlock)
                        intent = try .init(workspace: workspace,
                            mutationID: String(AnyContentDigest.sha256(Data((planID + ":" + key).utf8)).prefix(32)),
                            objectID: objectID, type: "paragraph", text: text,
                            parentID: placement.parentID, position: placement.position)
                        record.blockIntents[key] = intent
                        try journal.save(record)
                    }
                    guard intent.text == text, intent.objectID == objectID, intent.workspace == workspace else {
                        throw MiniAppBridgeError.conflictingResult
                    }
                    let preparedIntent = try AnyPreparedMigrationIntent.block(binding: binding, sourceKey: key,
                        objectID: objectID, dataset: intent.dataset, type: intent.type, text: intent.text,
                        style: intent.style, parentID: intent.parentID, position: intent.position)
                    let prepared = try await native.prepare(preparedIntent, authorize: authorize)
                    let receipt = try await native.commit(prepared, authorize: authorize)
                    guard receipt.isCompleteAndCurrent, receipt.recordIDs.count == 1,
                          let id = receipt.recordIDs.first else { throw AnyPreparedMigrationError.incompleteCommit }
                    current = try await documents.read(objectID: objectID, lease: lease)
                    guard let block = current.snapshot.blocks.first(where: { $0.id == id }),
                          current.snapshot.depthFirstIDs.contains(id), block.type == intent.type,
                          block.text == intent.text, block.parentID == intent.parentID,
                          block.position == intent.position else { throw AnyHostError.writeUncertain }
                    record.plan.insertedBlocks[key] = id
                    if let change = receipt.changeID { record.nativeVersions[id] = change }
                    try journal.save(record)
                    lastUndo = nil
                }
            }
            current = try await documents.read(objectID: objectID, lease: lease)
            try await authorize(); try await lease.validate()
            record.plan.completed = true
            try journal.save(record)
            return (record.plan.preservedNewerContent, current, lastUndo)
        }
        // The native write/readback and synchronized receipt precede ACK.
        // A closed or switched document keeps its pending bridge result.
        guard AnyMiniAppsCodec.matches(request, document: document) else { throw MiniAppBridgeError.wrongSource }
        try document.requireMounted(document.mountedOwnerID)
        _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
        return preserved
    }

    private static func attachFile(_ item: MiniAppContent, key: String,
        binding: AnyPreparedMigrationPlanBinding, objectID: String, client: AnyHTTPClient,
        store: MiniAppBridgeStore, lease: AnyHostLease,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyMiniAppsFileReceipt {
        guard let id = item.attachmentID else { throw MiniAppBridgeError.invalidAttachment }
        let url = try store.attachmentURL(id: id)
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true,
              let size = values.fileSize, size >= 0, Int64(size) <= AnyPreparedFileIntent.maximumBytes else {
            throw MiniAppBridgeError.invalidAttachment
        }
        let name = item.name ?? url.lastPathComponent
        let mime = item.typeIdentifier.flatMap(UTType.init)?.preferredMIMEType ?? "application/octet-stream"
        let input = try FileHandle(forReadingFrom: url); defer { try? input.close() }
        var hasher = SHA256(), counted: Int64 = 0
        while let data = try input.read(upToCount: 1 << 20), !data.isEmpty {
            counted += Int64(data.count)
            guard counted <= Int64(size) else { throw MiniAppBridgeError.invalidAttachment }
            hasher.update(data: data)
            try Task.checkCancellation()
        }
        guard counted == Int64(size) else { throw MiniAppBridgeError.invalidAttachment }
        let digest = hasher.finalize().map { String(format: "%02x", $0) }.joined()
        let fileID: String
        if size <= AnyPreparedInlineFileIntent.maximumBytes {
            let native = try await AnyNativePreparedInlineFileMigration.open(
                client: client, workspace: binding.workspace, authorize: authorize)
            guard native.capabilities.storeID == binding.storeID else { throw AnyPreparedMigrationError.changedStore }
            let bytes = try Data(contentsOf: url)
            guard bytes.count == size, AnyContentDigest.sha256(bytes) == digest else { throw MiniAppBridgeError.invalidAttachment }
            let intent = try AnyPreparedInlineFileIntent(binding: binding, sourceKey: key,
                ownerObjectID: objectID, name: name, mime: mime, content: bytes)
            let prepared = try await native.prepare(intent, authorize: authorize)
            let receipt = try await native.commit(prepared, authorize: authorize)
            guard receipt.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
            fileID = receipt.fileID
        } else {
            let native = try await AnyNativePreparedFileMigration.open(
                client: client, workspace: binding.workspace, authorize: authorize)
            guard native.capabilities.storeID == binding.storeID else { throw AnyPreparedMigrationError.changedStore }
            let intent = try AnyPreparedFileIntent(binding: binding, sourceKey: key,
                ownerObjectID: objectID, name: name, mime: mime, size: Int64(size), contentSHA256: digest)
            let prepared = try await native.prepare(intent, fileURL: url, authorize: authorize)
            let receipt = try await native.commit(prepared, authorize: authorize)
            guard receipt.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
            fileID = receipt.fileID
        }
        let info = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", binding.workspace.spaceID, "files", fileID], authorize: authorize)
        guard info["fileId"]?.string == fileID, info["objectId"]?.string == objectID,
              info["size"]?.integer == Int64(size), info["name"]?.string == name,
              info["mime"]?.string == mime else { throw AnyHostError.writeUncertain }
        let bytes = try await client.readFileContentDigest(spaceID: binding.workspace.spaceID,
            fileID: fileID, size: Int64(size), mime: mime, authorize: authorize)
        guard bytes.byteCount == Int64(size), bytes.sha256 == digest else { throw AnyHostError.writeUncertain }
        try await lease.validate(); try await authorize()
        return .init(fileID: fileID, bytes: Int64(size), sha256: digest, name: name, mime: mime)
    }
}
#endif

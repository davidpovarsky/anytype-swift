import Foundation
import CryptoKit
import AnytypeCore
import HanlinMiniAppsBridge
import Services
import ProtobufMessages
import SwiftProtobuf
import UniformTypeIdentifiers
import Darwin

/// Uses the editor's native services. Pending bridge results are acknowledged only
/// after native readback and a durable local receipt; no hidden document replica.
@MainActor
enum PinkhaMiniAppsResultApplier {
    static let receiptField = "pinkhaMiniAppsRequest"

    static func apply(request: MiniAppInvocation, result: MiniAppResult,
                      editor: EditorPageController, store: MiniAppBridgeStore,
                      authorize: @MainActor () throws -> Void = {}) async throws -> Bool {
        guard let model = editor.viewModel as? EditorPageViewModel else {
            throw PinkhaMiniAppsError.documentUnavailable
        }
        let document = model.document
        func validateContext() throws {
            try Task.checkCancellation()
            try authorize()
            try validate(request: request, document: document)
        }
        try validateContext()
        let journal = try PinkhaMiniAppsJournal(request: request)
        var plan = try resumePlan(request: request, result: result, journal: journal)
        if plan.completed {
            _ = try store.acknowledgeResult(id: request.id, sourceAppID: request.source.appID)
            return plan.preservedNewerContent
        }
        try journal.save(plan)
        var blocks = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
        try validateContext()

        // Preflight the complete mutation set before its first write.
        for mutation in plan.mutations {
            let marks = try resultingMarks(mutation)
            let snapshot = try snapshot(id: mutation.before.id, blocks: blocks)
            if try replayDecision(mutation: mutation, current: snapshot, plan: plan,
                expectedMarks: marks.serializedData()) == .preserveNewerContent {
                try preserveResult(result, in: &plan)
                try journal.save(plan)
                break
            }
        }

        for mutation in plan.mutations {
            try validateContext()
            let marks = try resultingMarks(mutation)
            let marksData = try marks.serializedData()
            // Refresh before each independent native write; never replay over a newer edit.
            blocks = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
            try validateContext()
            switch try replayDecision(mutation: mutation,
                current: snapshot(id: mutation.before.id, blocks: blocks),
                plan: plan, expectedMarks: marksData) {
            case .alreadyApplied:
                plan.appliedBlocks.insert(mutation.before.id)
                try journal.save(plan)
                continue
            case .preserveNewerContent:
                try preserveResult(result, in: &plan)
                try journal.save(plan)
                break
            case .apply:
                guard let text = mutation.afterText else { throw PinkhaMiniAppsError.unsupportedResult }
                try await dispatch(.mutation, key: mutation.before.id, plan: &plan,
                    journal: journal, validate: validateContext) {
                    try await model.blockActionService.setText(contextId: document.objectId,
                        blockId: mutation.before.id, middlewareString: .init(text: text, marks: marks))
                }
                let persisted = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
                try validateContext()
                guard let actual = try snapshot(id: mutation.before.id, blocks: persisted),
                      actual.matchesExactly(.init(id: mutation.before.id, text: text, marks: marksData)) else {
                    throw PinkhaMiniAppsError.resultNotSaved
                }
                plan.appliedBlocks.insert(mutation.before.id)
                try journal.save(plan)
            }
            if plan.preservedNewerContent { break }
        }

        var anchor = request.source.metadata["anytype.insertionAnchor"]
        for (index, item) in plan.additions.enumerated() {
            try validateContext()
            let key = "\(request.id.uuidString.lowercased()):\(index)"
            blocks = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
            try validateContext()
            if let recorded = plan.insertedBlocks[key] {
                // A later user edit or deletion of this block must not replay the insertion.
                anchor = blocks.contains(where: { $0.id == recorded }) ? recorded : anchor
                continue
            }
            let matches = blocks.filter { $0.fields[receiptField]?.stringValue == key }
            guard matches.count <= 1 else { throw PinkhaMiniAppsError.sourceChanged }
            let existing = matches.first
            let info = try insertionBlock(item: item, request: request.id, index: index, key: key)
            let inserted: String
            if let existing {
                inserted = existing.id
            } else {
                let target = item.kind == .file
                    ? PinkhaMiniAppsContext.topLevelAnchor(anchor, documentID: document.objectId, blocks: blocks)
                    : anchor
                inserted = try await dispatch(.insertion, key: key, plan: &plan,
                    journal: journal, validate: validateContext) {
                    if let target, blocks.contains(where: { $0.id == target }) {
                        return try await model.blockActionService.add(info: info,
                            targetBlockId: target, position: .bottom, setFocus: false)
                    } else {
                        return try await Container.shared.blockService().addFirstBlock(
                            contextId: document.objectId, info: info)
                    }
                }
            }
            blocks = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
            try validateContext()
            guard let native = blocks.first(where: { $0.id == inserted }),
                  native.fields[receiptField]?.stringValue == key else {
                throw PinkhaMiniAppsError.resultNotSaved
            }
            if case .text(let expected) = info.content {
                guard case .text(let actual) = native.content,
                      actual.text.utf8.elementsEqual(expected.text.utf8),
                      try actual.marks.serializedData() == expected.marks.serializedData() else {
                    throw PinkhaMiniAppsError.resultNotSaved
                }
            }
            if item.kind == .file {
                guard let attachmentID = item.attachmentID else { throw PinkhaMiniAppsError.attachmentUnavailable }
                guard case .file(let beforeFile) = native.content else {
                    // A user may have changed the marked block after a crash.
                    // Never turn a newer text/other block back into an attachment.
                    throw PinkhaMiniAppsError.sourceChanged
                }
                let sharedFile = try store.attachmentURL(id: attachmentID)
                let expectedBytes = try await PinkhaMiniAppsContext.fileWitnesses(at: [sharedFile])[0]
                try validateContext()
                if beforeFile.state != .done || beforeFile.metadata.targetObjectId.isEmpty {
                    guard let state = plan.heartDispatch, !state.uploads.contains(key) else {
                        throw PinkhaMiniAppsError.resultNotSaved
                    }
                    let directory = FileManager.default.temporaryDirectory
                        .appendingPathComponent("miniapps-upload-" + UUID().uuidString, isDirectory: true)
                    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                    defer { try? FileManager.default.removeItem(at: directory) }
                    let suppliedName = item.name.map { ($0 as NSString).lastPathComponent } ?? ""
                    let type = item.typeIdentifier.flatMap { UTType($0) }
                    let name = suppliedName.isEmpty || suppliedName == "." || suppliedName == ".."
                        ? "Attachment." + (type?.preferredFilenameExtension ?? "bin") : suppliedName
                    let upload = directory.appendingPathComponent(name)
                    try FileManager.default.copyItem(at: sharedFile, to: upload)
                    let uploadWitnesses = try await PinkhaMiniAppsContext.fileWitnesses(at: [upload, sharedFile])
                    try validateContext()
                    guard uploadWitnesses[0] == expectedBytes, uploadWitnesses[1] == expectedBytes else {
                        throw PinkhaMiniAppsError.sourceChanged
                    }
                    let beforeUpload = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
                    try validateContext()
                    guard let currentBlock = beforeUpload.first(where: { $0.id == inserted }),
                          currentBlock.fields[receiptField]?.stringValue == key,
                          case .file(let currentFile) = currentBlock.content, currentFile == beforeFile else {
                        throw PinkhaMiniAppsError.sourceChanged
                    }
                    try await dispatch(.upload, key: key, plan: &plan,
                        journal: journal, validate: validateContext) {
                        try await model.blockActionService.upload(blockId: inserted, filePath: upload.path)
                    }
                    let uploaded = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
                    try validateContext()
                    guard let verified = uploaded.first(where: { $0.id == inserted }),
                          case .file(let file) = verified.content, file.state == .done,
                          !file.metadata.targetObjectId.isEmpty else {
                        throw PinkhaMiniAppsError.resultNotSaved
                    }
                }
                // Recover a completed upload only after exact original bytes
                // match. Native upload and this journal are separate operations.
                let persisted = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
                try validateContext()
                guard let fileBlock = persisted.first(where: { $0.id == inserted }),
                      fileBlock.fields[receiptField]?.stringValue == key,
                      case .file(let completedFile) = fileBlock.content,
                      completedFile.state == .done, !completedFile.metadata.targetObjectId.isEmpty else {
                    throw PinkhaMiniAppsError.resultNotSaved
                }
                let (readback, _) = try await PinkhaMiniAppsContext.downloadNativeFile(completedFile)
                defer { try? FileManager.default.removeItem(at: readback) }
                let witnesses = try await PinkhaMiniAppsContext.fileWitnesses(at: [sharedFile, readback])
                try validateContext()
                guard witnesses[0] == expectedBytes, witnesses[1] == expectedBytes else {
                    throw PinkhaMiniAppsError.resultNotSaved
                }
                let afterReadback = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
                try validateContext()
                guard let stillCurrent = afterReadback.first(where: { $0.id == inserted }),
                      stillCurrent.fields[receiptField]?.stringValue == key,
                      case .file(let actualFile) = stillCurrent.content, actualFile == completedFile else {
                    throw PinkhaMiniAppsError.sourceChanged
                }
            }
            plan.insertedBlocks[key] = inserted
            try journal.save(plan)
            anchor = inserted
        }
        try validateContext()
        plan.completed = true
        try journal.save(plan)
        _ = try store.acknowledgeResult(id: request.id, sourceAppID: request.source.appID)
        return plan.preservedNewerContent
    }

    private static func validate(request: MiniAppInvocation, document: any BaseDocumentProtocol) throws {
        guard request.source.appID == PinkhaMiniAppsContext.sourceAppID,
              request.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id,
              request.source.documentID == document.objectId,
              request.source.metadata["anytype.spaceID"] == document.spaceId,
              document.isOpened, !document.isLocked,
              document.permissions.canEditBlocks, document.details?.isReadonly == false
        else { throw PinkhaMiniAppsError.documentUnavailable }
    }

    private static func snapshot(id: String, blocks: [BlockInformation]) throws -> PinkhaMiniAppsBlockSnapshot? {
        guard let info = blocks.first(where: { $0.id.utf8.elementsEqual(id.utf8) }),
              case .text(let text) = info.content else { return nil }
        return .init(id: info.id, text: text.text, marks: try text.marks.serializedData())
    }

    private static func resultingMarks(_ mutation: PinkhaMiniAppsEditPlan.Mutation) throws -> Anytype_Model_Block.Content.Text.Marks {
        let before = try Anytype_Model_Block.Content.Text.Marks(serializedBytes: mutation.before.marks)
        var after = Anytype_Model_Block.Content.Text.Marks()
        after.marks = before.marks.flatMap { mark in
            PinkhaMiniAppsEditPlanner.shiftedMarkRanges(from: Int(mark.range.from), to: Int(mark.range.to),
                editLocation: mutation.location, editLength: mutation.length,
                replacementLength: mutation.replacement.utf16.count).map { range in
                    var copy = mark
                    copy.range = range.asMiddleware
                    return copy
                }
        }
        return after
    }

    static func preserveResult(_ result: MiniAppResult, in plan: inout PinkhaMiniAppsEditPlan) throws {
        guard let dispatch = plan.heartDispatch,
              dispatch.mutations.isEmpty, dispatch.insertions.isEmpty, dispatch.uploads.isEmpty,
              plan.appliedBlocks.isEmpty, plan.insertedBlocks.isEmpty else {
            throw PinkhaMiniAppsError.resultNotSaved
        }
        plan.mutations = []
        plan.additions = result.items
        plan.preservedNewerContent = true
    }

    static func resumePlan(request: MiniAppInvocation, result: MiniAppResult,
                           journal: PinkhaMiniAppsJournal) throws -> PinkhaMiniAppsEditPlan {
        guard request.id == result.requestID else { throw MiniAppBridgeError.conflictingResult }
        let requestDigest = try digest(request), resultDigest = try digest(result)
        var plan: PinkhaMiniAppsEditPlan
        if let existing = try journal.load() {
            plan = existing
        } else {
            plan = try PinkhaMiniAppsEditPlanner.make(request: request, result: result)
            plan.heartDispatch = .init(requestDigest: requestDigest, resultDigest: resultDigest)
        }
        guard plan.requestID == request.id else { throw MiniAppBridgeError.conflictingResult }
        if let dispatch = plan.heartDispatch {
            guard dispatch.version == 1,
                  dispatch.requestDigest.utf8.elementsEqual(requestDigest.utf8),
                  dispatch.resultDigest.utf8.elementsEqual(resultDigest.utf8) else {
                throw MiniAppBridgeError.conflictingResult
            }
        } else if !plan.completed {
            // Old unfinished records cannot prove that a native call was never made.
            throw PinkhaMiniAppsError.resultNotSaved
        }
        return plan
    }

    static func replayDecision(mutation: PinkhaMiniAppsEditPlan.Mutation,
                               current: PinkhaMiniAppsBlockSnapshot?, plan: PinkhaMiniAppsEditPlan,
                               expectedMarks: Data) throws -> PinkhaMiniAppsEditPlanner.ReplayDecision {
        guard let dispatch = plan.heartDispatch else { throw PinkhaMiniAppsError.resultNotSaved }
        let decision = PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation, current: current,
            alreadyRecorded: plan.appliedBlocks.contains(mutation.before.id), expectedMarks: expectedMarks)
        if dispatch.mutations.contains(mutation.before.id), decision != .alreadyApplied {
            throw PinkhaMiniAppsError.resultNotSaved
        }
        return decision
    }

    enum DispatchKind { case mutation, insertion, upload }

    /// One durable fence precedes the original native call. Reopening never clears it.
    /// The caller may settle it using exact native readback; this helper never retries.
    static func dispatch<Value: Sendable>(_ kind: DispatchKind, key: String,
        plan: inout PinkhaMiniAppsEditPlan, journal: PinkhaMiniAppsJournal,
        validate: @MainActor () throws -> Void,
        operation: @MainActor () async throws -> Value
    ) async throws -> Value {
        try validate()
        guard !plan.completed, var dispatch = plan.heartDispatch else {
            throw PinkhaMiniAppsError.resultNotSaved
        }
        switch kind {
        case .mutation:
            guard !dispatch.mutations.contains(key) else { throw PinkhaMiniAppsError.resultNotSaved }
            dispatch.mutations.insert(key)
        case .insertion:
            guard !dispatch.insertions.contains(key) else { throw PinkhaMiniAppsError.resultNotSaved }
            dispatch.insertions.insert(key)
        case .upload:
            guard !dispatch.uploads.contains(key) else { throw PinkhaMiniAppsError.resultNotSaved }
            dispatch.uploads.insert(key)
        }
        plan.heartDispatch = dispatch
        try journal.save(plan)
        try validate()
        return try await operation()
    }

    private static func digest<Value: Encodable>(_ value: Value) throws -> String {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return SHA256.hash(data: try encoder.encode(value)).map { String(format: "%02x", $0) }.joined()
    }

    private static func insertionBlock(item: MiniAppContent, request: UUID, index: Int, key: String) throws -> BlockInformation {
        let content: BlockContent
        switch item.kind {
        case .text, .json:
            guard let text = item.text else { throw PinkhaMiniAppsError.unsupportedResult }
            content = .text(.plain(text, contentType: .text))
        case .url:
            guard let url = item.url else { throw PinkhaMiniAppsError.unsupportedResult }
            content = .text(.plain(url.absoluteString, contentType: .text))
        case .file:
            guard item.attachmentID != nil else { throw PinkhaMiniAppsError.attachmentUnavailable }
            let type = item.typeIdentifier.flatMap { UTType($0) }
            let kind: FileContentType = type?.conforms(to: .image) == true ? .image :
                type?.conforms(to: .video) == true ? .video :
                type?.conforms(to: .audio) == true ? .audio : .file
            content = .file(.empty(contentType: kind))
        }
        let original = BlockInformation.empty(id: "miniapp-\(request.uuidString.lowercased())-\(index)", content: content)
        return BlockInformation(id: original.id, content: content, backgroundColor: original.backgroundColor,
            horizontalAlignment: original.horizontalAlignment, childrenIds: original.childrenIds,
            configurationData: original.configurationData, fields: [receiptField: key.protobufValue])
    }
}

struct PinkhaMiniAppsJournal {
    let url: URL
    init(request: MiniAppInvocation) throws {
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        try self.init(request: request, supportDirectory: support)
    }

    #if DEBUG
    /// Synthetic component controls use the same namespace, encoding and durable writer.
    init(request: MiniAppInvocation, testingSupportDirectory: URL) throws {
        try self.init(request: request, supportDirectory: testingSupportDirectory)
    }
    #endif

    private init(request: MiniAppInvocation, supportDirectory: URL) throws {
        let identity = [request.source.metadata["anytype.accountID"] ?? "",
                        request.source.metadata["anytype.spaceID"] ?? "",
                        request.source.documentID ?? ""].joined(separator: "\u{0}")
        let namespace = SHA256.hash(data: Data(identity.utf8)).map { String(format: "%02x", $0) }.joined()
        let receipts = supportDirectory.appendingPathComponent("MiniAppsReceipts", isDirectory: true)
        try FileManager.default.createDirectory(at: receipts, withIntermediateDirectories: true)
        try Self.synchronizeDirectory(supportDirectory)
        let root = receipts.appendingPathComponent(namespace, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        try Self.synchronizeDirectory(receipts)
        url = root.appendingPathComponent(request.id.uuidString.lowercased()).appendingPathExtension("json")
    }
    func load() throws -> PinkhaMiniAppsEditPlan? {
        let bytes: Data
        do { bytes = try Data(contentsOf: url) }
        catch let error as CocoaError where error.code == .fileReadNoSuchFile { return nil }
        // A protected/unreadable or malformed record is not an absent dispatch fence.
        return try JSONDecoder().decode(PinkhaMiniAppsEditPlan.self, from: bytes)
    }
    func save(_ plan: PinkhaMiniAppsEditPlan) throws {
        try JSONEncoder().encode(plan).write(to: url,
            options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        let output = try FileHandle(forWritingTo: url)
        defer { try? output.close() }
        try output.synchronize()
        try Self.synchronizeDirectory(url.deletingLastPathComponent())
    }

    private static func synchronizeDirectory(_ url: URL) throws {
        let directory = open(url.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard directory >= 0 else { throw PinkhaMiniAppsError.resultNotSaved }
        defer { close(directory) }
        guard fsync(directory) == 0 else { throw PinkhaMiniAppsError.resultNotSaved }
    }
}

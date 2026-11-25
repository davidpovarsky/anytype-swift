import Foundation
import UIKit
import CryptoKit
import Services
import ProtobufMessages
import SwiftProtobuf
import UniformTypeIdentifiers

/// The captured canonical Otzaria row. These values are data, not permission to
/// select an account, create a remote object, or acknowledge an exchange.
public struct AnytypeOriginalEditorLocalAnnotationSource: Sendable, Equatable {
    public let hostProfileID: String
    public let annotationUUID: UUID
    public let expectedRevision: Int64
    public let sourceWitnessSHA256: String
    public let payloadSHA256: String?

    public init(hostProfileID: String, annotationUUID: UUID, expectedRevision: Int64,
                sourceWitnessSHA256: String, payloadSHA256: String?) throws {
        guard !hostProfileID.isEmpty, hostProfileID.utf8.count <= 512,
              !hostProfileID.utf8.contains(0), expectedRevision >= 0,
              OriginalEditorLocalAnnotationValidation.digest(sourceWitnessSHA256),
              payloadSHA256.map(OriginalEditorLocalAnnotationValidation.digest) ?? true else {
            throw AnytypeOriginalEditorLocalAnnotationError.invalidSource
        }
        self.hostProfileID = hostProfileID
        self.annotationUUID = annotationUUID
        self.expectedRevision = expectedRevision
        self.sourceWitnessSHA256 = sourceWitnessSHA256
        self.payloadSHA256 = payloadSHA256
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.hostProfileID.utf8.elementsEqual(rhs.hostProfileID.utf8)
            && lhs.annotationUUID == rhs.annotationUUID
            && lhs.expectedRevision == rhs.expectedRevision
            && lhs.sourceWitnessSHA256.utf8.elementsEqual(rhs.sourceWitnessSHA256.utf8)
            && lhs.payloadSHA256 == rhs.payloadSHA256
    }
}

/// A plain saved note is seeded through original native block commands. A rich
/// body is the original opaque snapshot decoded from the canonical SQLite row.
/// The current Host profile/revision must match its captured row. A genuine
/// selected-account read may retain a different native creation profile as
/// explicit transport history. Native archive bytes and creation markers are
/// never relabelled; all reconstructed draft writes remain localOnly.
public enum AnytypeOriginalEditorLocalAnnotationBody: Sendable {
    case plainText(String)
    case nativeSnapshot(AnytypeOriginalEditorSnapshot)
}

public enum AnytypeOriginalEditorLocalAnnotationError: Error, Sendable, Equatable {
    case invalidSource, retiredSource, sourceAlreadyUsed, canonicalBodyMismatch
    case unsupportedBody, runtimeAlreadyOwned, originalServiceUnavailable
    case incompatibleDeployment, foreignRepository, invalidJournal
    case missingCredential, uncertainNativeOperation, unavailableAccount
    case unavailableSpace, unobservedSchema, wrongNativeIdentity
    case invalidNativeImport, overlappingSession, alreadyMounted, captureAlreadyAttempted
    case invalidPreview, storageFailure(Int32), closeRequiresExplicitRetry
}

/// Bind this one-use token to the original Host DB/session/presentation lifetimes
/// before the factory await. Retirement is safe while the Host mutex is held.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationSourceLifetime {
    public nonisolated let source: AnytypeOriginalEditorLocalAnnotationSource
    internal nonisolated let lifetime = EditorDocumentWriteLifetime()
    private var claimed = false

    public init(source: AnytypeOriginalEditorLocalAnnotationSource) { self.source = source }
    public nonisolated var isCurrent: Bool { lifetime.token() != nil }

    public nonisolated func retire() {
        guard let deliver = lifetime.markUnavailableDeferringObservers() else { return }
        // No callback, I/O or native operation runs on the retiring Host stack.
        Task { @MainActor in deliver() }
    }

    internal func claim() throws {
        guard isCurrent else { throw AnytypeOriginalEditorLocalAnnotationError.retiredSource }
        guard !claimed else { throw AnytypeOriginalEditorLocalAnnotationError.sourceAlreadyUsed }
        claimed = true
    }

    deinit { retire() }
}

/// A secondary preview from the SAME flushed original primary-object export.
/// Only nativeCapture.snapshot.bodyBytes is the complete canonical rich body.
public struct AnytypeOriginalEditorLocalAnnotationCapture: Sendable {
    public let nativeCapture: AnytypeOriginalEditorSnapshotCapture
    public let textPreview: String
    /// Complete text projection of the SAME verified flushed native root. The
    /// bounded preview remains secondary; migration must compare these exact
    /// UTF-8 bytes with the captured original saved note before preserving it.
    public let fullPlainText: String

    internal init(nativeCapture: AnytypeOriginalEditorSnapshotCapture, textPreview: String,
                  fullPlainText: String) {
        self.nativeCapture = nativeCapture
        self.textPreview = textPreview
        self.fullPlainText = fullPlainText
    }
}

/// A private localOnly native draft. This is never an AnyTapy destination mapping
/// or a committed document. The Host's original SQLite CAS remains Save.
@MainActor
public final class AnytypeOriginalEditorLocalAnnotationSession {
    public let binding: AnytypeOriginalEditorBinding
    /// True only while this exact native source can still accept original edits.
    /// Validation conflicts keep it true; a dispatched uncertain failure or
    /// terminal capture retires it. No canonical SQLite receipt is implied.
    public var canContinueEditing: Bool {
        !miniAppsBusy && (try? owner.validateCurrent()) != nil
            && (try? owner.host.validateCurrentSource()) != nil
    }
    private let owner: OriginalEditorLocalAnnotationDraftOwner
    private nonisolated let sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime
    private var miniAppsBusy = false

    internal init(owner: OriginalEditorLocalAnnotationDraftOwner) {
        self.owner = owner
        binding = owner.host.binding
        sourceLifetime = owner.sourceLifetime
    }

    public func makeViewController() throws -> UIViewController {
        try owner.validateCurrent()
        return try owner.host.makeViewController()
    }

    public func captureNativeSnapshot(maximumBodyBytes: Int) async throws
        -> AnytypeOriginalEditorLocalAnnotationCapture {
        guard !miniAppsBusy else { throw AnytypeOriginalEditorMiniAppsError.operationInProgress }
        return try await owner.capture(maximumBodyBytes: maximumBodyBytes)
    }

    /// Validate this Session's actual completed capture against its still-live
    /// Host source. The native editor intentionally retired at capture; that
    /// does not retire the original saved-row source before the Host's Save CAS.
    public func validateCapturedSource(_ capture: AnytypeOriginalEditorLocalAnnotationCapture) throws {
        try owner.validateCapturedSource(capture)
    }

    public func retire() { owner.retire() }
    deinit { sourceLifetime.retire() }
}

extension AnytypeOriginalEditorModule {
    /// Close every mounted local editor first. This joins the genuine native
    /// AccountStop and event/subscription drain before releasing the process to
    /// an explicit original account presentation. Private drafts remain localOnly.
    @MainActor
    public static func suspendLocalAnnotationRuntime(appGroup: String) async throws {
        try await OriginalEditorLocalAnnotationRuntime.suspend(appGroup: appGroup, retrying: false)
    }

    /// Retry only the retained failed Stop; never recreate or replace its owner.
    @MainActor
    public static func retrySuspendLocalAnnotationRuntime(appGroup: String) async throws {
        try await OriginalEditorLocalAnnotationRuntime.suspend(appGroup: appGroup, retrying: true)
    }

    /// Opens only an app-owned localOnly draft, reconstructed from the captured
    /// canonical row. No caller-selected account, Space, object or path is accepted.
    /// This is local editing only: it creates neither a remote destination nor
    /// an exchange acknowledgement. Transported bytes must have been explicitly
    /// committed to this Host's canonical row with its own increasing revision;
    /// the original native creation profile remains separate historical data.
    @MainActor
    public static func openLocalAnnotation(
        appGroup: String,
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
        body: AnytypeOriginalEditorLocalAnnotationBody,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool
    ) async throws -> AnytypeOriginalEditorLocalAnnotationSession {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            guard sourceIsCurrent(sourceLifetime.source) else {
                throw AnytypeOriginalEditorLocalAnnotationError.retiredSource
            }
            let canonical = try OriginalEditorLocalAnnotationCanonical(
                source: sourceLifetime.source, body: body
            )
            let runtime = try await OriginalEditorLocalAnnotationRuntime.acquire(appGroup: appGroup)
            let owner = try await runtime.open(
                sourceLifetime: sourceLifetime, canonical: canonical,
                sourceIsCurrent: sourceIsCurrent
            )
            return AnytypeOriginalEditorLocalAnnotationSession(owner: owner)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}

internal enum OriginalEditorLocalAnnotationValidation {
    static func digest(_ text: String) -> Bool {
        text.utf8.count == 64 && text.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    static func sha256(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}

internal struct OriginalEditorLocalAnnotationCanonical: Sendable {
    let body: AnytypeOriginalEditorLocalAnnotationBody
    let digest: String
    var transportOriginHostProfileID: String? {
        guard case .nativeSnapshot(let snapshot) = body else { return nil }
        return snapshot.provenance.transportOriginHostProfileID
    }

    init(source: AnytypeOriginalEditorLocalAnnotationSource,
         body: AnytypeOriginalEditorLocalAnnotationBody) throws {
        switch body {
        case .plainText(let text):
            // A saved plain note may already have a versioned plain envelope.
            // Its Host payload digest is still part of the current row witness;
            // it does not imply that the envelope contains a rich native body.
            guard !text.utf8.contains(0), text.utf8.count <= 1_048_576 else {
                throw AnytypeOriginalEditorLocalAnnotationError.canonicalBodyMismatch
            }
            digest = OriginalEditorLocalAnnotationValidation.sha256(Data(text.utf8))
        case .nativeSnapshot(let snapshot):
            guard source.payloadSHA256 != nil,
                  snapshot.provenance.annotationUUID == source.annotationUUID,
                  snapshot.provenance.hostProfileID.utf8.elementsEqual(source.hostProfileID.utf8),
                  snapshot.provenance.capturedAgainstRevision < source.expectedRevision else {
                throw AnytypeOriginalEditorLocalAnnotationError.canonicalBodyMismatch
            }
            // Native provenance is historical. The current account/Space is
            // independently acquired below; historical IDs never select it.
            try OriginalEditorLocalAnnotationNativeBody.requireAnnotation(snapshot, source: source)
            digest = OriginalEditorLocalAnnotationValidation.sha256(snapshot.bodyBytes)
        }
        self.body = body
    }
}


/// Result intent for the original native draft. Non-text blocks, block IDs,
/// styles and every unaffected rich-text mark remain in their native form.
public enum AnytypeOriginalEditorMiniAppsAction: String, Codable, Sendable {
    case insert, replaceSelection, replaceDocument
}

public enum AnytypeOriginalEditorMiniAppsError: Error, Sendable, Equatable {
    case invalidContext, missingSelection, sourceChanged, nativeBodyChanged
    case invalidRange, notMounted, unsupportedResult, resultNotSaved, operationInProgress
    case invalidAttachment, attachmentUnavailable, attachmentTooLarge
}


/// Bytes from, or intended for, an original native file block. No private URL
/// crosses the process boundary. The caller imports/exports the bytes using its
/// shared Bridge and keeps the original archive size limit for the final save.
public struct AnytypeOriginalEditorMiniAppsAttachment: Sendable {
    public let data: Data
    public let name: String
    public let typeIdentifier: String

    public init(data: Data, name: String, typeIdentifier: String) throws {
        guard data.count <= OriginalEditorMiniAppsFiles.maximumBytes,
              !name.isEmpty, name.utf8.count <= 255,
              name != ".", name != "..", !name.contains("/"), !name.contains("\\"),
              !name.utf8.contains(0), !typeIdentifier.isEmpty,
              typeIdentifier.utf8.count <= 256, !typeIdentifier.utf8.contains(0) else {
            throw AnytypeOriginalEditorMiniAppsError.invalidAttachment
        }
        self.data = data
        self.name = name
        self.typeIdentifier = typeIdentifier
    }
}

public struct AnytypeOriginalEditorMiniAppsFile: Sendable {
    public let blockID: String
    public let attachment: AnytypeOriginalEditorMiniAppsAttachment
}

internal enum OriginalEditorMiniAppsFiles {
    static let maximumBytes = OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes

    static func validate(_ attachments: [AnytypeOriginalEditorMiniAppsAttachment]) throws {
        var total = 0
        for attachment in attachments {
            guard attachment.data.count <= maximumBytes - total else {
                throw AnytypeOriginalEditorMiniAppsError.attachmentTooLarge
            }
            total += attachment.data.count
        }
    }

    static func kind(_ identifier: String) -> FileContentType {
        let type = UTType(identifier)
        return type?.conforms(to: .image) == true ? .image
            : type?.conforms(to: .video) == true ? .video
            : type?.conforms(to: .audio) == true ? .audio : .file
    }

    static func download(file: Anytype_Model_Block.Content.File,
                         binding: AnytypeOriginalEditorBinding, maximumBytes: Int) async throws
        -> AnytypeOriginalEditorMiniAppsAttachment {
        guard file.state == .done, !file.targetObjectID.isEmpty,
              maximumBytes >= 0, maximumBytes <= self.maximumBytes else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentUnavailable
        }
        try Task.checkCancellation()
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = binding.objectID
            $0.objectID = file.targetObjectID
            $0.spaceID = binding.spaceID
        }).invoke()
        try Task.checkCancellation()
        let records = response.objectView.details.filter { $0.id.utf8.elementsEqual(file.targetObjectID.utf8) }
        guard response.error.code == .null, response.hasObjectView,
              response.objectView.rootID.utf8.elementsEqual(file.targetObjectID.utf8),
              records.count == 1 else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentUnavailable
        }
        let original = ObjectDetails(id: records[0].id, values: records[0].details.fields)
        let details = FileDetails(objectDetails: original)
        guard details.spaceId.utf8.elementsEqual(binding.spaceID.utf8),
              let declaredBytes = original.sizeInBytes, declaredBytes >= 0,
              declaredBytes <= maximumBytes else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentTooLarge
        }
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let downloaded = try await ClientCommands.fileDownload(.with {
            $0.objectID = file.targetObjectID
            $0.path = directory.path
        }).invoke()
        try Task.checkCancellation()
        guard downloaded.error.code == .null else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentUnavailable
        }
        let data = try OriginalEditorArchiveFiles.readMiniAppsAttachment(
            URL(fileURLWithPath: downloaded.localPath), in: directory, maximumBytes: maximumBytes)
        guard data.count == declaredBytes else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentUnavailable
        }
        let type = UTType(mimeType: details.fileMimeType)
            ?? UTType(filenameExtension: (details.fileName as NSString).pathExtension) ?? .data
        return try .init(data: data, name: details.fileName, typeIdentifier: type.identifier)
    }
}

/// Durable data from one original source. Decoding this value never grants
/// authority: the source lifetime, native graph and selection are checked again.
public struct AnytypeOriginalEditorMiniAppsContext: Codable, Sendable {
    public let documentText: String
    public let selectedText: String?
    public let selectionLocation: Int?
    public let selectionLength: Int?
    public let blockIDs: [String]
    public let sceneID: String?
    internal let schema: String
    internal let source: OriginalEditorMiniAppsSource
    internal let nodes: [OriginalEditorMiniAppsNode]
    internal let selectedPaths: [[Int]]
    internal var baselineBodySHA256: String?

    /// The native selection range is block-relative. This optional offset is
    /// supplied only when the selection is also contiguous in documentText.
    public var documentSelectionLocation: Int? {
        guard let location = selectionLocation, let length = selectionLength,
              location >= 0, length >= 0,
              let selectedText, !blockIDs.isEmpty else { return nil }
        let textNodes = nodes.filter { $0.bodyText != nil }
        let indices = textNodes.indices.filter { blockIDs.contains(textNodes[$0].id) }
        guard let first = indices.first, let last = indices.last,
              indices == Array(first...last) else { return nil }
        let prefix = textNodes.prefix(first).compactMap(\.bodyText)
        let offsetResult = prefix.reduce(0) { $0 + $1.utf16.count + 1 }.addingReportingOverflow(location)
        guard !offsetResult.overflow else { return nil }
        let offset = offsetResult.partialValue
        guard offset <= documentText.utf16.count, length <= documentText.utf16.count - offset,
              let range = Range(NSRange(location: offset, length: length), in: documentText),
              String(documentText[range]) == selectedText else { return nil }
        return offset
    }

    public var selectedBlockText: String? {
        guard blockIDs.count == 1 else { return nil }
        return nodes.first(where: { $0.id == blockIDs[0] })?.bodyText
    }
}

/// Save the complete capture through the Host's original SQLite CAS, reopen the
/// saved row, then restore context. Only then create the external request. This
/// preserves unsaved rich edits before the source process can be terminated.
public struct AnytypeOriginalEditorMiniAppsLaunch: Sendable {
    public let context: AnytypeOriginalEditorMiniAppsContext
    public let capture: AnytypeOriginalEditorLocalAnnotationCapture
}

internal struct OriginalEditorMiniAppsSource: Codable, Sendable {
    let profile: String
    let annotation: UUID
    let revision: Int64
    let witness: String
    let account: String
    let object: String
    let space: String

    init(_ binding: AnytypeOriginalEditorBinding) {
        profile = binding.hostProfileID; annotation = binding.annotationUUID
        revision = binding.expectedRevision; witness = binding.sourceWitnessSHA256
        account = binding.accountID; object = binding.objectID; space = binding.spaceID
    }

    func matches(_ binding: AnytypeOriginalEditorBinding) -> Bool {
        profile.utf8.elementsEqual(binding.hostProfileID.utf8)
            && annotation == binding.annotationUUID && revision == binding.expectedRevision
            && witness == binding.sourceWitnessSHA256
            && account.utf8.elementsEqual(binding.accountID.utf8)
    }
}

internal struct OriginalEditorMiniAppsNode: Codable, Sendable {
    let id: String
    let path: [Int]
    let bytes: Data
    let bodyText: String?

    func native() throws -> Anytype_Model_Block {
        try Anytype_Model_Block(serializedBytes: bytes)
    }

    func equivalent(to other: Self) throws -> Bool {
        var left = try native(), right = try other.native()
        // Original native Import assigns a new private object/Space. The exact
        // ordered child paths and every other protobuf field remain witnesses.
        left.id = ""; right.id = ""
        left.childrenIds = []; right.childrenIds = []
        return path == other.path && left == right && bodyText == other.bodyText
    }
}

internal enum OriginalEditorMiniAppsGraph {
    static func read(binding: AnytypeOriginalEditorBinding) async throws -> [OriginalEditorMiniAppsNode] {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = binding.objectID; $0.objectID = binding.objectID; $0.spaceID = binding.spaceID
        }).invoke()
        guard response.error.code == .null, response.hasObjectView else {
            throw AnytypeOriginalEditorMiniAppsError.sourceChanged
        }
        let view = response.objectView
        let details = view.details.filter { $0.id == binding.objectID }
        guard view.rootID == binding.objectID, details.count == 1,
              ObjectDetails(id: details[0].id, values: details[0].details.fields).spaceId == binding.spaceID,
              Set(view.blocks.map(\.id)).count == view.blocks.count else {
            throw AnytypeOriginalEditorMiniAppsError.sourceChanged
        }
        let all = Dictionary(uniqueKeysWithValues: view.blocks.map { ($0.id, $0) })
        var pending: [(String, [Int])] = [(binding.objectID, [])]
        var seen = Set<String>(), nodes: [OriginalEditorMiniAppsNode] = []
        while let (id, path) = pending.popLast() {
            guard seen.insert(id).inserted, let block = all[id] else {
                throw AnytypeOriginalEditorMiniAppsError.invalidContext
            }
            let bodyText: String?
            if case .text(let text)? = block.content,
               text.style != .title, text.style != .description_ {
                bodyText = text.text
            } else { bodyText = nil }
            nodes.append(.init(id: id, path: path, bytes: try block.serializedData(), bodyText: bodyText))
            pending.append(contentsOf: block.childrenIds.enumerated().reversed().map {
                ($0.element, path + [$0.offset])
            })
        }
        return nodes
    }

    static func matching(_ expected: [OriginalEditorMiniAppsNode],
                         _ actual: [OriginalEditorMiniAppsNode]) throws -> Bool {
        guard expected.count == actual.count else { return false }
        return try zip(expected, actual).allSatisfy { left, right in try left.equivalent(to: right) }
    }

    static func range(location: Int, length: Int, text: String) throws -> Range<String.Index> {
        guard location >= 0, length >= 0, location <= text.utf16.count,
              length <= text.utf16.count - location,
              let range = Range(NSRange(location: location, length: length), in: text) else {
            throw AnytypeOriginalEditorMiniAppsError.invalidRange
        }
        return range
    }

    static func replacing(_ original: Anytype_Model_Block.Content.Text,
                          location: Int, length: Int, with replacement: String)
        throws -> Anytype_Model_Block.Content.Text {
        guard original.marks.marks.allSatisfy({ mark in
            mark.range.from >= 0 && mark.range.to > mark.range.from
                && Int(mark.range.to) <= original.text.utf16.count
        }) else { throw AnytypeOriginalEditorMiniAppsError.invalidContext }
        var changed = original
        let range = try range(location: location, length: length, text: original.text)
        changed.text.replaceSubrange(range, with: replacement)
        let end = location + length, replacementLength = replacement.utf16.count
        let delta = replacementLength - length
        changed.marks.marks = original.marks.marks.flatMap { mark in
            let start = Int(mark.range.from), finish = Int(mark.range.to)
            let ranges: [NSRange]
            if finish <= location {
                ranges = [NSRange(location: start, length: finish - start)]
            } else if start >= end {
                ranges = [NSRange(location: start + delta, length: finish - start)]
            } else {
                var retained: [NSRange] = []
                if start < location { retained.append(NSRange(location: start, length: location - start)) }
                if finish > end {
                    retained.append(NSRange(location: location + replacementLength, length: finish - end))
                }
                ranges = retained
            }
            return ranges.map { range in var copy = mark; copy.range = range.asMiddleware; return copy }
        }
        return changed
    }
}

extension AnytypeOriginalEditorLocalAnnotationSession {
    /// Adds a native action to this prepared editor's own text-selection menu.
    /// The Host uses its shared Picker; the framework embeds no runtime or picker.
    public func setMiniAppsAction(title: String,
        handler: @escaping @MainActor (Result<AnytypeOriginalEditorMiniAppsContext, Error>) -> Void) throws {
        try owner.validateCurrent()
        guard !title.isEmpty, title.utf8.count <= 256 else {
            throw AnytypeOriginalEditorMiniAppsError.invalidContext
        }
        let session = owner.host.preparedSession
        session.externalMiniAppsActionTitle = title
        session.externalMiniAppsTextAction = { [weak self] view, range in
            guard let self else { return }
            Task { @MainActor in
                do { handler(.success(try await self.captureMiniAppsContext(origin: view, range: range))) }
                catch { handler(.failure(error)) }
            }
        }
    }

    /// Nonterminal: the original owner drains admitted text/table writes and the
    /// same native editor remains available when this operation returns.
    public func captureMiniAppsContext() async throws -> AnytypeOriginalEditorMiniAppsContext {
        try await captureMiniAppsContext(origin: nil, range: nil)
    }


    /// Reads the selected original file blocks, including descendants of selected
    /// block containers. With no selection it reads the captured document's file
    /// blocks. The caller transfers bytes through its Bridge before terminal save.
    /// Every native file and the current source are checked again after download.
    public func exportMiniAppsFiles(context: AnytypeOriginalEditorMiniAppsContext,
        maximumBytes: Int) async throws -> [AnytypeOriginalEditorMiniAppsFile] {
        guard maximumBytes >= 0, maximumBytes <= OriginalEditorMiniAppsFiles.maximumBytes else {
            throw AnytypeOriginalEditorMiniAppsError.attachmentTooLarge
        }
        try Task.checkCancellation()
        try beginMiniApps()
        defer { miniAppsBusy = false; owner.host.endMiniAppsInteraction() }
        try validateMiniAppsContext(context)
        let current = try await readMiniAppsNodes()
        try Task.checkCancellation()
        let selected = try remappedSelection(context: context, current: current)
        let paths = selected.map(\.path)
        let expected = try context.nodes.filter { node in
            let included = context.selectedPaths.isEmpty
                || context.selectedPaths.contains { node.path.starts(with: $0) }
            if case .file? = try node.native().content { return included }
            return false
        }
        let candidates = try current.filter { node in
            let included = paths.isEmpty || paths.contains { node.path.starts(with: $0) }
            if case .file? = try node.native().content { return included }
            return false
        }
        guard candidates.count == expected.count else {
            throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
        }
        var result: [AnytypeOriginalEditorMiniAppsFile] = []
        var remaining = maximumBytes
        for (before, node) in zip(expected, candidates) {
            guard try before.equivalent(to: node), case .file(let file)? = try node.native().content else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
            try Task.checkCancellation()
            let attachment = try await downloadMiniAppsFile(file, maximumBytes: remaining)
            try Task.checkCancellation()
            try owner.validateCurrent()
            let observed = try await readMiniAppsNodes()
            try Task.checkCancellation()
            guard let actual = observed.first(where: { $0.id == node.id }),
                  try node.equivalent(to: actual) else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
            remaining -= attachment.data.count
            result.append(.init(blockID: node.id, attachment: attachment))
        }
        try owner.validateCurrent()
        return result
    }

    private func downloadMiniAppsFile(_ file: Anytype_Model_Block.Content.File,
        maximumBytes: Int) async throws -> AnytypeOriginalEditorMiniAppsAttachment {
        let captured = binding
        return try await owner.host.preparedSession.owner.withExclusiveRead(
            contextId: captured.objectID, spaceId: captured.spaceID,
            rpcNames: ["ObjectShow", "FileDownload"]
        ) { try await OriginalEditorMiniAppsFiles.download(file: file, binding: captured,
                                                          maximumBytes: maximumBytes) }
    }

    /// Terminal launch baseline. The Host must durably save capture before it
    /// dispatches a request, then call restore on the reopened canonical row.
    public func captureMiniAppsLaunch(context: AnytypeOriginalEditorMiniAppsContext,
        maximumBodyBytes: Int) async throws -> AnytypeOriginalEditorMiniAppsLaunch {
        try AnytypeOriginalEditorSnapshot.validateLimit(maximumBodyBytes)
        try beginMiniApps()
        var transferred = false
        defer { miniAppsBusy = false; if !transferred { owner.host.endMiniAppsInteraction() } }
        try validateMiniAppsContext(context)
        let current = try await readMiniAppsNodes()
        guard try OriginalEditorMiniAppsGraph.matching(context.nodes, current) else {
            throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
        }
        try owner.validateCurrent()
        owner.host.endMiniAppsInteraction(restore: false)
        transferred = true
        do {
            let captured = try await owner.capture(maximumBodyBytes: maximumBodyBytes)
            var durable = context
            durable.baselineBodySHA256 = OriginalEditorLocalAnnotationValidation.sha256(
                captured.nativeCapture.snapshot.bodyBytes)
            return .init(context: durable, capture: captured)
        } catch { owner.retire(); throw error }
    }

    /// Restores exactly the saved launch archive or the same unchanged canonical
    /// row after a cold reopen. New native IDs are mapped by the complete ordered
    /// protobuf witness, never by matching text. Ambiguous mapping is a conflict.
    public func restoreMiniAppsContext(_ context: AnytypeOriginalEditorMiniAppsContext) async throws
        -> AnytypeOriginalEditorMiniAppsContext {
        try beginMiniApps()
        defer { miniAppsBusy = false; owner.host.endMiniAppsInteraction() }
        try validateMiniAppsStructure(context)
        let source = context.source
        if source.matches(binding),
           source.object == binding.objectID, source.space == binding.spaceID {
            // The same retained native draft may contain newer edits outside
            // the original selection. Keep the captured baseline intact:
            // applyMiniAppsResult checks its actual targets before writing,
            // while replaceDocument still requires the complete graph.
            try validateMiniAppsContext(context)
            try owner.validateCurrent()
            return context
        }
        let successor = source.revision.addingReportingOverflow(1)
        let savedBaseline = !successor.overflow
            && binding.expectedRevision == successor.partialValue
            && context.baselineBodySHA256 == owner.canonicalBodySHA256
            && context.baselineBodySHA256 != nil
            && source.profile.utf8.elementsEqual(binding.hostProfileID.utf8)
            && source.annotation == binding.annotationUUID
            && source.account.utf8.elementsEqual(binding.accountID.utf8)
        guard source.matches(binding) || savedBaseline else {
            throw AnytypeOriginalEditorMiniAppsError.sourceChanged
        }
        let current = try await readMiniAppsNodes()
        guard try OriginalEditorMiniAppsGraph.matching(context.nodes, current) else {
            throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
        }
        try owner.validateCurrent()
        let selected = try remappedSelection(context: context, current: current)
        return .init(documentText: current.compactMap(\.bodyText).joined(separator: "\n"),
            selectedText: context.selectedText, selectionLocation: context.selectionLocation,
            selectionLength: context.selectionLength, blockIDs: selected.map(\.id),
            sceneID: context.sceneID, schema: context.schema, source: .init(binding),
            nodes: current, selectedPaths: selected.map(\.path), baselineBodySHA256: nil)
    }

    /// Writes only a private native draft, then returns its complete terminal
    /// archive. The Host commits that archive AND the exact request/result receipt
    /// in its original SQLite CAS before ACK. This method makes no distributed
    /// atomicity claim and cannot acknowledge the Bridge.
    public func applyMiniAppsResult(requestID: UUID, context: AnytypeOriginalEditorMiniAppsContext,
        action: AnytypeOriginalEditorMiniAppsAction, text: String, maximumBodyBytes: Int) async throws
        -> AnytypeOriginalEditorLocalAnnotationCapture {
        try await applyMiniAppsResult(requestID: requestID, context: context, action: action,
                                      text: text, attachments: [], maximumBodyBytes: maximumBodyBytes)
    }

    /// Adds original native attachments and verifies both native download bytes
    /// and the complete returned export before the Host's canonical save/ACK.
    public func applyMiniAppsResult(requestID: UUID, context: AnytypeOriginalEditorMiniAppsContext,
        action: AnytypeOriginalEditorMiniAppsAction, text: String,
        attachments: [AnytypeOriginalEditorMiniAppsAttachment], maximumBodyBytes: Int) async throws
        -> AnytypeOriginalEditorLocalAnnotationCapture {
        try Task.checkCancellation()
        try OriginalEditorMiniAppsFiles.validate(attachments)
        try AnytypeOriginalEditorSnapshot.validateLimit(maximumBodyBytes)
        try beginMiniApps()
        var mutated = false
        defer { miniAppsBusy = false; if !mutated { owner.host.endMiniAppsInteraction() } }
        try validateMiniAppsContext(context)
        guard text.utf8.count <= 1_048_576, !text.utf8.contains(0) else {
            throw AnytypeOriginalEditorMiniAppsError.unsupportedResult
        }
        var current = try await readMiniAppsNodes()
        try Task.checkCancellation()
        let sameNativeObject = context.source.object == binding.objectID && context.source.space == binding.spaceID
        if !sameNativeObject {
            guard try OriginalEditorMiniAppsGraph.matching(context.nodes, current) else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
        }
        let selected = try remappedSelection(context: context, current: current)
        let originals = Dictionary(uniqueKeysWithValues: context.nodes.map { ($0.id, $0) })
        var edits: [(OriginalEditorMiniAppsNode, Anytype_Model_Block.Content.Text)] = []
        let body = current.filter { $0.bodyText != nil }
        let targets: [OriginalEditorMiniAppsNode]
        switch action {
        case .replaceDocument:
            guard try OriginalEditorMiniAppsGraph.matching(context.nodes, current) else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
            targets = body
        case .replaceSelection:
            targets = selected.filter { $0.bodyText != nil }
            guard !targets.isEmpty else { throw AnytypeOriginalEditorMiniAppsError.missingSelection }
        case .insert:
            targets = selected.count == 1 && selected[0].bodyText != nil ? selected : []
        }
        for (index, target) in targets.enumerated() {
            let expected: OriginalEditorMiniAppsNode?
            if sameNativeObject { expected = originals[target.id] }
            else { expected = context.nodes.first { $0.path == target.path } }
            guard let expected, try expected.equivalent(to: target),
                  case .text(let before)? = try target.native().content else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
            let location: Int, length: Int, replacement: String
            if action != .replaceDocument, targets.count == 1,
               let capturedLocation = context.selectionLocation, let capturedLength = context.selectionLength {
                let range = try OriginalEditorMiniAppsGraph.range(location: capturedLocation,
                    length: capturedLength, text: before.text)
                guard String(before.text[range]) == context.selectedText else {
                    throw AnytypeOriginalEditorMiniAppsError.invalidRange
                }
                location = action == .insert ? capturedLocation + capturedLength : capturedLocation
                length = action == .insert ? 0 : capturedLength
                replacement = text
            } else {
                location = 0; length = before.text.utf16.count; replacement = index == 0 ? text : ""
            }
            edits.append((target, try OriginalEditorMiniAppsGraph.replacing(before,
                location: location, length: length, with: replacement)))
        }
        // All targets were checked before any native mutation. A later failure
        // retires this draft; the canonical row/receipt is still untouched.
        do {
            try Task.checkCancellation()
            try owner.validateCurrent()
            mutated = true
            for (before, after) in edits {
                try await owner.host.preparedSession.services.blockActionService.textServiceHandler.setText(
                    contextId: binding.objectID, blockId: before.id,
                    middlewareString: .init(text: after.text, marks: after.marks))
                try Task.checkCancellation()
                try owner.validateCurrent()
                current = try await readMiniAppsNodes()
                guard let observed = current.first(where: { $0.id == before.id }),
                      case .text(let actual)? = try observed.native().content, actual == after else {
                    throw AnytypeOriginalEditorMiniAppsError.resultNotSaved
                }
            }
            if edits.isEmpty && (!text.isEmpty || attachments.isEmpty) {
                let raw = BlockInformation.empty(id: "miniapp-\(requestID.uuidString.lowercased())",
                    content: .text(.plain(text, contentType: .text)))
                let info = BlockInformation(id: raw.id, content: raw.content,
                    backgroundColor: raw.backgroundColor, horizontalAlignment: raw.horizontalAlignment,
                    childrenIds: raw.childrenIds, configurationData: raw.configurationData,
                    fields: ["otzariaMiniAppsRequest": .with { $0.stringValue = requestID.uuidString.lowercased() }])
                let service = owner.host.preparedSession.services.blockActionService.blockService
                let anchor = selected.last?.id ?? current.last(where: { $0.path.count == 1 })?.id
                let added: String
                if let anchor {
                    added = try await service.add(contextId: binding.objectID, targetId: anchor,
                        info: info, position: .bottom)
                } else {
                    added = try await service.addFirstBlock(contextId: binding.objectID, info: info)
                }
                try Task.checkCancellation()
                try owner.validateCurrent()
                current = try await readMiniAppsNodes()
                guard let observed = current.first(where: { $0.id == added }), observed.bodyText == text,
                      try observed.native().fields.fields["otzariaMiniAppsRequest"]?.stringValue
                        == requestID.uuidString.lowercased() else {
                    throw AnytypeOriginalEditorMiniAppsError.resultNotSaved
                }
            }

            // File blocks are original native objects. Their data is never
            // rendered as an app-private URL or substituted with a text block.
            var importedFiles: [(String, Data)] = []
            var fileAnchor = selected.last?.path.first.flatMap { index in
                current.first(where: { $0.path == [index] })?.id
            } ?? current.last(where: { $0.path.count == 1 })?.id
            for (index, attachment) in attachments.enumerated() {
                try Task.checkCancellation()
                try owner.validateCurrent()
                let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
                defer { try? FileManager.default.removeItem(at: directory) }
                let upload = directory.appendingPathComponent(attachment.name, isDirectory: false)
                try attachment.data.write(to: upload, options: .withoutOverwriting)
                let raw = BlockInformation.empty(
                    id: "miniapp-\(requestID.uuidString.lowercased())-file-\(index)",
                    content: .file(.empty(contentType: OriginalEditorMiniAppsFiles.kind(attachment.typeIdentifier))))
                let info = BlockInformation(id: raw.id, content: raw.content,
                    backgroundColor: raw.backgroundColor, horizontalAlignment: raw.horizontalAlignment,
                    childrenIds: raw.childrenIds, configurationData: raw.configurationData,
                    fields: ["otzariaMiniAppsRequest": .with { $0.stringValue = requestID.uuidString.lowercased() },
                             "otzariaMiniAppsFileIndex": .with { $0.stringValue = String(index) }])
                let service = owner.host.preparedSession.services.blockActionService.blockService
                let added: String
                if let fileAnchor {
                    added = try await service.add(contextId: binding.objectID, targetId: fileAnchor,
                                                  info: info, position: .bottom)
                } else {
                    added = try await service.addFirstBlock(contextId: binding.objectID, info: info)
                }
                try Task.checkCancellation()
                try owner.validateCurrent()
                try await owner.host.preparedSession.services.blockActionService.fileService.uploadDataAt(
                    source: .path(upload.path), contextID: binding.objectID, blockID: added)
                try Task.checkCancellation()
                try owner.validateCurrent()
                current = try await readMiniAppsNodes()
                guard let observed = current.first(where: { $0.id == added }),
                      case .file(let file)? = try observed.native().content,
                      file.state == .done, !file.targetObjectID.isEmpty,
                      try observed.native().fields.fields["otzariaMiniAppsRequest"]?.stringValue
                        == requestID.uuidString.lowercased(),
                      try observed.native().fields.fields["otzariaMiniAppsFileIndex"]?.stringValue
                        == String(index) else {
                    throw AnytypeOriginalEditorMiniAppsError.resultNotSaved
                }
                let readback = try await downloadMiniAppsFile(file, maximumBytes: attachment.data.count)
                try Task.checkCancellation()
                try owner.validateCurrent()
                guard readback.data == attachment.data,
                      readback.name.utf8.elementsEqual(attachment.name.utf8) else {
                    throw AnytypeOriginalEditorMiniAppsError.resultNotSaved
                }
                importedFiles.append((file.targetObjectID, attachment.data))
                fileAnchor = added
            }
            try Task.checkCancellation()
            owner.host.endMiniAppsInteraction(restore: false)
            let capture = try await owner.capture(maximumBodyBytes: maximumBodyBytes)
            try Task.checkCancellation()
            if !importedFiles.isEmpty {
                let archive = try OriginalEditorLocalAnnotationNativeBody.decoded(capture.nativeCapture.snapshot)
                for (objectID, expectedBytes) in importedFiles {
                    guard try archive.fileData(objectID: objectID) == expectedBytes else {
                        throw AnytypeOriginalEditorMiniAppsError.resultNotSaved
                    }
                }
            }
            return capture

        } catch { owner.retire(); throw error }
    }

    private func beginMiniApps() throws {
        try owner.validateCurrent()
        guard !miniAppsBusy else { throw AnytypeOriginalEditorMiniAppsError.operationInProgress }
        try owner.host.beginMiniAppsInteraction()
        miniAppsBusy = true
    }

    private func readMiniAppsNodes() async throws -> [OriginalEditorMiniAppsNode] {
        let captured = binding
        return try await owner.host.preparedSession.owner.withExclusiveRead(
            contextId: captured.objectID, spaceId: captured.spaceID, rpcNames: ["ObjectShow"]
        ) { try await OriginalEditorMiniAppsGraph.read(binding: captured) }
    }

    private func validateMiniAppsStructure(_ context: AnytypeOriginalEditorMiniAppsContext) throws {
        guard context.schema == "otzaria.original-miniapps-context/1",
              context.nodes.count <= 100_000, !context.nodes.isEmpty,
              context.nodes.first?.path.isEmpty == true, context.nodes.first?.id == context.source.object,
              context.documentText == context.nodes.compactMap(\.bodyText).joined(separator: "\n"),
              Set(context.nodes.map(\.id)).count == context.nodes.count,
              Set(context.nodes.map(\.path)).count == context.nodes.count,
              context.blockIDs.count == context.selectedPaths.count,
              Set(context.blockIDs).count == context.blockIDs.count,
              Set(context.selectedPaths).count == context.selectedPaths.count,
              context.nodes.allSatisfy({ !$0.id.isEmpty && $0.bytes.count <= 4_194_304 && $0.path.allSatisfy { $0 >= 0 } }),
              (context.selectionLocation == nil) == (context.selectionLength == nil) else {
            throw AnytypeOriginalEditorMiniAppsError.invalidContext
        }
        for (id, path) in zip(context.blockIDs, context.selectedPaths) {
            guard context.nodes.contains(where: { $0.id == id && $0.path == path }) else {
                throw AnytypeOriginalEditorMiniAppsError.invalidContext
            }
        }
    }

    private func validateMiniAppsContext(_ context: AnytypeOriginalEditorMiniAppsContext) throws {
        try validateMiniAppsStructure(context)
        guard context.source.matches(binding) else { throw AnytypeOriginalEditorMiniAppsError.sourceChanged }
        if let origin = context.sceneID,
           let scene = owner.host.preparedSession.mountedEditorController?.viewIfLoaded?.window?.windowScene,
           scene.session.persistentIdentifier != origin {
            throw AnytypeOriginalEditorMiniAppsError.sourceChanged
        }
    }

    private func remappedSelection(context: AnytypeOriginalEditorMiniAppsContext,
        current: [OriginalEditorMiniAppsNode]) throws -> [OriginalEditorMiniAppsNode] {
        let sameObject = context.source.object == binding.objectID && context.source.space == binding.spaceID
        return try zip(context.blockIDs, context.selectedPaths).map { id, path in
            guard let match = current.first(where: { sameObject ? $0.id == id : $0.path == path }) else {
                throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged
            }
            return match
        }
    }

    private func captureMiniAppsContext(origin: UITextView?, range: NSRange?) async throws
        -> AnytypeOriginalEditorMiniAppsContext {
        try owner.validateCurrent()
        guard let editor = owner.host.preparedSession.mountedEditorController,
              let root = editor.viewIfLoaded, root.window != nil,
              let model = editor.viewModel as? EditorPageViewModel else {
            throw AnytypeOriginalEditorMiniAppsError.notMounted
        }
        var selectedIDs: [String] = []
        switch model.blocksStateManager.editingState {
        case .selecting(let blocks, _), .simpleTablesSelection(_, let blocks, _): selectedIDs = blocks
        default: break
        }
        var location: Int?, length: Int?, selectedText: String?
        // The original block/table selection is authoritative even when UIKit
        // still retains a text first responder from an earlier editing action.
        let focused = selectedIDs.isEmpty ? (origin ?? Self.focusedMiniAppsText(in: root)) : nil
        if let focused {
            guard focused.isDescendant(of: root),
                  let blockID = Self.miniAppsBlockID(view: focused, root: root) else {
                throw AnytypeOriginalEditorMiniAppsError.missingSelection
            }
            let value = focused.attributedText ?? NSAttributedString(string: focused.text ?? "")
            let selectedRange = range ?? focused.selectedRange
            guard selectedRange.location != NSNotFound, selectedRange.location >= 0,
                  selectedRange.length >= 0, selectedRange.location <= value.length,
                  selectedRange.length <= value.length - selectedRange.location else {
                throw AnytypeOriginalEditorMiniAppsError.invalidRange
            }
            let prefix = AttributedTextConverter.asMiddleware(attributedText:
                value.attributedSubstring(from: NSRange(location: 0, length: selectedRange.location)))
            let selection = AttributedTextConverter.asMiddleware(attributedText:
                value.attributedSubstring(from: selectedRange))
            location = prefix.text.utf16.count; length = selection.text.utf16.count
            selectedText = selection.text; selectedIDs = [blockID]
        }
        try beginMiniApps()
        defer { miniAppsBusy = false; owner.host.endMiniAppsInteraction() }
        let nodes = try await readMiniAppsNodes()
        try owner.validateCurrent()
        let selected = nodes.filter { selectedIDs.contains($0.id) }
        guard Set(selected.map(\.id)) == Set(selectedIDs) else {
            throw AnytypeOriginalEditorMiniAppsError.missingSelection
        }
        if focused != nil {
            guard selected.count == 1, let text = selected[0].bodyText, let location, let length,
                  String(text[try OriginalEditorMiniAppsGraph.range(location: location, length: length, text: text)])
                    == selectedText else { throw AnytypeOriginalEditorMiniAppsError.nativeBodyChanged }
        } else if !selected.isEmpty {
            selectedText = selected.compactMap(\.bodyText).joined(separator: "\n")
            location = 0; length = selectedText?.utf16.count
        }
        return .init(documentText: nodes.compactMap(\.bodyText).joined(separator: "\n"),
            selectedText: selectedText, selectionLocation: location, selectionLength: length,
            blockIDs: selected.map(\.id), sceneID: root.window?.windowScene?.session.persistentIdentifier,
            schema: "otzaria.original-miniapps-context/1", source: .init(binding), nodes: nodes,
            selectedPaths: selected.map(\.path), baselineBodySHA256: nil)
    }

    private static func focusedMiniAppsText(in view: UIView) -> UITextView? {
        if let text = view as? UITextView, text.isFirstResponder { return text }
        return view.subviews.lazy.compactMap { focusedMiniAppsText(in: $0) }.first
    }

    private static func miniAppsBlockID(view: UITextView, root: UIView) -> String? {
        var parent: UIView? = view
        while let current = parent, current !== root {
            if let content = current as? TextBlockContentView, content.textView.textView === view {
                return content.pinkhaMiniAppsBlockID
            }
            parent = current.superview
        }
        return nil
    }
}

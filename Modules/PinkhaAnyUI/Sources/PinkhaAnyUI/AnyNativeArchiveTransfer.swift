import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost
import PinkhaKit

/// FileHandle may return a short read before EOF. Read every bounded chunk so
/// an otherwise valid JSON prefix cannot hide unread trailing data.
enum AnyCanonicalArchiveBoundedReader {
    static func read(maximumBytes: Int, next: (Int) throws -> Data?) throws -> Data {
        guard maximumBytes > 0, maximumBytes < Int.max else { throw AnyEngineError.readLimit }
        var output = Data()
        while true {
            let remaining = maximumBytes + 1 - output.count
            guard remaining > 0 else { throw AnyEngineError.readLimit }
            let count = min(65_536, remaining)
            guard let bytes = try next(count), !bytes.isEmpty else { break }
            guard bytes.count <= count else { throw AnyEngineError.readLimit }
            output.append(bytes)
            guard output.count <= maximumBytes else { throw AnyEngineError.readLimit }
        }
        guard !output.isEmpty else { throw AnyTorahArchiveError.invalidArchive }
        return output
    }
}

/// Reopening the same reviewed archive/mapping resumes the same operations.
/// A distinct mapping gets a distinct plan; source/destination conflicts are
/// still rejected by the authoritative migration executor before any append.
public enum AnyNativeArchiveImportIdentity {
    public static func key(archiveSHA256: String, workspace: AnyTorahWorkspace,
                           objectID: String, blockMap: [String: String],
                           objectMap: [String: String]) throws -> String {
        guard archiveSHA256.utf8.count == 64,
              archiveSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              AnyEditorBlock.validID(objectID),
              (Array(blockMap.keys) + Array(blockMap.values) +
               Array(objectMap.keys) + Array(objectMap.values)).allSatisfy(AnyEditorBlock.validID) else {
            throw AnyTorahArchiveError.invalidArchive
        }
        let fields = ["pinkha-any-ui-archive-import-v1", archiveSHA256,
                      workspace.accountID, workspace.spaceID, objectID] +
            blockMap.keys.sorted().flatMap { ["block", $0, blockMap[$0]!] } +
            objectMap.keys.sorted().flatMap { ["object", $0, objectMap[$0]!] }
        let framed = fields.map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
        return AnyContentDigest.sha256(Data(framed.utf8))
    }
}

#if canImport(SwiftUI)
import Observation
import SwiftUI
import UniformTypeIdentifiers

public struct AnyCanonicalAssociationFile: FileDocument, Sendable {
    public static var readableContentTypes: [UTType] { [.json] }
    public let data: Data
    public init(data: Data) throws {
        _ = try AnyTorahArchive.decode(data)
        self.data = data
    }
    public init(configuration: ReadConfiguration) throws {
        guard let bytes = configuration.file.regularFileContents else { throw AnyTorahArchiveError.invalidArchive }
        try self.init(data: bytes)
    }
    public func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}

@MainActor @Observable
final class AnyNativeArchivePresentation {
    private(set) var archive: AnyTorahArchive?
    private(set) var fileName: String?
    private(set) var blockMappings: [String: String] = [:]
    private(set) var objectMappings: [String: String] = [:]
    private(set) var requiredObjectIDs: [String] = []
    private(set) var noteCandidates: [AnyTorahRelatedDocumentMetadata] = []
    private(set) var plan: AnyTorahMigrationPlan?
    private(set) var receipt: AnyTorahMigrationReceipt?
    private(set) var hasDispatched = false
    private(set) var isBusy = false
    var message: String?
    @ObservationIgnored private weak var document: AnyDocumentPresentation?
    @ObservationIgnored private var epoch = UUID()
    // Activation changes the import controls after the sheet's first render.
    private var active = false

    init(document: AnyDocumentPresentation) { self.document = document }
    var targetTitle: String { document?.title ?? "" }
    var blocks: [AnyEditorBlock] { document?.orderedBlocks ?? [] }
    var canImport: Bool {
        active && document?.canMutate == true && document?.hasPendingEdits == false && !isBusy
    }
    var canChangeMapping: Bool { canImport && !hasDispatched }
    var mappingIsComplete: Bool {
        guard let archive else { return false }
        return archive.sourceBlockIDs.allSatisfy { blockMappings[$0] != nil } &&
            requiredObjectIDs.allSatisfy { objectMappings[$0] != nil }
    }

    func activate() { guard !active else { return }; active = true; epoch = UUID() }
    func deactivate() { active = false; epoch = UUID() }

    func selectBlock(_ sourceID: String, destination: String) {
        guard canChangeMapping, archive?.sourceBlockIDs.contains(sourceID) == true else { return }
        if destination.isEmpty { blockMappings.removeValue(forKey: sourceID) }
        else if blocks.contains(where: { $0.id == destination }) { blockMappings[sourceID] = destination }
        plan = nil; receipt = nil
    }
    func selectObject(_ sourceID: String, destination: String) {
        guard canChangeMapping, requiredObjectIDs.contains(sourceID) else { return }
        if destination.isEmpty { objectMappings.removeValue(forKey: sourceID) }
        else if noteCandidates.contains(where: { $0.objectID == destination }) {
            objectMappings[sourceID] = destination
        }
        plan = nil; receipt = nil
    }

    func exportFile() async -> AnyCanonicalAssociationFile? {
        guard active, !isBusy, let document else { return nil }
        let expected = epoch, mounted = document.mountedOwnerID
        isBusy = true
        defer { isBusy = false }
        do {
            let access = try AnyHTTPTorahTargetAccess(client: document.client, workspace: document.workspace,
                allowedTypeIDs: document.capabilities.allowedTargetTypes, documentTypePolicy: .nativeCanonicalEditorV1)
            let service = try AnyTorahArchiveService(workspace: document.workspace,
                                                      store: document.operations, access: access)
            let objectID = document.objectID
            let authorize = authorization(expected, mounted: mounted)
            let result = try await document.nativeSession.perform { lease in
                let archive = try await service.export(objectID: objectID) {
                    try await lease.validate(); try await authorize()
                }
                let file = try AnyCanonicalAssociationFile(data: archive.encodedData())
                try await lease.validate(); try await authorize()
                return file
            }
            try requireActive(expected, mounted: mounted)
            return result
        } catch {
            if active && expected == epoch { message = AnyUIErrorText.describe(error) }
            return nil
        }
    }

    func loadFile(_ url: URL) async {
        guard canChangeMapping, let document else { return }
        let expected = epoch, mounted = document.mountedOwnerID
        isBusy = true
        defer { isBusy = false }
        do {
            let bytes = try await Task.detached(priority: .userInitiated) {
                guard url.isFileURL else { throw AnyTorahArchiveError.invalidArchive }
                let scoped = url.startAccessingSecurityScopedResource()
                defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                // File providers can replace or update an imported document.
                // Coordinate the bounded snapshot while security scope is held.
                let coordinator = NSFileCoordinator(filePresenter: nil)
                var coordinationError: NSError?
                var snapshot: Result<Data, Error>?
                coordinator.coordinate(readingItemAt: url, options: [], error: &coordinationError) { coordinatedURL in
                    snapshot = Result {
                        let handle = try FileHandle(forReadingFrom: coordinatedURL)
                        defer { try? handle.close() }
                        return try AnyCanonicalArchiveBoundedReader.read(maximumBytes: AnyTorahArchive.maximumBytes) {
                            try handle.read(upToCount: $0)
                        }
                    }
                }
                if let coordinationError { throw coordinationError }
                guard let snapshot else { throw AnyTorahArchiveError.invalidArchive }
                return try snapshot.get()
            }.value
            try requireActive(expected, mounted: mounted)
            let value = try AnyTorahArchive.decode(bytes)
            let referenced = try value.requiredReferencedObjectIDs()
            guard value.conflictCount == 0, value.pendingObservedCount == 0 else {
                throw AnyTorahArchiveError.incompleteOrConflicted
            }
            // No automatic native-ID reuse, even if source and destination IDs
            // happen to look alike. Every block and Note mapping is reviewed.
            archive = value; fileName = url.lastPathComponent
            requiredObjectIDs = referenced.filter { $0 != value.sourceObjectID }
            blockMappings = [:]; objectMappings = [:]; plan = nil; receipt = nil
            hasDispatched = false; noteCandidates = []
            if !requiredObjectIDs.isEmpty { try await loadNoteCandidates(expected: expected, mounted: mounted) }
        } catch {
            if active && expected == epoch { message = AnyUIErrorText.describe(error) }
        }
    }

    func prepare() async {
        guard canImport, mappingIsComplete, !hasDispatched, let archive, let document else { return }
        let expected = epoch, mounted = document.mountedOwnerID
        isBusy = true
        defer { isBusy = false }
        do {
            let documents = document.documents, objectID = document.objectID
            let reader = document.metadata, mappedObjects = Array(objectMappings.values)
            let requiresSelfNote = try archive.requiredReferencedObjectIDs().contains(archive.sourceObjectID)
            let authorize = authorization(expected, mounted: mounted)
            let fresh = try await document.nativeSession.perform { lease in
                let value = try await documents.read(objectID: objectID, lease: lease)
                for id in mappedObjects + (requiresSelfNote ? [objectID] : []) {
                    try await authorize()
                    let metadata = try await reader.metadata(objectID: id)
                    guard metadata.isNote else { throw AnyTorahArchiveError.invalidArchive }
                    try await lease.validate()
                }
                return value
            }
            try requireActive(expected, mounted: mounted)
            guard Set(blockMappings.values).isSubset(of: Set(fresh.snapshot.depthFirstIDs)),
                  Set(blockMappings.values).count == blockMappings.count else {
                throw AnyHostError.invalidSelection
            }
            let bytes = try archive.encodedData()
            let key = try AnyNativeArchiveImportIdentity.key(
                archiveSHA256: AnyContentDigest.sha256(bytes), workspace: document.workspace,
                objectID: objectID, blockMap: blockMappings, objectMap: objectMappings)
            let candidate = try archive.prepareImport(workspace: document.workspace, targetObjectID: objectID,
                blockIDMap: blockMappings, objectIDMap: objectMappings, migrationKey: key)
            try requireActive(expected, mounted: mounted)
            plan = candidate; receipt = nil
        } catch {
            if active && expected == epoch { message = AnyUIErrorText.describe(error) }
        }
    }

    func execute() async {
        guard canImport, let plan, let document else { return }
        let expected = epoch, mounted = document.mountedOwnerID
        isBusy = true; hasDispatched = true
        defer { isBusy = false }
        do {
            let access = try AnyHTTPTorahTargetAccess(client: document.client, workspace: document.workspace,
                allowedTypeIDs: document.capabilities.allowedTargetTypes, documentTypePolicy: .nativeCanonicalEditorV1)
            let executor = try AnyTorahMigrationExecutor(workspace: document.workspace,
                                                         store: document.operations, access: access)
            let authorize = authorization(expected, mounted: mounted)
            let result = try await document.nativeSession.perform { lease in
                let receipt = try await executor.execute(plan) {
                    try await lease.validate(); try await authorize()
                }
                try await lease.validate(); try await authorize()
                return receipt
            }
            try requireActive(expected, mounted: mounted)
            receipt = result
            if result.status == .complete {
                await document.torah.refreshAssociationSnapshot()
                await document.load()
            } else {
                message = AnyUIErrorText.text(
                    "חלק מהקישורים טרם אומתו. ניסיון נוסף ישתמש באותה תוכנית בלי ליצור זהויות חדשות.",
                    "Some associations have not been verified. Retrying uses the same plan and identities.")
            }
        } catch {
            if active && expected == epoch { message = AnyUIErrorText.describe(error) }
        }
    }

    private func loadNoteCandidates(expected: UUID, mounted: UUID) async throws {
        guard let document else { throw AnyHostError.sessionClosed }
        let client = document.client, reader = document.metadata
        let marker = document.noteMarker.collectionID
        let authorize = authorization(expected, mounted: mounted)
        let result = try await document.nativeSession.perform { lease in
            let response = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", lease.workspace.spaceID, "objects", "query"],
                body: .object(["filter": .object(["$and": .array([
                    .object(["any.collections": .object(["$in": .array([.string(marker)])])]),
                    .object(["any.collections": .object(["$nin": .array([.string("bin"), .string("template")])])])
                ])]), "limit": .integer(1_001), "includeTotal": .bool(true)]))
            guard let rows = response["records"]?.array, rows.count <= 1_000,
                  response["total"]?.integer == Int64(rows.count), response["hasNext"]?.bool == false else {
                throw AnyEngineError.readLimit
            }
            var output: [AnyTorahRelatedDocumentMetadata] = []
            for row in rows {
                try await authorize()
                try await lease.validate()
                guard let id = row["id"]?.string, row["spaceId"]?.string == lease.workspace.spaceID else {
                    throw AnyTorahArchiveError.invalidArchive
                }
                let metadata = try await reader.metadata(objectID: id)
                guard metadata.isNote else { throw AnyTorahArchiveError.invalidArchive }
                output.append(metadata)
            }
            try await lease.validate(); return output
        }
        try requireActive(expected, mounted: mounted)
        guard Set(result.map(\.objectID)).count == result.count else { throw AnyTorahArchiveError.invalidArchive }
        noteCandidates = result.sorted { $0.title.localizedStandardCompare($1.title) == .orderedAscending }
    }

    private func requireActive(_ expected: UUID, mounted: UUID) throws {
        guard active, expected == epoch, let document else { throw AnyHostError.sessionClosed }
        try document.requireMounted(mounted)
    }
    private func authorization(_ expected: UUID, mounted: UUID) -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireActive(expected, mounted: mounted)
        }
    }
}

#if canImport(UIKit)
public struct AnyNativeArchiveTransferView: View {
    @State private var model: AnyNativeArchivePresentation
    private let document: AnyDocumentPresentation
    @State private var export: AnyCanonicalAssociationFile?
    @State private var showsExporter = false
    @State private var showsImporter = false
    @State private var exportedFileName: String?
    @State private var exportsDirectory: URL?
    @Environment(\.dismiss) private var dismiss

    public init(document: AnyDocumentPresentation) {
        self.document = document
        _model = State(initialValue: AnyNativeArchivePresentation(document: document))
    }

    public var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(AnyUIErrorText.text(
                        "הקובץ מכיל קישורי מקורות קנוניים והיסטוריית המקור שלהם. טקסט המסמך וקבצים מצורפים אינם נכללים.",
                        "This file contains canonical source associations and their provenance. Document text and attachments are not included."))
                        .font(.footnote).foregroundStyle(.secondary)
                    Button(AnyUIErrorText.text("ייצוא קישורי המקורות", "Export source associations"),
                           systemImage: "square.and.arrow.up") {
                        Task {
                            if let file = await model.exportFile() { export = file; showsExporter = true }
                        }
                    }.disabled(model.isBusy || exportsDirectory == nil).accessibilityIdentifier("any-native-archive-export")
                    Button(AnyUIErrorText.text("בחירת קובץ לייבוא", "Choose archive to import"),
                           systemImage: "square.and.arrow.down") { showsImporter = true }
                        .disabled(!model.canChangeMapping || exportsDirectory == nil).accessibilityIdentifier("any-native-archive-import")
                    if let exportedFileName {
                        LabeledContent(AnyUIErrorText.text("הקובץ שיוצא", "Exported archive"), value: exportedFileName)
                            .accessibilityIdentifier("any-native-archive-exported-file")
                            .accessibilityValue(exportedFileName)
                    }
                }
                if let archive = model.archive {
                    Section(AnyUIErrorText.text("בדיקת הייבוא", "Review import")) {
                        LabeledContent(AnyUIErrorText.text("קובץ", "File"), value: model.fileName ?? "")
                            .accessibilityIdentifier("any-native-archive-file")
                            .accessibilityValue(model.fileName ?? "")
                        LabeledContent(AnyUIErrorText.text("מסמך היעד", "Destination document"),
                                       value: model.targetTitle.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : model.targetTitle)
                        LabeledContent(AnyUIErrorText.text("קישורים פעילים", "Live associations"),
                                       value: String(archive.liveClaimCount))
                        Text(AnyUIErrorText.text(
                            "קישורי המסמך יתווספו למסמך הזה. יש לבחור יעד לכל בלוק ולכל הערה מקושרת.",
                            "Document associations will be added here. Choose a destination for every source block and referenced Note."))
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    if !archive.sourceBlockIDs.isEmpty {
                        Section(AnyUIErrorText.text("התאמת בלוקים", "Map source blocks")) {
                            ForEach(Array(archive.sourceBlockIDs.enumerated()), id: \.element) { offset, id in
                                Picker(AnyUIErrorText.text("בלוק מקור", "Source block") + " \(offset + 1) · " + String(id.prefix(12)),
                                       selection: Binding(get: { model.blockMappings[id] ?? "" },
                                                          set: { model.selectBlock(id, destination: $0) })) {
                                    Text(AnyUIErrorText.text("בחירת בלוק יעד", "Choose destination block")).tag("")
                                    ForEach(model.blocks, id: \.id) { block in
                                        Text(blockLabel(block)).tag(block.id)
                                            .accessibilityIdentifier("any-native-archive-target-block-" + block.id)
                                    }
                                }.disabled(!model.canChangeMapping)
                                    .accessibilityIdentifier("any-native-archive-block-map-" + id)
                            }
                        }
                    }
                    if !model.requiredObjectIDs.isEmpty {
                        Section(AnyUIErrorText.text("התאמת הערות מקושרות", "Map referenced Notes")) {
                            ForEach(model.requiredObjectIDs, id: \.self) { id in
                                Picker(AnyUIErrorText.text("הערת מקור", "Source Note") + " · " + String(id.prefix(12)),
                                       selection: Binding(get: { model.objectMappings[id] ?? "" },
                                                          set: { model.selectObject(id, destination: $0) })) {
                                    Text(AnyUIErrorText.text("בחירת הערת יעד", "Choose destination Note")).tag("")
                                    ForEach(model.noteCandidates, id: \.objectID) { note in
                                        Text(note.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : note.title).tag(note.objectID)
                                    }
                                }.disabled(!model.canChangeMapping)
                                    .accessibilityIdentifier("any-native-archive-note-map-" + id)
                            }
                        }
                    }
                    if let plan = model.plan {
                        Section {
                            Text(AnyUIErrorText.text("קישורים בתוכנית", "Associations in this plan") + ": \(plan.operations.count)")
                            if let receipt = model.receipt {
                                Text(receipt.status == .complete ?
                                     AnyUIErrorText.text("כל הקישורים בתוכנית אומתו במנוע.", "Every association in the plan was verified in the engine.") :
                                     AnyUIErrorText.text("הייבוא הושלם חלקית; הקישורים שאומתו נשמרו.", "Import is incomplete; verified associations were retained."))
                                    .accessibilityIdentifier("any-native-archive-import-result")
                                    .accessibilityValue(receipt.status == .complete ? "complete" : "incomplete")
                                if receipt.status == .incomplete {
                                    Text(AnyUIErrorText.text("ממתינים לאימות", "Pending verification") + ": \(receipt.pendingClaimIDs.count)")
                                }
                            }
                            if model.receipt?.status != .complete {
                                Button(model.hasDispatched ? AnyUIErrorText.text("ניסיון נוסף לאותה תוכנית", "Retry the same plan") :
                                                             AnyUIErrorText.text("אישור וייבוא", "Confirm import")) {
                                    Task { await model.execute() }
                                }.disabled(!model.canImport).accessibilityIdentifier("any-native-archive-confirm")
                            }
                        }
                    } else {
                        Button(AnyUIErrorText.text("בדיקת התוכנית", "Prepare import review")) {
                            Task { await model.prepare() }
                        }.disabled(!model.canImport || !model.mappingIsComplete)
                            .accessibilityIdentifier("any-native-archive-prepare")
                    }
                }
                if model.isBusy { ProgressView() }
                if let message = model.message { Text(message).font(.footnote).foregroundStyle(.secondary) }
            }
            .navigationTitle(AnyUIErrorText.text("העברת קישורי מקורות", "Transfer source associations"))
            .toolbar { ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("סיום", "Done")) { dismiss() }
                    .accessibilityIdentifier("any-native-archive-close")
            }}
            .fileExporter(isPresented: $showsExporter, document: export, contentType: .json,
                          defaultFilename: "source-associations") { result in
                switch result {
                case .success(let url): exportedFileName = url.lastPathComponent
                case .failure(let error): model.message = AnyUIErrorText.describe(error)
                }
            }
            .fileDialogDefaultDirectory(exportsDirectory)
            .fileImporter(isPresented: $showsImporter, allowedContentTypes: [.json]) { result in
                switch result {
                case .success(let url): Task { await model.loadFile(url) }
                case .failure(let error): model.message = AnyUIErrorText.describe(error)
                }
            }
            .fileDialogDefaultDirectory(exportsDirectory)
            .task {
                model.activate()
                do { exportsDirectory = try Self.userExportsDirectory() }
                catch { model.message = AnyUIErrorText.describe(error) }
            }
            .onDisappear { if !document.showsArchiveTransfer { model.deactivate() } }
        }
    }

    /// Documents is intentionally user-visible in Files. Native storage and
    /// journals continue to use Application Support; credentials stay in Keychain.
    private static func userExportsDirectory() throws -> URL {
        let documents = try FileManager.default.url(for: .documentDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        let directory = documents.appendingPathComponent("Exports", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let values = try directory.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        guard values.isDirectory == true, values.isSymbolicLink != true,
              directory.resolvingSymlinksInPath().deletingLastPathComponent() ==
                documents.resolvingSymlinksInPath() else {
            throw CocoaError(.fileWriteInvalidFileName)
        }
        return directory
    }

    private func blockLabel(_ block: AnyEditorBlock) -> String {
        let projection = block.type == "code" ? AnyInlineMarkdown(literal: block.text) : AnyInlineMarkdown(block.text)
        let text = (projection.isEditable ? projection.display : block.text)
            .replacingOccurrences(of: "\n", with: " ")
        return (text.isEmpty ? AnyUIErrorText.text("בלוק ריק", "Empty block") : String(text.prefix(72))) +
            " · " + String(block.id.prefix(8))
    }
}
#endif
#endif

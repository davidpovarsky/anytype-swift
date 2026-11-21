#if DEBUG && targetEnvironment(simulator)
import Foundation
import CryptoKit
import Services
import ProtobufMessages
import SwiftProtobuf

/// A qualification fixture created by the ORIGINAL engine in an owned Space.
/// Stored protobufs are actual ObjectShow results, never substitute block models.
internal struct AnytypeOriginalEditorNativeFixture: Sendable {
    let accountID: String
    let spaceID: String
    let runtimeNonce: UUID
    let objectID: String
    let linkedObjectID: String
    let fileObjectID: String
    let paragraphBlockID: String
    let linkBlockID: String
    let fileBlockID: String
    let originalRootViewBytes: Data
    let originalLinkedViewBytes: Data
    let attachmentBytes: Data
    let retainedEvidenceDirectory: URL
}

internal enum AnytypeOriginalEditorNativeFixtureError: Error, Sendable {
    case invalidScope, invalidNativeIdentity, missingFixtureContent
    case ambiguousDependency, changedBlockIdentity, changedNativeBlock, changedAttachment
}

internal struct AnytypeOriginalEditorNativeFixtureFailure: Error {
    let retainedEvidenceDirectory: URL
    let underlyingError: any Error
}

/// This is acceptance support for the additive framework consumer. It does not
/// install an editor engine, create an account, choose a Space, or admit a caller's
/// arbitrary Space string. The runtime alone can mint OwnedQualificationSpace.
internal enum AnytypeOriginalEditorNativeFixtureBuilder {
    @MainActor
    static func create(in source: OwnedQualificationSpace) async throws -> AnytypeOriginalEditorNativeFixture {
        try source.validateCurrentRuntime()
        let accountID = source.accountID
        let spaceID = source.spaceID
        let runtimeNonce = source.runtimeNonce
        try source.claimForFixture()
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        let attachment = Data([0x00, 0xff, 0x0d, 0x0a, 0x80, 0x01])
            + Data("original-sidecar-שלום-\u{0065}\u{0301}".utf8)
        let uploadURL = directory.appendingPathComponent("qualification-sidecar.bin")
        do {
            try attachment.write(to: uploadURL, options: .withoutOverwriting)
            let fixture = try await source.performRPCs(
                rpcNames: ["ObjectCreate", "BlockCreate", "BlockTextSetText", "FileUpload", "FileDownload", "ObjectShow"]
            ) {
                let objectID = try await createPage(
                    name: "Original rich qualification \(runtimeNonce.uuidString)",
                    spaceID: spaceID, evidenceName: "source-create.pb", directory: directory
                )
                let linkedObjectID = try await createPage(
                    name: "Original linked qualification \(runtimeNonce.uuidString)",
                    spaceID: spaceID, evidenceName: "linked-create.pb", directory: directory
                )
                _ = try await createBlock(
                    contextID: linkedObjectID, targetID: linkedObjectID, position: .inner,
                    block: .with { $0.text = .with { $0.text = "Linked original content — מקור" } },
                    evidenceName: "linked-text-create.pb", directory: directory
                )

                let paragraphID = try await createBlock(
                    contextID: objectID, targetID: objectID, position: .inner,
                    block: .with { $0.text = .with { $0.text = "original pending marks" } },
                    evidenceName: "paragraph-create.pb", directory: directory
                )
                let richText = "שלום rich 👩🏽‍💻 e\u{0301} source"
                let marks = Anytype_Model_Block.Content.Text.Marks.with {
                    $0.marks = [
                        mark(.bold, substring: "שלום", in: richText),
                        mark(.italic, substring: "rich", in: richText),
                        mark(.link, substring: "source", in: richText, parameter: "https://example.invalid/original-source"),
                    ]
                }
                let textResult = try await ClientCommands.blockTextSetText(.with {
                    $0.contextID = objectID
                    $0.blockID = paragraphID
                    $0.text = richText
                    $0.marks = marks
                }).invoke()
                try retain(textResult, named: "paragraph-real-text-write.pb", in: directory)
                let checkboxID = try await createBlock(
                    contextID: objectID, targetID: paragraphID, position: .bottom,
                    block: .with { $0.text = .with { $0.text = "Original checked item"; $0.style = .checkbox; $0.checked = true } },
                    evidenceName: "checkbox-create.pb", directory: directory
                )
                let quoteID = try await createBlock(
                    contextID: objectID, targetID: checkboxID, position: .inner,
                    block: .with { $0.text = .with { $0.text = "Nested original quotation"; $0.style = .quote } },
                    evidenceName: "nested-quote-create.pb", directory: directory
                )
                let linkID = try await createBlock(
                    contextID: objectID, targetID: checkboxID, position: .bottom,
                    block: .with { $0.link = .with { $0.targetBlockID = linkedObjectID } },
                    evidenceName: "native-link-create.pb", directory: directory
                )
                let uploaded = try await ClientCommands.fileUpload(.with {
                    $0.spaceID = spaceID
                    $0.localPath = uploadURL.path
                    $0.type = .file
                    $0.style = .auto
                    $0.preloadOnly = false
                    $0.createdInContext = objectID
                }).invoke()
                try retain(uploaded, named: "native-file-upload.pb", in: directory)
                guard !uploaded.objectID.isEmpty, uploaded.preloadFileID.isEmpty,
                      uploaded.hasDetails else {
                    throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
                }
                try requireString(uploaded.details, "id", equals: uploaded.objectID)
                try requireString(uploaded.details, "spaceId", equals: spaceID)
                guard Set([objectID, linkedObjectID, uploaded.objectID]).count == 3 else {
                    throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
                }
                let fileID = try await createBlock(
                    contextID: objectID, targetID: linkID, position: .bottom,
                    // Exactly the original BlockFile.asMiddleware fields. File
                    // metadata remains owned by the real native file object.
                    block: .with { $0.file = .with {
                        $0.targetObjectID = uploaded.objectID
                        $0.type = .file
                        $0.state = .done
                        $0.style = .auto
                    } },
                    evidenceName: "native-file-block-create.pb", directory: directory
                )
                let beforeRoot = try await show(
                    objectID: objectID, spaceID: spaceID,
                    named: "source-root-object-show.pb", directory: directory
                )
                let beforeLinked = try await show(
                    objectID: linkedObjectID, spaceID: spaceID,
                    named: "source-linked-object-show.pb", directory: directory
                )
                let nativeParagraph = try uniqueBlock(paragraphID, in: beforeRoot)
                let nativeCheckbox = try uniqueBlock(checkboxID, in: beforeRoot)
                let nativeQuote = try uniqueBlock(quoteID, in: beforeRoot)
                guard case .text(let nativeText)? = nativeParagraph.content,
                      nativeText.text.utf8.elementsEqual(richText.utf8),
                      nativeText.hasMarks,
                      try deterministic(nativeText.marks) == deterministic(marks),
                      case .text(let checkbox)? = nativeCheckbox.content,
                      checkbox.style == .checkbox, checkbox.checked,
                      checkbox.text == "Original checked item",
                      nativeCheckbox.childrenIds.contains(quoteID),
                      case .text(let quote)? = nativeQuote.content,
                      quote.style == .quote, quote.text == "Nested original quotation",
                      try uniqueBlock(linkID, in: beforeRoot).link.targetBlockID == linkedObjectID,
                      try uniqueBlock(fileID, in: beforeRoot).file.targetObjectID == uploaded.objectID else {
                    throw AnytypeOriginalEditorNativeFixtureError.missingFixtureContent
                }
                try await verifyDownloadedFile(
                    objectID: uploaded.objectID, expected: attachment, receiptName: "source-file-download.pb",
                    evidenceDirectory: directory
                )
                return AnytypeOriginalEditorNativeFixture(
                    accountID: accountID, spaceID: spaceID, runtimeNonce: runtimeNonce,
                    objectID: objectID, linkedObjectID: linkedObjectID, fileObjectID: uploaded.objectID,
                    paragraphBlockID: paragraphID, linkBlockID: linkID, fileBlockID: fileID,
                    originalRootViewBytes: try beforeRoot.serializedData(),
                    originalLinkedViewBytes: try beforeLinked.serializedData(),
                    attachmentBytes: attachment, retainedEvidenceDirectory: directory
                )
            }
            try source.validateCurrentRuntime()
            return fixture
        } catch {
            throw AnytypeOriginalEditorNativeFixtureFailure(
                retainedEvidenceDirectory: directory, underlyingError: error
            )
        }
    }

    /// Call after the acceptance consumer has reopened/mounted the imported
    /// candidate through the real Host. This independently reads native state
    /// again; the earlier Import result cannot stand in for a later reader.
    /// A successful return proves this fixture's native data/file fidelity only.
    @MainActor
    static func verifyAfterReopen(
        candidate: AnytypeOriginalEditorImportedCandidate,
        fixture: AnytypeOriginalEditorNativeFixture,
        host: AnytypeOriginalEditorHost,
        in target: OwnedQualificationSpace
    ) async throws -> URL {
        try target.validateCurrentRuntime()
        try host.validateCurrentSource()
        let currentHostRevision = host.binding.expectedRevision
        guard candidate.runtimeNonce == fixture.runtimeNonce,
              candidate.runtimeNonce == target.runtimeNonce,
              candidate.accountID.utf8.elementsEqual(fixture.accountID.utf8),
              candidate.accountID.utf8.elementsEqual(target.accountID.utf8),
              candidate.spaceID.utf8.elementsEqual(target.spaceID.utf8),
              candidate.originalObjectID.utf8.elementsEqual(fixture.objectID.utf8),
              candidate.capturedProvenance.spaceID.utf8.elementsEqual(fixture.spaceID.utf8),
              !candidate.spaceID.utf8.elementsEqual(fixture.spaceID.utf8),
              host.binding.accountID.utf8.elementsEqual(candidate.accountID.utf8),
              host.binding.spaceID.utf8.elementsEqual(candidate.spaceID.utf8),
              host.binding.objectID.utf8.elementsEqual(candidate.objectID.utf8),
              host.binding.hostProfileID.utf8.elementsEqual(candidate.capturedProvenance.hostProfileID.utf8),
              host.binding.annotationUUID == candidate.capturedProvenance.annotationUUID,
              host.binding.sourceWitnessSHA256 == candidate.capturedProvenance.sourceWitnessSHA256,
              host.binding.expectedRevision >= candidate.capturedProvenance.capturedAgainstRevision else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidScope
        }
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        do {
            let receiptURL = try await target.performRPCs(rpcNames: ["ObjectSearch", "ObjectShow", "FileDownload"]) {
                let beforeRoot = try Anytype_Model_ObjectView(serializedBytes: fixture.originalRootViewBytes)
                let beforeLinked = try Anytype_Model_ObjectView(serializedBytes: fixture.originalLinkedViewBytes)
                let afterRoot = try await show(
                    objectID: candidate.objectID, spaceID: candidate.spaceID,
                    named: "after-reopen-root-object-show.pb", directory: directory
                )
                let mappedLinkedID = try await findImportedDependency(
                    originalObjectID: fixture.linkedObjectID, originalSpaceID: fixture.spaceID,
                    targetSpaceID: candidate.spaceID, directory: directory
                )
                let afterLinked = try await show(
                    objectID: mappedLinkedID, spaceID: candidate.spaceID,
                    named: "after-reopen-linked-object-show.pb", directory: directory
                )
                let afterFileBlock = try uniqueBlock(fixture.fileBlockID, in: afterRoot)
                guard case .file(let file)? = afterFileBlock.content, !file.targetObjectID.isEmpty,
                      file.type == .file, file.state == .done else {
                    throw AnytypeOriginalEditorNativeFixtureError.missingFixtureContent
                }
                _ = try await show(
                    objectID: file.targetObjectID, spaceID: candidate.spaceID,
                    named: "after-reopen-file-object-show.pb", directory: directory
                )
                guard Set([candidate.objectID, mappedLinkedID, file.targetObjectID]).count == 3 else {
                    throw AnytypeOriginalEditorNativeFixtureError.ambiguousDependency
                }
                let mapping = [
                    candidate.objectID: fixture.objectID,
                    mappedLinkedID: fixture.linkedObjectID,
                    file.targetObjectID: fixture.fileObjectID,
                ]
                // Exact blocks, unknown fields, UTF8 text, marks/ranges, hierarchy,
                // styles and flags. Only verified original OBJECT references are
                // mapped back; child block IDs are never rewritten or flattened.
                try compareBlocks(before: beforeRoot, after: afterRoot, objectMap: mapping)
                try compareBlocks(before: beforeLinked, after: afterLinked, objectMap: mapping)
                try await verifyDownloadedFile(
                    objectID: file.targetObjectID, expected: fixture.attachmentBytes,
                    receiptName: "restored-file-download.pb", evidenceDirectory: directory
                )
                let receipt: [String: Any] = [
                    "scope": "Actual original ObjectShow after Host reopen; exact native block/reference and FileDownload byte comparison",
                    "runtimeNonce": candidate.runtimeNonce.uuidString,
                    "originalSpaceID": fixture.spaceID, "restoredSpaceID": candidate.spaceID,
                    "originalObjectID": fixture.objectID, "restoredObjectID": candidate.objectID,
                    "annotationUUID": candidate.capturedProvenance.annotationUUID.uuidString,
                    "hostProfileID": candidate.capturedProvenance.hostProfileID,
                    "capturedAgainstRevision": candidate.capturedProvenance.capturedAgainstRevision,
                    "currentHostRevision": currentHostRevision,
                    "originalLinkedObjectID": fixture.linkedObjectID, "restoredLinkedObjectID": mappedLinkedID,
                    "originalFileObjectID": fixture.fileObjectID, "restoredFileObjectID": file.targetObjectID,
                    "rootBlockCount": beforeRoot.blocks.count, "linkedBlockCount": beforeLinked.blocks.count,
                    "fileBytes": fixture.attachmentBytes.count,
                    "fileSHA256": SHA256.hash(data: fixture.attachmentBytes).map { String(format: "%02x", $0) }.joined(),
                    "uiMountAndInteractionRequireSeparateWitness": true,
                ]
                let output = directory.appendingPathComponent("native-fidelity-after-reopen.json")
                try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys, .withoutEscapingSlashes])
                    .write(to: output, options: .withoutOverwriting)
                return output
            }
            try target.validateCurrentRuntime()
            try host.validateCurrentSource()
            return receiptURL
        } catch {
            throw AnytypeOriginalEditorNativeFixtureFailure(
                retainedEvidenceDirectory: directory, underlyingError: error
            )
        }
    }

    private static func createPage(name: String, spaceID: String, evidenceName: String, directory: URL) async throws -> String {
        let result = try await ClientCommands.objectCreate(.with {
            $0.spaceID = spaceID
            $0.objectTypeUniqueKey = ObjectTypeUniqueKey.page.value
            $0.details = .with { $0.fields["name"] = .with { $0.stringValue = name } }
            // No editorDeleteEmpty / select-type / select-template flags.
        }).invoke()
        try retain(result, named: evidenceName, in: directory)
        guard !result.objectID.isEmpty, result.hasDetails else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
        }
        try requireString(result.details, "id", equals: result.objectID)
        try requireString(result.details, "spaceId", equals: spaceID)
        return result.objectID
    }

    private static func createBlock(
        contextID: String, targetID: String, position: Anytype_Model_Block.Position,
        block: Anytype_Model_Block, evidenceName: String, directory: URL
    ) async throws -> String {
        let result = try await ClientCommands.blockCreate(.with {
            $0.contextID = contextID; $0.targetID = targetID; $0.position = position; $0.block = block
        }).invoke()
        try retain(result, named: evidenceName, in: directory)
        guard !result.blockID.isEmpty else { throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity }
        return result.blockID
    }

    private static func mark(
        _ type: Anytype_Model_Block.Content.Text.Mark.TypeEnum,
        substring: String, in text: String, parameter: String = ""
    ) -> Anytype_Model_Block.Content.Text.Mark {
        let range = (text as NSString).range(of: substring)
        // Only constant substrings above call this helper; NSRange is the exact
        // UTF16 convention of original NSRange+Middleware / AttributedTextConverter.
        precondition(range.location != NSNotFound && range.length > 0)
        return .with {
            $0.type = type; $0.param = parameter
            $0.range = .with { $0.from = Int32(range.location); $0.to = Int32(NSMaxRange(range)) }
        }
    }

    private static func show(objectID: String, spaceID: String, named name: String, directory: URL) async throws -> Anytype_Model_ObjectView {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
        }).invoke()
        try retain(response, named: name, in: directory)
        guard response.hasObjectView, response.objectView.rootID.utf8.elementsEqual(objectID.utf8),
              !response.objectView.blocks.isEmpty else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
        }
        let details = response.objectView.details.filter { $0.id.utf8.elementsEqual(objectID.utf8) }
        guard details.count == 1, details[0].hasDetails else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
        }
        try requireString(details[0].details, "spaceId", equals: spaceID)
        return response.objectView
    }

    private static func findImportedDependency(
        originalObjectID: String, originalSpaceID: String, targetSpaceID: String, directory: URL
    ) async throws -> String {
        let response = try await ClientCommands.objectSearch(.with {
            $0.spaceID = targetSpaceID; $0.limit = 2; $0.needTotal = true
            $0.keys = ["id", "spaceId", "oldAnytypeID", "sourceFilePath"]
            $0.filters = [("oldAnytypeID", originalObjectID), ("sourceFilePath", originalSpaceID + "/" + originalObjectID)].map { key, value in
                .with { $0.relationKey = key; $0.condition = .equal; $0.value = .with { $0.stringValue = value } }
            }
        }).invoke()
        try retain(response, named: "imported-link-dependency-query.pb", in: directory)
        guard response.total == 1, response.records.count == 1 else {
            throw AnytypeOriginalEditorNativeFixtureError.ambiguousDependency
        }
        let details = response.records[0]
        try requireString(details, "spaceId", equals: targetSpaceID)
        try requireString(details, "oldAnytypeID", equals: originalObjectID)
        try requireString(details, "sourceFilePath", equals: originalSpaceID + "/" + originalObjectID)
        return try string(details, "id")
    }

    private static func verifyDownloadedFile(
        objectID: String, expected: Data, receiptName: String, evidenceDirectory: URL
    ) async throws {
        // Keep every original downloaded byte under this receipt tree so the
        // consumer can retain the complete evidence after a failure as well.
        let destination = try OriginalEditorArchiveFiles.makeOwnedDirectory(in: evidenceDirectory)
        try JSONSerialization.data(withJSONObject: ["ownedDestination": destination.path], options: [.sortedKeys])
            .write(to: evidenceDirectory.appendingPathComponent(receiptName + ".destination.json"), options: .withoutOverwriting)
        let response = try await ClientCommands.fileDownload(.with {
            $0.objectID = objectID; $0.path = destination.path
        }).invoke()
        try retain(response, named: receiptName, in: evidenceDirectory)
        let actual = try OriginalEditorArchiveFiles.readOwnedRegularFile(
            URL(fileURLWithPath: response.localPath), in: destination, maximumBytes: 65_536
        )
        guard actual == expected else { throw AnytypeOriginalEditorNativeFixtureError.changedAttachment }
    }

    private static func compareBlocks(
        before: Anytype_Model_ObjectView, after: Anytype_Model_ObjectView, objectMap: [String: String]
    ) throws {
        let beforeIDs = before.blocks.map(\.id)
        let mappedIDs = after.blocks.map { $0.id == after.rootID ? before.rootID : $0.id }
        guard !beforeIDs.contains(""), Set(beforeIDs).count == beforeIDs.count,
              Set(mappedIDs).count == mappedIDs.count, beforeIDs.count == mappedIDs.count,
              Set(beforeIDs) == Set(mappedIDs) else {
            throw AnytypeOriginalEditorNativeFixtureError.changedBlockIdentity
        }
        for actual in after.blocks {
            var mapped = actual
            if mapped.id == after.rootID { mapped.id = before.rootID }
            if case .link(var link)? = mapped.content, let original = objectMap[link.targetBlockID] {
                link.targetBlockID = original; mapped.link = link
            }
            if case .file(var file)? = mapped.content, let original = objectMap[file.targetObjectID] {
                file.targetObjectID = original; mapped.file = file
            }
            let expected = try uniqueBlock(mapped.id, in: before)
            guard try deterministic(expected) == deterministic(mapped) else {
                throw AnytypeOriginalEditorNativeFixtureError.changedNativeBlock
            }
        }
    }

    private static func uniqueBlock(_ blockID: String, in view: Anytype_Model_ObjectView) throws -> Anytype_Model_Block {
        let found = view.blocks.filter { $0.id.utf8.elementsEqual(blockID.utf8) }
        guard found.count == 1 else { throw AnytypeOriginalEditorNativeFixtureError.changedBlockIdentity }
        return found[0]
    }

    private static func deterministic<M: SwiftProtobuf.Message>(_ message: M) throws -> Data {
        var options = BinaryEncodingOptions()
        options.useDeterministicOrdering = true
        return try message.serializedData(options: options)
    }

    private static func string(_ details: Google_Protobuf_Struct, _ key: String) throws -> String {
        guard let value = details.fields[key], case .stringValue(let result)? = value.kind, !result.isEmpty else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
        }
        return result
    }

    private static func requireString(_ details: Google_Protobuf_Struct, _ key: String, equals expected: String) throws {
        guard try string(details, key).utf8.elementsEqual(expected.utf8) else {
            throw AnytypeOriginalEditorNativeFixtureError.invalidNativeIdentity
        }
    }

    private static func retain<M: SwiftProtobuf.Message>(_ message: M, named name: String, in directory: URL) throws {
        try message.serializedData().write(to: directory.appendingPathComponent(name), options: .withoutOverwriting)
    }
}
#endif

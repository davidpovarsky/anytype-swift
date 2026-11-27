import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost

/// Complete original-parser output for ONE native Markdown body operation.
/// This value grants no authority and never calls a native API itself.
struct AnyHanlinAtomicSaveBody: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    static let primitiveSource = "2619d5b144b23eb80247df613d5d128aa2efbfb6"
    let document: PinkhaHanlinSaveMessageDocument
    let manifest: PinkhaHanlinSaveMessageManifest
    private let markdown: String
    var description: String { "AnyHanlinAtomicSaveBody(private message redacted)" }
    var debugDescription: String { description }

    init(plan: PinkhaHanlinSaveMessagePlan, conversion: PinkhaHanlinMarkdownSaveConversion) throws {
        try conversion.manifest.validate(plan: plan)
        guard plan.identity.session.context.namespace.app.utf8.elementsEqual(PinkhaHanlinEngineNamespace.any.utf8),
              conversion.document.title.utf8.elementsEqual(plan.title.utf8) else {
            throw HanlinHostError.staleContext
        }
        struct Serialization: Encodable {
            let contract: String; let primitiveSource: String; let markdownSHA256: String; let markdownBytes: Int
        }
        let serialization = Serialization(contract: "pinkha-hanlin-original-any-markdown/v1",
            primitiveSource: Self.primitiveSource, markdownSHA256: plan.markdownSHA256,
            markdownBytes: plan.markdown.utf8.count)
        manifest = try conversion.document.manifest(for: plan,
            nativeSerializationSHA256: Self.digest(try Self.canonical(serialization)), bodyMode: .conditionalMarkdown)
        document = conversion.document; markdown = plan.markdown
    }

    func intent(reference: AnyNativeMarkdownReference, expectedVersion: String) throws -> AnyNativeMarkdownWriteIntent {
        let scope = manifest.identity.session.context.namespace
        guard reference.accountID.utf8.elementsEqual(scope.account.utf8),
              reference.spaceID.utf8.elementsEqual(scope.space.utf8) else {
            throw HanlinHostError.staleContext
        }
        return try .init(reference: reference, requestID: manifest.conditionalBodyRequestID,
                         expectedVersion: expectedVersion, content: markdown)
    }

    /// The exact original reference, request correlation, content, native run
    /// and version enter the durable dispatch digest. It is not native dedup.
    func requestSHA256(_ intent: AnyNativeMarkdownWriteIntent, generation: UUID,
                       engineStartedAt: String) throws -> String {
        guard intent.context.requestID.utf8.elementsEqual(manifest.conditionalBodyRequestID.utf8),
              intent.context.requestedContentSHA256 == manifest.markdownSHA256,
              intent.context.requestedContentBytes == manifest.markdownUTF8Bytes,
              intent.content.utf8.elementsEqual(markdown.utf8), !engineStartedAt.isEmpty else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let original = try self.intent(reference: intent.context.reference, expectedVersion: intent.expectedVersion)
        guard original.content.utf8.elementsEqual(intent.content.utf8) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        struct Material: Encodable {
            let contract: String; let manifestSHA256: String; let account: String; let space: String; let object: String
            let requestID: String; let requestedSHA256: String; let requestedBytes: Int
            let expectedVersionSHA256: String; let generation: UUID; let engineStartedAtSHA256: String
        }
        return Self.digest(try Self.canonical(Material(contract: "pinkha-hanlin-conditional-request/v1",
            manifestSHA256: manifest.canonicalSHA256(), account: intent.context.reference.accountID,
            space: intent.context.reference.spaceID, object: intent.context.reference.objectID,
            requestID: intent.context.requestID, requestedSHA256: intent.context.requestedContentSHA256,
            requestedBytes: intent.context.requestedContentBytes, expectedVersionSHA256: Self.digest(intent.expectedVersion),
            generation: generation, engineStartedAtSHA256: Self.digest(engineStartedAt))))
    }

    static func validate(_ acknowledgement: AnyNativeMarkdownAcknowledgement,
                         intent: AnyNativeMarkdownWriteIntent) throws {
        let actual = acknowledgement.context, original = intent.context
        guard actual.reference == original.reference,
              actual.requestID.utf8.elementsEqual(original.requestID.utf8),
              actual.requestedContentSHA256 == original.requestedContentSHA256,
              actual.requestedContentBytes == original.requestedContentBytes,
              !acknowledgement.nativeVersion.isEmpty, acknowledgement.nativeVersion.utf8.count <= 1_024,
              acknowledgement.nativeVersion.utf8.allSatisfy({ $0 >= 33 && $0 <= 126 }) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
    }

    static func admittedAcknowledgement(_ acknowledgement: AnyNativeMarkdownAcknowledgement,
        intent: AnyNativeMarkdownWriteIntent, requestSHA256: String) throws -> PinkhaHanlinSaveMessageAtomicAcknowledgement {
        try validate(acknowledgement, intent: intent)
        return try .init(requestSHA256: requestSHA256, savedVersionSHA256: digest(acknowledgement.nativeVersion),
            insertedReferences: acknowledgement.insertedBlockIDs, updatedReferences: acknowledgement.updatedBlockIDs,
            deletedReferences: acknowledgement.deletedBlockIDs, unchangedBlocks: acknowledgement.unchangedBlocks)
    }

    static func unadmittedAcknowledgementDigest(_ acknowledgement: AnyNativeMarkdownAcknowledgement,
        intent: AnyNativeMarkdownWriteIntent, requestSHA256: String) throws -> String {
        try validate(acknowledgement, intent: intent)
        return try PinkhaHanlinSaveMessageAtomicAcknowledgement.digestUnadmittedNativeReceipt(
            requestSHA256: requestSHA256, savedVersionSHA256: digest(acknowledgement.nativeVersion),
            insertedReferences: acknowledgement.insertedBlockIDs, updatedReferences: acknowledgement.updatedBlockIDs,
            deletedReferences: acknowledgement.deletedBlockIDs, unchangedBlocks: acknowledgement.unchangedBlocks)
    }

    static func digest(_ text: String) -> String { digest(Data(text.utf8)) }
    static func digest(_ bytes: Data) -> String { PinkhaHanlinCreatePagePlan.digest(bytes) }
    private static func canonical<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
}

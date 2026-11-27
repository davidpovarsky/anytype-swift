import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

public enum PinkhaHanlinSaveMessageError: Error, Equatable, Sendable {
    case invalidPlan
    case unsupportedDocument
    case invalidProgress
    case conflictingReceipt
    case invalidTransition
}

/// An in-memory request for a NEW document. This type grants no write authority
/// and is not installed in the catalog. Native confirmation and complete
/// conversion must finish before any native effect. The original generic
/// metadata reservation alone never confers authority or proves persistence.
public struct PinkhaHanlinSaveMessagePlan: PinkhaHanlinNativeWritePlan {
    public static let alias = "anytype_save_message"
    public static let localToolID = "save-message"
    public static let maximumTitleUTF8Bytes = 512
    public static let maximumMarkdownUTF8Bytes = 65_536
    public static let maximumBlocks = 64

    public let title: String
    public let markdown: String
    public let identity: PinkhaHanlinWriteIdentity

    public init(invocation: HanlinHostInvocation) throws {
        let request = invocation.request
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                         localToolID: try .init(validating: Self.localToolID))
        guard invocation.writeGuarantee == .independentObjectCreation, invocation.expectedRevision == nil,
              request.logicalToolID == logical,
              request.aliasUsed.utf8.elementsEqual(Self.alias.utf8),
              request.descriptorRevision == (try HanlinDescriptorRevision(1)),
              request.routingTableRevision == HanlinCatalogRevision(1),
              request.origin == .assistantModel, request.grantIDs.isEmpty,
              request.appSessionID == nil, request.runtimeSessionID == nil,
              PinkhaHanlinInvocationEnvelope.acceptsSDKIdentity(request),
              invocation.step >= 0, !invocation.providerCallID.isEmpty,
              invocation.providerCallID.utf8.count <= 1_024,
              request.limits.timeoutMilliseconds > 0, request.limits.timeoutMilliseconds <= 30_000,
              request.limits.maximumOutputBytes > 0,
              request.limits.maximumOutputBytes <= 8 * 1_048_576,
              let deadline = request.deadline, deadline > .now, deadline.timeIntervalSinceNow <= 30,
              case .object(let members) = request.arguments, members.count == 2,
              case .string(let title)? = members["title"],
              case .string(let markdown)? = members["markdown"] else {
            throw PinkhaHanlinSaveMessageError.invalidPlan
        }
        try Self.validateContent(title: title, markdown: markdown)
        // Keep the exact user-visible bytes. No normalization, truncation,
        // splitting, destination argument, existing-object edit, or new retry ID.
        self.title = title
        self.markdown = markdown
        self.identity = .init(session: invocation.session, invocationID: request.id,
            runID: invocation.runID, step: invocation.step,
            providerCallDigest: Self.digest(Data(invocation.providerCallID.utf8)),
            argumentsDigest: Self.materialDigest(["pinkha-hanlin-save-message-input/v1", title, markdown]),
            envelopeDigest: Self.digest(try Self.canonicalBytes(request)), deadline: deadline)
        try identity.validate()
    }

    /// Pure content bounds shared with completed-message presentation. Passing
    /// this check grants no permission and creates no invocation or retry ID.
    public static func validateContent(title: String, markdown: String) throws {
        guard !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              title.utf8.count <= maximumTitleUTF8Bytes,
              !markdown.isEmpty, markdown.utf8.count <= maximumMarkdownUTF8Bytes else {
            throw PinkhaHanlinSaveMessageError.invalidPlan
        }
    }

    public var titleSHA256: String { Self.digest(Data(title.utf8)) }
    public var markdownSHA256: String { Self.digest(Data(markdown.utf8)) }

    static func digest(_ bytes: Data) -> String { PinkhaHanlinCreatePagePlan.digest(bytes) }

    static func materialDigest(_ values: [String]) -> String {
        digest(Data(values.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8))
    }

    static func canonicalBytes<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    static func validReference(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 256 &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
}

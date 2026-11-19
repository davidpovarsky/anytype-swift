import Foundation
#if canImport(CryptoKit)
import CryptoKit
#else
import Crypto
#endif
import HanlinHostContracts
import HanlinPlatformContracts

public enum PinkhaHanlinWriteError: Error {
    case unavailable, invalidPlan, duplicate, conflict, unresolved, corruptJournal, journalFull
}

/// Host-private preparation only. No catalog/dispatch hook is installed by these write helpers.
/// The title exists in memory for the exact native confirmation; only its digest enters the journal.
public struct PinkhaHanlinCreatePagePlan: Sendable {
    public static let alias = "anytype_create_page"
    public let title: String
    public let identity: PinkhaHanlinWriteIdentity

    public init(invocation: HanlinHostInvocation) throws {
        let request = invocation.request
        let logical = HanlinLogicalToolID(providerInstanceID: try .init(validating: "anytype.host"),
                                         localToolID: try .init(validating: "create-page"))
        guard invocation.writeGuarantee == .independentObjectCreation, invocation.expectedRevision == nil,
              request.logicalToolID == logical,
              request.aliasUsed.utf8.elementsEqual(Self.alias.utf8),
              request.descriptorRevision == (try HanlinDescriptorRevision(1)),
              request.routingTableRevision == HanlinCatalogRevision(1),
              request.origin == .assistantModel, request.grantIDs.isEmpty,
              request.appSessionID == nil, request.runtimeSessionID == nil, PinkhaHanlinInvocationEnvelope.acceptsSDKIdentity(request),
              invocation.step >= 0, !invocation.providerCallID.isEmpty, invocation.providerCallID.utf8.count <= 1_024,
              request.limits.timeoutMilliseconds > 0, request.limits.timeoutMilliseconds <= 30_000,
              request.limits.maximumOutputBytes > 0, request.limits.maximumOutputBytes <= 8 * 1_048_576,
              let deadline = request.deadline, deadline > .now, deadline.timeIntervalSinceNow <= 30,
              case .object(let members) = request.arguments, members.count == 1,
              let titleValue = members["title"], case .string(let title) = titleValue,
              !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              title.utf8.count <= 512 else { throw PinkhaHanlinWriteError.invalidPlan }
        self.title = title // Preserve exact bytes. No normalization, numeric coercion, type/template/body input.
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        self.identity = .init(session: invocation.session, invocationID: request.id,
            runID: invocation.runID, step: invocation.step,
            providerCallDigest: Self.digest(Data(invocation.providerCallID.utf8)),
            argumentsDigest: Self.digest(Data(title.utf8)),
            envelopeDigest: Self.digest(try encoder.encode(request)), deadline: deadline)
    }

    public static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}

/// Metadata only, retaining the ORIGINAL immutable namespace/session, never a business title/body.
public struct PinkhaHanlinWriteIdentity: Codable, Equatable, Sendable {
    public let session: HanlinHostSession
    public let invocationID: HanlinToolInvocationID
    public let runID: UUID
    public let step: Int
    public let providerCallDigest: String
    public let argumentsDigest: String
    public let envelopeDigest: String
    public let deadline: Date

    public var key: String { PinkhaHanlinCreatePagePlan.digest(Data(invocationID.rawValue.utf8)) }

    public func validate() throws {
        guard session.context.namespace.app.utf8.elementsEqual("anytype".utf8), step >= 0,
              [providerCallDigest, argumentsDigest, envelopeDigest].allSatisfy(Self.isDigest),
              session.context.namespace.workspace.utf8.elementsEqual(session.context.namespace.space.utf8),
              session.context.objectReference.map({ !$0.isEmpty && $0.utf8.count <= 256 }) ?? true,
              session.context.selectionReferences.count <= 64,
              session.context.selectionReferences.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 256 }),
              session.context.sourceRevision.map({ $0.utf8.count <= 256 }) ?? true,
              session.context.localeIdentifier.utf8.count <= 64,
              deadline.timeIntervalSinceReferenceDate.isFinite else { throw PinkhaHanlinWriteError.corruptJournal }
    }

    public static func isDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}
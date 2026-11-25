import Foundation
import SwiftProtobuf

public extension PinkhaHeartSemanticAnchorSnapshot {
    init(nativeBlock block: Anytype_Model_Block) throws {
        guard case .text(let text)? = block.content,
              text.unknownFields.data.isEmpty, text.marks.unknownFields.data.isEmpty else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        let marks = try text.marks.marks.map { mark in
            guard mark.hasRange, mark.unknownFields.data.isEmpty, mark.range.unknownFields.data.isEmpty,
                  let kind = Int32(exactly: mark.type.rawValue) else {
                throw PinkhaHeartSemanticAnchorError.invalidRequest
            }
            return PinkhaHeartSemanticAnchorMark(from: mark.range.from, to: mark.range.to,
                kind: kind, param: mark.param)
        }
        try self.init(text: text.text, marks: marks)
    }
}

/// Keeps the complete original native block for a current-read comparison and
/// later non-mark readback. This plan cannot publish or invoke the native engine.
public struct PinkhaHeartSemanticAnchorPlan: Sendable {
    public let request: PinkhaHeartSemanticAnchorRequest
    let originalBlock: Anytype_Model_Block

    public init(spaceID: String, objectID: String, anchorID: String,
                range: NSRange, nativeBlock: Anytype_Model_Block) throws {
        request = try .init(spaceID: spaceID, objectID: objectID, blockID: nativeBlock.id,
            anchorID: anchorID, range: range, expected: .init(nativeBlock: nativeBlock))
        originalBlock = nativeBlock
    }

    func verifyCurrent(_ response: Anytype_Rpc.Object.Show.Response) throws {
        let current = try target(in: response)
        guard try exactBlock(originalBlock, current) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        guard try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: current) == request.expected else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
    }

    func validatedEvent(_ reply: PinkhaHeartSemanticAnchorAppliedReply,
                        preflight: Anytype_Rpc.Object.Show.Response? = nil) throws -> Anytype_ResponseEvent {
        try reply.receipt.validate(for: request)
        let event: Anytype_ResponseEvent
        do { event = try .init(serializedBytes: reply.responseEvent) }
        catch { throw PinkhaHeartSemanticAnchorError.invalidReply }
        guard heartBytesEqual(event.contextID, request.objectID), event.unknownFields.data.isEmpty,
              (1...2).contains(event.messages.count),
              event.messages.allSatisfy({
                  heartBytesEqual($0.spaceID, request.spaceID) && $0.unknownFields.data.isEmpty
              }), let message = event.messages.last else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        if event.messages.count == 2 {
            guard case .objectDetailsAmend(let amendment)? = event.messages[0].value else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            try validateTorahProjection(amendment, preflight: preflight)
        }
        guard case .blockSetText(let update)? = message.value,
              heartBytesEqual(update.id, request.blockID), update.unknownFields.data.isEmpty,
              !update.hasText, !update.hasStyle, !update.hasChecked, !update.hasColor,
              !update.hasIconEmoji, !update.hasIconImage,
              update.hasMarks, update.marks.hasValue, update.marks.unknownFields.data.isEmpty else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        var block = originalBlock
        var text = block.text
        text.marks = update.marks.value
        block.text = text
        let actual = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: block)
        let planned = try request.plannedSnapshot()
        guard actual.hasSameMarks(as: planned),
              actual.digest == reply.receipt.afterTextMarksSHA256 else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        return event
    }


    private func validateTorahProjection(
        _ amendment: Anytype_Event.Object.Details.Amend,
        preflight: Anytype_Rpc.Object.Show.Response?
    ) throws {
        guard let preflight else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        try verifyCurrent(preflight)
        let rows = preflight.objectView.details.filter { heartBytesEqual($0.id, request.objectID) }
        guard rows.count == 1, let row = rows.first, row.hasDetails, row.subIds.isEmpty,
              row.unknownFields.data.isEmpty, row.details.unknownFields.data.isEmpty,
              heartBytesEqual(amendment.id, request.objectID), amendment.subIds.isEmpty,
              amendment.unknownFields.data.isEmpty,
              amendment.details.count == Self.torahProjectionKeys.count else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        var seen = Set<String>()
        var options = BinaryEncodingOptions()
        options.useDeterministicOrdering = true
        for item in amendment.details {
            guard Self.torahProjectionKeys.contains(item.key), seen.insert(item.key).inserted,
                  item.hasValue, item.unknownFields.data.isEmpty,
                  let original = row.details.fields[item.key] else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            try Self.validateProjectionValue(item.value, key: item.key)
            try Self.validateProjectionValue(original, key: item.key)
            // Native page154 capture changes only block marks. Its rebuildable
            // Torah projection is already exposed by this same object's
            // ObjectShow. A hash-shaped string alone is not content authority.
            guard try item.value.serializedData(options: options)
                == original.serializedData(options: options) else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
        }
        guard seen == Self.torahProjectionKeys else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }

    private static let torahProjectionKeys: Set<String> = [
        "_pinkhaTorahState", "_pinkhaTorahCanonicalHash", "_pinkhaTorahProjectionVersion",
        "_pinkhaTorahCacheIntegrity", "_pinkhaTorahCanonicalPropertyKey", "_pinkhaTorahRelatedVersion",
        "_pinkhaTorahReady", "_pinkhaTorahAttachedProperties", "_pinkhaTorahLabels"
    ]

    private static func validateProjectionValue(_ value: Google_Protobuf_Value, key: String) throws {
        guard value.unknownFields.data.isEmpty else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        switch (key, value.kind) {
        case ("_pinkhaTorahState", .stringValue(let state)?):
            guard heartBytesEqual(state, "READY") else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        case ("_pinkhaTorahReady", .boolValue(let ready)?):
            guard ready else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        case ("_pinkhaTorahProjectionVersion", .numberValue(let version)?),
             ("_pinkhaTorahRelatedVersion", .numberValue(let version)?):
            guard version == 1 else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        case ("_pinkhaTorahCanonicalHash", .stringValue(let hash)?),
             ("_pinkhaTorahCacheIntegrity", .stringValue(let hash)?):
            guard hash.utf8.count == 64,
                  hash.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
        case ("_pinkhaTorahCanonicalPropertyKey", .stringValue(let property)?):
            guard !property.isEmpty else { throw PinkhaHeartSemanticAnchorError.invalidReply }
        case ("_pinkhaTorahAttachedProperties", .listValue(let properties)?):
            let allowed: Set<String> = ["pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords"]
            guard properties.unknownFields.data.isEmpty, properties.values.count <= allowed.count else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            var seen = Set<String>()
            for item in properties.values {
                guard item.unknownFields.data.isEmpty, case .stringValue(let property)? = item.kind,
                      allowed.contains(property), seen.insert(property).inserted else {
                    throw PinkhaHeartSemanticAnchorError.invalidReply
                }
            }
        case ("_pinkhaTorahLabels", .stringValue(let labels)?):
            let data = Data(labels.utf8)
            try HeartSemanticJSON.validate(data, maximumBytes: 2 * 1_024 * 1_024)
            guard let values = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            for (identity, raw) in values {
                guard !identity.isEmpty, let label = raw as? [String: Any],
                      label["he"] is String, Set(label.keys).isSubset(of: ["he", "en"]),
                      label["en"] == nil || label["en"] is String else {
                    throw PinkhaHeartSemanticAnchorError.invalidReply
                }
            }
        default:
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }

    func verifyReadback(_ response: Anytype_Rpc.Object.Show.Response,
                        receipt: PinkhaHeartSemanticAnchorReceipt) throws {
        try receipt.validate(for: request)
        let actualBlock = try target(in: response)
        let actual = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: actualBlock)
        let planned = try request.plannedSnapshot()
        guard actual.hasSameMarks(as: planned),
              actual.digest == receipt.afterTextMarksSHA256 else {
            throw PinkhaHeartSemanticAnchorError.uncertain
        }
        var restored = actualBlock
        var text = restored.text
        if originalBlock.text.hasMarks {
            text.marks = originalBlock.text.marks
        } else {
            text.clearMarks()
        }
        restored.text = text

        // Original Heart Base.Diff materializes absent Restrictions as an empty
        // message. Preserve every restriction value and unknown field, while
        // treating only absent/present-empty message identity as equivalent.
        var original = originalBlock
        if !original.hasRestrictions { original.restrictions = .init() }
        if !restored.hasRestrictions { restored.restrictions = .init() }
        guard try exactBlock(original, restored) else {
            throw PinkhaHeartSemanticAnchorError.uncertain
        }
    }

    private func target(in response: Anytype_Rpc.Object.Show.Response) throws -> Anytype_Model_Block {
        guard response.error.code == .null, response.hasObjectView,
              heartBytesEqual(response.objectView.rootID, request.objectID),
              response.objectView.blocks.count <= 10_000 else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        let details = response.objectView.details.filter { heartBytesEqual($0.id, request.objectID) }
        guard details.count == 1, let row = details.first, row.hasDetails,
              case .stringValue(let objectID)? = row.details.fields["id"]?.kind,
              case .stringValue(let spaceID)? = row.details.fields["spaceId"]?.kind,
              heartBytesEqual(objectID, request.objectID), heartBytesEqual(spaceID, request.spaceID) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        let blocks = response.objectView.blocks.filter { heartBytesEqual($0.id, request.blockID) }
        guard blocks.count == 1, let block = blocks.first else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        return block
    }

    private func exactBlock(_ left: Anytype_Model_Block, _ right: Anytype_Model_Block) throws -> Bool {
        var options = BinaryEncodingOptions()
        options.useDeterministicOrdering = true
        // Generated Swift equality normalizes Unicode string equivalence.
        // Deterministic protobuf bytes preserve text, IDs, opaque fields and
        // every original mark parameter exactly, including unknown fields.
        return try left.serializedData(options: options) == right.serializedData(options: options)
    }
}

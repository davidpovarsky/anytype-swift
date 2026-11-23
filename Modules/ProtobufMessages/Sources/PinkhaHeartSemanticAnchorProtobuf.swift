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

    func validatedEvent(_ reply: PinkhaHeartSemanticAnchorAppliedReply) throws -> Anytype_ResponseEvent {
        try reply.receipt.validate(for: request)
        let event: Anytype_ResponseEvent
        do { event = try .init(serializedBytes: reply.responseEvent) }
        catch { throw PinkhaHeartSemanticAnchorError.invalidReply }
        guard heartBytesEqual(event.contextID, request.objectID), event.unknownFields.data.isEmpty,
              event.messages.count == 1, let message = event.messages.first,
              heartBytesEqual(message.spaceID, request.spaceID), message.unknownFields.data.isEmpty,
              case .blockSetText(let update)? = message.value,
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

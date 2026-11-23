#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import PinkhaKit
import ProtobufMessages

/// Downstream Heart adapter for the existing canonical anchor identity. The
/// selected text remains native plain text plus complete protobuf marks.
/// Shipping/mounted editor activation is a separate acceptance boundary.
@MainActor
final class AnytypeHeartSemanticAnchorService {
    private let client = PinkhaHeartSemanticAnchorClient.page154()

    func prepare(anchor: PinkhaSemanticTextAnchor, nativeBlock: Anytype_Model_Block,
                 selection: NSRange) throws -> PinkhaHeartSemanticAnchorPending {
        let lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: anchor.spaceID)
        let plan = try PinkhaHeartSemanticAnchorPlan(spaceID: anchor.spaceID, objectID: anchor.objectID,
            anchorID: anchor.id.uuidString.lowercased(), range: selection, nativeBlock: nativeBlock)
        guard plan.request.marker.utf8.elementsEqual(anchor.markerString.utf8) else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        return try client.prepare(plan, lease: lease)
    }

    func prepareVisibleSelection(anchor: PinkhaSemanticTextAnchor, blockID: String,
                                 visibleText: String, selection: NSRange,
                                 lease: PinkhaNativeReadLease) async throws -> PinkhaHeartSemanticAnchorPending {
        let pending = try await client.prepareVisibleSelection(spaceID: anchor.spaceID,
            objectID: anchor.objectID, blockID: blockID, anchorID: anchor.id.uuidString.lowercased(),
            visibleText: visibleText, range: selection, lease: lease)
        guard pending.marker.utf8.elementsEqual(anchor.markerString.utf8) else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        return pending
    }

    func apply(_ pending: PinkhaHeartSemanticAnchorPending) async throws
        -> PinkhaHeartSemanticAnchorVerifiedCapture {
        try await client.apply(pending)
    }
}
#endif

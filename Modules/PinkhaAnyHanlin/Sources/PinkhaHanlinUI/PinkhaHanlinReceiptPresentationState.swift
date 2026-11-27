#if canImport(UIKit)
import Foundation
import HanlinHostContracts

/// The UI's bounded display history is separate from its sticky write barrier.
/// Only the original SDK callback feeds this value; it grants no native authority.
struct PinkhaHanlinReceiptPresentationState {
    static let maximumDisplayReceipts = 256
    let session: HanlinHostSession
    private var displayReceiptIDs = Set<UUID>()
    private(set) var requiresReconciliation = false

    var permitsNewRun: Bool { !requiresReconciliation }
    var displayReceiptCount: Int { displayReceiptIDs.count }

    init(session: HanlinHostSession) { self.session = session }

    /// Return true only when the caller may append a display label. Capacity
    /// never prevents an authenticated new uncertainty from closing the run gate.
    mutating func observe(_ event: HanlinHostResultEvent) -> Bool {
        guard event.call.session == session, event.result.context == session.context,
              !displayReceiptIDs.contains(event.resultID) else { return false }
        if event.result.effectState == .uncertain { requiresReconciliation = true }
        guard displayReceiptIDs.count < Self.maximumDisplayReceipts else { return false }
        displayReceiptIDs.insert(event.resultID)
        return true
    }

    mutating func requireReconciliation() { requiresReconciliation = true }
}
#endif

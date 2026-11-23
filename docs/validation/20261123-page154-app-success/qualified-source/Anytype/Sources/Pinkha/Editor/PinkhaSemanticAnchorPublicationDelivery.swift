#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
@preconcurrency import Combine
import ProtobufMessages

private struct PinkhaSemanticScopedUpdate<Value: Sendable>: Sendable {
    let value: Value
    let fence: PinkhaHeartSemanticAnchorPublicationFence?
}

extension Publisher where Output: Sendable, Failure == Never {
    /// Capture the owner before Combine schedules onto main, then recheck at the
    /// actual mounted consumer. Ordinary non-capture updates retain their route.
    func pinkhaReceiveSemanticUpdates(
        spaceID: String, objectID: String,
        ownerIsCurrent: @escaping @MainActor @Sendable () -> Bool
    ) -> AnyPublisher<Output, Never> {
        map { PinkhaSemanticScopedUpdate(value: $0, fence: PinkhaHeartSemanticAnchorPublication.current) }
            .receive(on: DispatchQueue.main)
            .compactMap { update -> Output? in
                MainActor.assumeIsolated { () -> Output? in
                    guard let fence = update.fence else { return update.value }
                    var accepted: Output?
                    fence.withCurrentMainDelivery(spaceID: spaceID, objectID: objectID) {
                        if ownerIsCurrent() { accepted = update.value }
                    }
                    return accepted
                }
            }
            .eraseToAnyPublisher()
    }

    /// Preserve the existing sinkOnMain scheduling choice for the block model,
    /// while carrying the candidate owner across any required queue hop.
    func pinkhaSinkSemanticUpdates(
        spaceID: String, objectID: String,
        ownerIsCurrent: @escaping @MainActor @Sendable () -> Bool,
        receiveValue: @escaping @MainActor @Sendable (Output) -> Void
    ) -> AnyCancellable {
        let updates = map {
            PinkhaSemanticScopedUpdate(value: $0, fence: PinkhaHeartSemanticAnchorPublication.current)
        }
        let deliver: @Sendable (PinkhaSemanticScopedUpdate<Output>) -> Void = { update in
            MainActor.assumeIsolated {
                guard let fence = update.fence else { receiveValue(update.value); return }
                fence.withCurrentMainDelivery(spaceID: spaceID, objectID: objectID) {
                    if ownerIsCurrent() { receiveValue(update.value) }
                }
            }
        }
        if Thread.isMainThread {
            return updates.sink(receiveValue: deliver)
        }
        return updates.receive(on: DispatchQueue.main).sink(receiveValue: deliver)
    }
}
#endif

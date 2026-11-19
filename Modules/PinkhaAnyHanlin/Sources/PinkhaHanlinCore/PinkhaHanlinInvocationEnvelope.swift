import HanlinPlatformContracts

/// The canonical SDK dispatcher correlates its idempotency key with its own invocation UUID.
/// Legacy direct adapter calls may omit it; an independent or model-selected key is never authority.
public enum PinkhaHanlinInvocationEnvelope {
    public static func acceptsSDKIdentity(_ request: HanlinToolInvocationRequest) -> Bool {
        request.idempotencyKey.map { $0.utf8.elementsEqual(request.id.rawValue.utf8) } ?? true
    }
}

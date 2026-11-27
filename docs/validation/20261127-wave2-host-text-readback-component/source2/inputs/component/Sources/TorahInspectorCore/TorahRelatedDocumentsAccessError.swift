/// Engine adapters use this only for a confirmed current read denial or a
/// retired/changed account, Space or session. Provider/network failures remain
/// ordinary errors so transient refreshes can retain their previous results.
public enum TorahRelatedDocumentsAccessError: String, Error, Equatable, Sendable {
    case denied
    case invalidated
}

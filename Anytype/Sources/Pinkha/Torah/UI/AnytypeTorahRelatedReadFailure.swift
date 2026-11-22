import ProtobufMessages
import TorahInspectorCore

/// These exact pairs are emitted only by the native current-Space read fence.
/// A general BAD_INPUT response or an arbitrary matching description is not an
/// authority decision. No wire field, protobuf case or capability is added.
enum AnytypeTorahRelatedReadFailure {
    static func classify(_ error: Error) -> TorahRelatedDocumentsAccessError? {
        if let search = error as? Anytype_Rpc.Object.Search.Response.Error,
           search.code == .badInput {
            return currentAuthorityFailure(description: search.description_p)
        }
        if let show = error as? Anytype_Rpc.Object.Show.Response.Error,
           show.code == .badInput {
            return currentAuthorityFailure(description: show.description_p)
        }
        return nil
    }

    private static func currentAuthorityFailure(
        description: String
    ) -> TorahRelatedDocumentsAccessError? {
        switch description {
        case "PINKHA_CURRENT_SPACE_READ_DENIED_V1": return .denied
        case "PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1": return .invalidated
        default: return nil
        }
    }
}

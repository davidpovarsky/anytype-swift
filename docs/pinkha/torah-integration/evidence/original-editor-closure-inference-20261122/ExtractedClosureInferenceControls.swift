import Foundation
enum GateError: Error { case retired }
struct Participant {
    let canManageChannelPins: Bool
    let isOwner: Bool
}
struct SpaceView {
    func effectiveNotificationMode(for objectId: String) -> Int { objectId.count }
}
@MainActor
final class CallbackInferenceFixture {
    var retired = false
    var canManageChannelPins = false
    var isSpaceOwner = false
    var chatNotificationMode = 0
    var actionsUpdated = 0
    var settingsUpdated = 0
    let objectId = "object"
    func updateActions() { actionsUpdated += 1 }
    func updateSettings() { settingsUpdated += 1 }
    // Same generic return shape only; this is NOT an original Owner test.
    func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        if retired { throw GateError.retired }
        return try operation()
    }
    func participant(_ participantSpaceView: Participant) -> Bool {
            guard (try? withCurrentSource { () -> Void in
                canManageChannelPins = participantSpaceView.canManageChannelPins
                isSpaceOwner = participantSpaceView.isOwner
                updateActions()
            }) != nil else { return false }
        return true
    }
    func space(_ spaceView: SpaceView) -> Bool {
            guard (try? withCurrentSource { () -> Void in
                chatNotificationMode = spaceView.effectiveNotificationMode(for: objectId)
                updateSettings()
            }) != nil else { return false }
        return true
    }
}
@main
struct InferenceControls {
    @MainActor static func main() {
        let accepted = CallbackInferenceFixture()
        precondition(accepted.participant(Participant(canManageChannelPins: true, isOwner: true)))
        precondition(accepted.canManageChannelPins && accepted.isSpaceOwner && accepted.actionsUpdated == 1)
        precondition(accepted.space(SpaceView()))
        precondition(accepted.chatNotificationMode == 6 && accepted.settingsUpdated == 1)
        let retired = CallbackInferenceFixture()
        retired.retired = true
        precondition(!retired.participant(Participant(canManageChannelPins: true, isOwner: true)))
        precondition(!retired.canManageChannelPins && !retired.isSpaceOwner && retired.actionsUpdated == 0)
        precondition(!retired.space(SpaceView()))
        precondition(retired.chatNotificationMode == 0 && retired.settingsUpdated == 0)
        print("PASS 4 extracted closure inference controls; original Owner, Apple framework and Native behavior NOT_RUN")
    }
}

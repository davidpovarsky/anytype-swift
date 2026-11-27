import XCTest

// COMPILE-ONLY PROBE. No top-level call, XCTest case, entry point or executable.
// The owner must use swiftc -typecheck against the selected real Simulator SDK.
// Do not run this function: enabling VoiceOver belongs to a separately admitted
// future UI test and is not authorized by this compiler/importer check.
@MainActor
@available(iOS 27.0, *)
func pinkhaVoiceOverPublicAPICompileProbe() throws {
    let service = XCUIDevice.shared.voiceOverService
    let wasEnabled: Bool = service.isEnabled
    try service.enable()
    let current: XCUIVoiceOverService.Output = try service.currentSpeech()
    let forward: XCUIVoiceOverService.Output = try service.moveForward()
    let backward: XCUIVoiceOverService.Output = try service.moveBackward()
    let utterances: [String] = [current.utterance, forward.utterance, backward.utterance]
    try service.disable()
    _ = (wasEnabled, utterances, service.isEnabled)
}

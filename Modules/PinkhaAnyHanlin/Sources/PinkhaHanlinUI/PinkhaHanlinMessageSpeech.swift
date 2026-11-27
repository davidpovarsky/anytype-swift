#if canImport(UIKit)
import AVFoundation
import Foundation
import Observation

/// A presentation-owned native text service. The SDK supplies the original
/// action controls; this object owns only the device speech operation.
@MainActor
@Observable
final class PinkhaHanlinMessageSpeech: NSObject, AVSpeechSynthesizerDelegate {
    private(set) var messageID: UUID?
    @ObservationIgnored private let synthesizer = AVSpeechSynthesizer()
    @ObservationIgnored private var utteranceID: ObjectIdentifier?

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func toggle(messageID: UUID, text: String, localeIdentifier: String) {
        let wasSpeaking = self.messageID == messageID
        stop()
        guard !wasSpeaking, !text.isEmpty else { return }
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: localeIdentifier)
        self.messageID = messageID
        utteranceID = ObjectIdentifier(utterance)
        synthesizer.speak(utterance)
    }

    func stop() {
        utteranceID = nil
        messageID = nil
        synthesizer.stopSpeaking(at: .immediate)
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                      didFinish utterance: AVSpeechUtterance) {
        finish(ObjectIdentifier(utterance))
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                      didCancel utterance: AVSpeechUtterance) {
        finish(ObjectIdentifier(utterance))
    }

    private nonisolated func finish(_ completed: ObjectIdentifier) {
        Task { @MainActor [weak self] in
            // A delayed callback for an old voice operation cannot clear a
            // newer message's operation after a stop/switch.
            guard let self, self.utteranceID == completed else { return }
            self.utteranceID = nil
            self.messageID = nil
        }
    }
}
#endif

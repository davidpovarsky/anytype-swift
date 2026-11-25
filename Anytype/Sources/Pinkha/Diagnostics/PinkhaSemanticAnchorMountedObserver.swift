#if DEBUG && targetEnvironment(simulator) && PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import UIKit
import AnytypeCore
import Services
import ProtobufMessages

/// Observer only. It cannot select text, press Create/Cancel, mutate a block,
/// replace Invocation's handler, or synthesize an editor/reducer event.
@MainActor
final class PinkhaSemanticAnchorMountedObserver {
    private typealias Fixture = PinkhaSemanticAnchorMountedFixture
    private static var active: PinkhaSemanticAnchorMountedObserver?
    private let fixture: Fixture
    private weak var editor: EditorPageController?
    private let model: any EditorPageViewModelProtocol
    private let label: UILabel
    private let mode: String
    private var lease: PinkhaNativeReadLease?
    private var phase = "STARTING"
    private var preparations = 0
    private var cancellations = 0
    private var applyAttempts = 0
    private var documentPublications = 0
    private var marker: String?
    private var cancelledMarker: String?
    private weak var pendingApply: PinkhaHeartSemanticAnchorPending?
    private var receipt: [String: Any]
    private var task: Task<Void, Never>?

    static func startIfRequested(editor: EditorPageController) {
        let env = ProcessInfo.processInfo.environment
        guard env["PINKHA_SEMANTIC_MOUNTED_UI"] == "1" else { return }
        do {
            let fixture = try Fixture.loadForUI()
            guard editor.viewModel?.document.spaceId == fixture.spaceID,
                  editor.viewModel?.document.objectId == fixture.objectID else { return }
            if let active {
                try Fixture.require(active.editor === editor, "editor-rebound-in-owned-journey")
                return
            }
            let observer = try Self(fixture: fixture, editor: editor, mode: env["PINKHA_SEMANTIC_MOUNTED_PHASE"] ?? "")
            active = observer
            observer.task = Task { await observer.start() }
        } catch {
            if let window = editor.viewIfLoaded?.window {
                let label = makeLabel(in: window); label.text = "MOUNTED_FAIL"
                label.accessibilityValue = "{\"failure\":\"owned-fixture-setup-rejected\"}"
            }
        }
    }

    static func prepared(editor: EditorPageController, textView: TextViewWithPlaceholder,
                         blockID: String, range: NSRange, pending: PinkhaHeartSemanticAnchorPending,
                         lease: PinkhaNativeReadLease) {
        guard let active else { return }
        active.record {
            try active.requireEditor(editor)
            try Fixture.require(active.mode == "capture" && [0, 1].contains(active.preparations)
                && (active.phase == "READY" || active.phase == "CANCELLED_UNCHANGED"), "unexpected-preparation")
            try Fixture.require(blockID == active.fixture.blockID && textView.window === editor.viewIfLoaded?.window
                && textView.isFirstResponder && textView.selectedRange == range
                && range == NSRange(location: 0, length: active.fixture.text.utf16.count)
                && Data(textView.textStorage.string.utf8) == Data(active.fixture.text.utf8),
                "actual-selection-or-mount-differs")
            try lease.validate()
            try Fixture.require(lease.generation == active.lease?.generation && lease.accountID == active.fixture.accountID,
                "selected-owner-differs")
            active.preparations += 1
            active.marker = pending.marker
            active.receipt["selection"] = ["blockID": blockID, "location": range.location, "length": range.length,
                "visibleTextSHA256": Fixture.digest(Data(textView.textStorage.string.utf8))]
            if active.preparations == 2 {
                try Fixture.require(active.cancelledMarker != pending.marker, "cancelled-intent-reused")
            }
            try active.emit(active.preparations == 1 ? "CANCEL_CONFIRMATION_VISIBLE" : "CREATE_CONFIRMATION_VISIBLE")
        }
    }

    static func cancelled(editor: EditorPageController) {
        guard let active else { return }
        active.record {
            try active.requireEditor(editor)
            try Fixture.require(active.phase == "CANCEL_CONFIRMATION_VISIBLE" && active.preparations == 1
                && active.applyAttempts == 0 && active.documentPublications == 0, "cancel-followed-a-write")
            active.cancellations += 1
            active.cancelledMarker = active.marker
            active.task = Task { await active.verifyCancellation() }
        }
    }

    static func applyQueued(editor: EditorPageController, pending: PinkhaHeartSemanticAnchorPending) {
        guard let active else { return }
        active.record {
            try active.requireEditor(editor)
            try Fixture.require(active.phase == "CREATE_CONFIRMATION_VISIBLE" && active.cancellations == 1
                && active.applyAttempts == 0 && active.marker == pending.marker, "unexpected-explicit-apply")
            active.applyAttempts += 1
            active.pendingApply = pending
            try active.emit("APPLY_QUEUED")
        }
    }

    /// A completed apply failure is distinct from an unreturned native await.
    /// This records only the exact queued Pending; it never revalidates or
    /// mutates the document, retries the operation, or replaces its error.
    static func applyFailed(editor: EditorPageController,
                            pending: PinkhaHeartSemanticAnchorPending, error: Error) {
        guard let active, active.editor === editor, active.pendingApply === pending,
              active.applyAttempts == 1,
              ["APPLY_QUEUED", "MOUNTED_FAIL"].contains(active.phase) else { return }
        try? active.saveBoundaryEvidence(requireComplete: false)
        let observation = pending.applyObservation
        var values: [String: Any] = [
            "protocolVersion": 1,
            "phases": observation.phases.map(\.rawValue),
            "phasesTruncated": observation.phasesTruncated,
            "nativeReceiptDecoded": observation.nativeReceiptDecoded,
            "returnedError": PinkhaHeartSemanticAnchorApplyObservation.classify(error).rawValue,
            "observedAtApplyReturn": true,
            "realTimeProgress": false
        ]
        if let value = observation.latestPhase { values["latestPhase"] = value.rawValue }
        if let value = observation.nativeReplyBytes { values["nativeReplyBytes"] = value }
        if let value = observation.decodedNativeOutcome { values["decodedNativeOutcome"] = value.rawValue }
        if let value = observation.eventBytes { values["eventBytes"] = value }
        if let value = observation.publicationReturned { values["publicationReturned"] = value }
        if let value = observation.firstFailurePhase { values["firstFailurePhase"] = value.rawValue }
        if let value = observation.firstFailure { values["firstFailure"] = value.rawValue }
        if let semantic = error as? PinkhaHeartSemanticAnchorError,
           case .nativeRefusal(let outcome) = semantic {
            values["returnedNativeOutcome"] = outcome.rawValue
        }
        active.receipt["applyObservation"] = values
        if active.phase == "MOUNTED_FAIL" {
            // Preserve an earlier observer failure; append only this evidence.
            try? active.emit("MOUNTED_FAIL")
        } else {
            active.fail(SemanticAnchorMountedError.invariant("apply-returned-error"))
        }
    }

    /// Called at the actual BaseDocument main delivery, after fenced state conversion.
    /// This observes the existing route; it is not an alternative publication path.
    static func documentPublished(document: any BaseDocumentProtocol, fence: PinkhaHeartSemanticAnchorPublicationFence) {
        guard let active, (active.model.document as AnyObject) === (document as AnyObject),
              fence.matches(spaceID: active.fixture.spaceID, objectID: active.fixture.objectID) else { return }
        active.record {
            try active.requireCurrent()
            try Fixture.require(active.phase == "APPLY_QUEUED" && active.applyAttempts == 1
                && active.documentPublications == 0 && fence.generation == active.lease?.generation
                && fence.accountID == active.fixture.accountID, "ordinary-document-publication-differs")
            let value = try active.documentText()
            try Fixture.require(value.marks.marks.contains { $0.type == .link && $0.param == active.marker },
                "native-mark-missing-at-ordinary-publication")
            active.documentPublications += 1
            active.receipt["publicationGeneration"] = fence.generation.uuidString.lowercased()
        }
    }

    static func verified(editor: EditorPageController, capture: PinkhaHeartSemanticAnchorVerifiedCapture) {
        guard let active else { return }
        active.record {
            try active.requireEditor(editor)
            try Fixture.require(active.phase == "APPLY_QUEUED" && active.applyAttempts == 1
                && capture.generation == active.lease?.generation && capture.receipt.marker == active.marker,
                "verified-ui-capture-differs")
            try active.saveBoundaryEvidence(requireComplete: true)
            active.task = Task { await active.verifyCapture(capture) }
        }
    }

    /// Copy only bytes already observed by the pending client. No native read,
    /// mutation, authority decision, event publication, or retry occurs here.
    private func saveBoundaryEvidence(requireComplete: Bool) throws {
        guard let pendingApply else {
            try Fixture.require(!requireComplete, "native-boundary-pending-missing")
            return
        }
        let observed = pendingApply.mountedDiagnosticSnapshots
        let names = ["preflight": "pinkha-semantic-page154-preflight.pb",
                     "nativeReply": "pinkha-semantic-page154-native-reply.json",
                     "readback": "pinkha-semantic-page154-readback.pb"]
        if requireComplete {
            try Fixture.require(Set(observed.keys) == Set(names.keys), "native-boundary-evidence-incomplete")
        }
        var files: [String: Any] = [:]
        for role in names.keys.sorted() {
            guard let bytes = observed[role], let name = names[role] else { continue }
            let path = try Fixture.fileURL(name)
            if FileManager.default.fileExists(atPath: path.path) {
                try Fixture.require(try Data(contentsOf: path) == bytes, "native-boundary-original-bytes-changed")
            } else {
                try bytes.write(to: path, options: .atomic)
                try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: path.path)
            }
            files[role] = ["filename": name, "bytes": bytes.count, "sha256": Fixture.digest(bytes)]
        }
        receipt["nativeBoundaryEvidence"] = ["protocolVersion": 1, "files": files,
            "source": "actual-client-call-results", "extraNativeCalls": 0]
    }

    private init(fixture: Fixture, editor: EditorPageController, mode: String) throws {
        try Fixture.require(["capture", "reopen"].contains(mode), "invalid-ui-phase")
        guard let model = editor.viewModel, let window = editor.viewIfLoaded?.window,
              window.windowScene?.activationState == .foregroundActive else {
            throw SemanticAnchorMountedError.invariant("real-editor-not-mounted")
        }
        let output = mode == "capture" ? Fixture.captureFileName : Fixture.reopenFileName
        try Fixture.require(!FileManager.default.fileExists(atPath: try Fixture.fileURL(output).path),
            "existing-owned-phase-receipt")
        self.fixture = fixture; self.editor = editor; self.model = model; self.mode = mode
        label = Self.makeLabel(in: window)
        receipt = ["protocol": "pinkha-semantic-page154-mounted-v1", "sourceSHA": fixture.sourceSHA,
            "runID": fixture.runID, "runAttempt": fixture.runAttempt, "nonce": fixture.nonce,
            "accountID": fixture.accountID, "spaceID": fixture.spaceID, "objectID": fixture.objectID,
            "blockID": fixture.blockID, "excludedBlockID": fixture.excludedBlockID,
            "processID": Int(ProcessInfo.processInfo.processIdentifier), "preparationProcessID": Int(fixture.preparationProcessID),
            "mode": mode, "startedAt": Date().timeIntervalSince1970, "checks": [String: Bool]()]
    }

    private func start() async {
        do {
            try await waitUntil { self.model.document.isOpened && self.textView() != nil }
            try Fixture.require(Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly
                && Container.shared.accountManager().account.id == fixture.accountID, "actual-account-space-differs")
            try Fixture.require(InvocationSettings.handler is InvocationMesagesHandler
                && InvocationSettings.handler?.isLogEnabled == false, "ordinary-handler-or-private-logging-differs")
            let version = try await ClientCommands.appGetVersion().invoke().version
            try Fixture.require(version == PinkhaHeartSemanticAnchorProfile.runtimeVersion, "page154-runtime-missing")
            lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: fixture.spaceID)
            try requireCurrent()
            try Fixture.require(lease?.accountID == fixture.accountID, "actual-lease-account-differs")
            receipt["generation"] = lease!.generation.uuidString.lowercased()
            receipt["runtimeVersion"] = version
            receipt["nativeManifestSHA256"] = PinkhaHeartSemanticAnchorProfile.sourceManifestSHA256
            try Fixture.require(ProcessInfo.processInfo.processIdentifier != fixture.preparationProcessID,
                "ui-must-be-a-cold-process-after-preparation")
            if mode == "reopen" { try await verifyColdReopen(); return }
            let blocks = try await nativeBlocks()
            try Fixture.require(try Fixture.bytes(blocks.0) == Fixture.bytes(fixture.beforeBlock())
                && Fixture.bytes(blocks.1) == Fixture.bytes(fixture.excludedBlock()), "initial-native-snapshot-differs")
            let visible = try documentText()
            try Fixture.require(visible.marks == blocks.0.text.marks, "initial-document-marks-differ")
            try emit("READY")
        } catch { fail(error) }
    }

    private func verifyCancellation() async {
        do {
            let blocks = try await nativeBlocks()
            try requireCurrent()
            try Fixture.require(applyAttempts == 0 && documentPublications == 0 && cancellations == 1,
                "cancel-dispatched-write")
            try Fixture.require(try Fixture.bytes(blocks.0) == Fixture.bytes(fixture.beforeBlock())
                && Fixture.bytes(blocks.1) == Fixture.bytes(fixture.excludedBlock()), "cancel-changed-native-block")
            try Fixture.require(try documentText().marks == fixture.beforeBlock().text.marks, "cancel-changed-document")
            receipt["cancelNativeBlockSHA256"] = Fixture.digest(try Fixture.bytes(blocks.0))
            receipt["cancelledMarker"] = cancelledMarker
            try emit("CANCELLED_UNCHANGED")
        } catch { fail(error) }
    }

    private func verifyCapture(_ capture: PinkhaHeartSemanticAnchorVerifiedCapture) async {
        do {
            // Capture the actual rendered document before this observer's independent readback.
            try await waitUntil { self.documentPublications == 1 && self.hasRenderedMarker(capture.receipt.marker) }
            try requireCurrent()
            let document = try documentText()
            let rendered = try renderedLinks()
            try Fixture.require(document.marks.marks.contains { $0.type == .link && $0.param == capture.receipt.marker },
                "mounted-document-did-not-consume-native-mark")
            let blocks = try await nativeBlocks()
            let before = try fixture.beforeBlock()
            let after = blocks.0
            let snapshot = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: after)
            let previous = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: before)
            try Fixture.require(snapshot.digest == capture.receipt.afterTextMarksSHA256
                && previous.digest == capture.receipt.beforeTextMarksSHA256, "native-receipt-snapshot-differs")
            try Fixture.require(after.text.marks == document.marks, "rendered-document-native-marks-differ")
            var restored = after; restored.text.marks = before.text.marks
            try Fixture.require(try Fixture.bytes(restored) == Fixture.bytes(before)
                && Fixture.bytes(blocks.1) == Fixture.bytes(fixture.excludedBlock()), "non-mark-or-unselected-block-changed")
            let value = capture.receipt
            try Fixture.require(value.spaceID == fixture.spaceID && value.objectID == fixture.objectID
                && value.blockID == fixture.blockID && value.marker == marker, "native-receipt-identity-differs")
            receipt["native"] = ["anchorID": value.anchorID, "marker": value.marker, "changeID": value.changeID,
                "nativeChangeSHA256": value.nativeChangeSHA256,
                "beforeTextMarksSHA256": value.beforeTextMarksSHA256, "afterTextMarksSHA256": value.afterTextMarksSHA256]
            receipt["afterBlockBase64"] = try Fixture.bytes(after).base64EncodedString()
            receipt["documentMarksBase64"] = try Fixture.bytes(document.marks).base64EncodedString()
            receipt["renderedLinks"] = rendered
            receipt["checks"] = ["actualEditorAndInputMounted": true, "actualUserSelection": true,
                "cancelNativeUnchanged": true, "explicitApplyOnce": true, "ordinaryDocumentPublication": true,
                "renderedBeforeIndependentReadback": true, "nativeReceiptVerified": true,
                "nonMarkAndExcludedBlockUnchanged": true, "middlewareLoggingDisabled": true]
            receipt["finishedAt"] = Date().timeIntervalSince1970
            try emit("PASS_CAPTURE_MOUNTED")
        } catch { fail(error) }
    }

    private func verifyColdReopen() async throws {
        let raw = try Data(contentsOf: Fixture.fileURL(Fixture.captureFileName))
        try Fixture.require(raw.count <= 65_536, "capture-receipt-too-large")
        guard let captured = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
              let native = captured["native"] as? [String: String],
              let marker = native["marker"], let after64 = captured["afterBlockBase64"] as? String,
              let afterBytes = Data(base64Encoded: after64),
              let previousPID = captured["processID"] as? Int else {
            throw SemanticAnchorMountedError.invariant("capture-receipt-invalid")
        }
        try Fixture.require(captured["phase"] as? String == "PASS_CAPTURE_MOUNTED"
            && captured["sourceSHA"] as? String == fixture.sourceSHA && captured["nonce"] as? String == fixture.nonce
            && captured["runID"] as? String == fixture.runID && captured["runAttempt"] as? String == fixture.runAttempt
            && captured["accountID"] as? String == fixture.accountID && captured["spaceID"] as? String == fixture.spaceID
            && captured["objectID"] as? String == fixture.objectID && captured["blockID"] as? String == fixture.blockID,
            "capture-receipt-owner-differs")
        try Fixture.require(previousPID > 0 && previousPID != Int(ProcessInfo.processInfo.processIdentifier)
            && captured["generation"] as? String != lease?.generation.uuidString.lowercased(), "cold-process-owner-not-distinct")
        try await waitUntil { self.hasRenderedMarker(marker) }
        let document = try documentText()
        let rendered = try renderedLinks()
        let blocks = try await nativeBlocks()
        try Fixture.require(try Fixture.bytes(blocks.0) == afterBytes
            && Fixture.bytes(blocks.1) == Fixture.bytes(fixture.excludedBlock())
            && blocks.0.text.marks == document.marks, "cold-reopen-native-or-rendered-snapshot-differs")
        try Fixture.require(try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: blocks.0).digest == native["afterTextMarksSHA256"],
            "cold-reopen-digest-differs")
        try Fixture.require(preparations == 0 && applyAttempts == 0 && documentPublications == 0, "cold-reopen-mutated")
        receipt["captureProcessID"] = previousPID
        receipt["captureReceiptSHA256"] = Fixture.digest(raw)
        receipt["native"] = native; receipt["afterBlockBase64"] = after64
        receipt["documentMarksBase64"] = try Fixture.bytes(document.marks).base64EncodedString()
        receipt["renderedLinks"] = rendered
        receipt["checks"] = ["actualEditorAndInputMounted": true, "distinctColdProcessAndGeneration": true,
            "persistedNativeBlockIdentical": true, "renderedBeforeIndependentReadback": true,
            "excludedBlockUnchanged": true, "noNewApply": true, "middlewareLoggingDisabled": true]
        receipt["finishedAt"] = Date().timeIntervalSince1970
        try emit("PASS_COLD_REOPEN_MOUNTED")
    }

    private func requireEditor(_ value: EditorPageController) throws {
        try Fixture.require(editor === value, "selection-editor-changed")
        try requireCurrent()
    }

    private func requireCurrent() throws {
        guard let editor, let current = editor.viewModel, current === model,
              let window = editor.viewIfLoaded?.window, window.windowScene?.activationState == .foregroundActive,
              current.document.spaceId == fixture.spaceID, current.document.objectId == fixture.objectID,
              current.document.isOpened, Container.shared.accountManager().account.id == fixture.accountID,
              let lease else { throw SemanticAnchorMountedError.invariant("mounted-owner-retired") }
        try lease.validate()
    }

    private func documentText() throws -> BlockText {
        guard let info = model.document.infoContainer.get(id: fixture.blockID), case .text(let text) = info.content,
              Data(text.text.utf8) == Data(fixture.text.utf8) else {
            throw SemanticAnchorMountedError.invariant("actual-document-text-differs")
        }
        return text
    }

    private func textView() -> TextViewWithPlaceholder? {
        guard let editor, let window = editor.viewIfLoaded?.window else { return nil }
        var views = [editor.view!]
        while let view = views.popLast() {
            if let content = view as? TextBlockContentView,
               content.pinkhaSemanticAnchorContext?.blockID == fixture.blockID,
               content.window === window, content.textView.textView.window === window,
               Data(content.textView.textView.textStorage.string.utf8) == Data(fixture.text.utf8),
               content.convert(content.bounds, to: window).intersects(window.bounds) {
                return content.textView.textView
            }
            views.append(contentsOf: view.subviews)
        }
        return nil
    }

    private func renderedLinks() throws -> [[String: Any]] {
        guard let textView = textView() else { throw SemanticAnchorMountedError.invariant("actual-text-input-not-mounted") }
        var result: [[String: Any]] = []
        textView.textStorage.enumerateAttribute(.link, in: NSRange(location: 0, length: textView.textStorage.length)) {
            value, range, _ in
            if let url = value as? URL {
                result.append(["marker": url.absoluteString, "location": range.location, "length": range.length])
            }
        }
        return result
    }

    private func hasRenderedMarker(_ value: String) -> Bool {
        guard let links = try? renderedLinks(), links.count == 1 else { return false }
        return links[0]["marker"] as? String == value && links[0]["location"] as? Int == 0
            && links[0]["length"] as? Int == fixture.text.utf16.count
    }

    private func nativeBlocks() async throws -> (Anytype_Model_Block, Anytype_Model_Block) {
        try requireCurrent()
        let shown = try await ClientCommands.objectShow(.with {
            $0.spaceID = fixture.spaceID; $0.objectID = fixture.objectID; $0.contextID = fixture.objectID
        }).invoke()
        try requireCurrent()
        let target = shown.objectView.blocks.filter { $0.id == fixture.blockID }
        let other = shown.objectView.blocks.filter { $0.id == fixture.excludedBlockID }
        try Fixture.require(shown.objectView.rootID == fixture.objectID && target.count == 1 && other.count == 1,
            "native-readback-identity-differs")
        return (target[0], other[0])
    }

    private func waitUntil(_ predicate: () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(30)
        while !predicate() {
            try Fixture.require(phase != "MOUNTED_FAIL" && Date() < deadline, "mounted-observation-timeout")
            try await Task.sleep(for: .milliseconds(20))
        }
    }

    private func record(_ body: () throws -> Void) {
        guard phase != "MOUNTED_FAIL" else { return }
        do { try body() } catch { fail(error) }
    }

    private func fail(_ error: Error) {
        if case SemanticAnchorMountedError.invariant(let label) = error { receipt["failure"] = label }
        else { receipt["failure"] = "native-or-owner-observation-failed" }
        receipt["finishedAt"] = Date().timeIntervalSince1970
        try? emit("MOUNTED_FAIL")
    }

    private func emit(_ next: String) throws {
        phase = next
        receipt["phase"] = next; receipt["preparations"] = preparations; receipt["cancellations"] = cancellations
        receipt["applyAttempts"] = applyAttempts; receipt["documentPublications"] = documentPublications
        let data = try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys])
        try Fixture.require(data.count <= 65_536, "receipt-too-large")
        try data.write(to: Fixture.fileURL(mode == "capture" ? Fixture.captureFileName : Fixture.reopenFileName), options: .atomic)
        label.text = next; label.accessibilityValue = String(decoding: data, as: UTF8.self)
    }

    private static func makeLabel(in window: UIWindow) -> UILabel {
        let label = UILabel(frame: CGRect(x: 8, y: window.safeAreaInsets.top + 6, width: max(1, window.bounds.width - 16), height: 20))
        label.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        label.backgroundColor = .systemBackground; label.textColor = .label
        label.isUserInteractionEnabled = false; label.isAccessibilityElement = true
        label.accessibilityIdentifier = "pinkha.semanticAnchor.mounted-status"
        label.autoresizingMask = [.flexibleWidth, .flexibleBottomMargin]
        window.addSubview(label)
        return label
    }
}
#endif

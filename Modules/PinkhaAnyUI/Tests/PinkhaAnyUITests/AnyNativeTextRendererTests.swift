#if canImport(UIKit)
import UIKit
import XCTest
@testable import PinkhaAnyUI

private final class RenderStorageEdits: NSObject, NSTextStorageDelegate {
    var changedCharacters = false
    func textStorage(_ textStorage: NSTextStorage, didProcessEditing editedMask: NSTextStorage.EditActions,
                     range editedRange: NSRange, changeInLength delta: Int) {
        changedCharacters = changedCharacters || editedMask.contains(.editedCharacters)
    }
}

@MainActor
final class AnyNativeTextRendererTests: XCTestCase {
    func testEqualNativeTextChangesAttributesWithoutReplacingCharactersOrSelection() {
        let input = UITextView()
        let text = "אב😀xyz"
        input.attributedText = NSAttributedString(string: text,
            attributes: [.foregroundColor: UIColor.red, .link: URL(string: "https://example.com")!])
        let selection = NSRange(location: 2, length: 2)
        input.selectedRange = selection
        let edits = RenderStorageEdits()
        input.textStorage.delegate = edits
        let paragraph = NSMutableParagraphStyle()
        paragraph.baseWritingDirection = .rightToLeft
        paragraph.alignment = .center
        let incoming = NSAttributedString(string: text,
            attributes: [.foregroundColor: UIColor.blue, .paragraphStyle: paragraph])

        XCTAssertTrue(AnyNativeTextRenderer.apply(incoming, to: input, isComposing: false))

        XCTAssertFalse(edits.changedCharacters)
        XCTAssertEqual(input.text, text)
        XCTAssertEqual(input.selectedRange, selection)
        XCTAssertNil(input.textStorage.attribute(.link, at: 0, effectiveRange: nil))
        let actual = input.textStorage.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle
        XCTAssertEqual(actual?.baseWritingDirection, .rightToLeft)
        XCTAssertEqual(actual?.alignment, .center)
    }

    func testChangedNativeTextReplacesCharactersAndKeepsValidSelection() {
        let input = UITextView()
        input.text = "old native text"
        input.selectedRange = NSRange(location: 2, length: 5)
        let incoming = NSAttributedString(string: "new")
        XCTAssertTrue(AnyNativeTextRenderer.apply(incoming, to: input, isComposing: false))
        XCTAssertEqual(input.text, "new")
        XCTAssertEqual(input.selectedRange, NSRange(location: 2, length: 1))
    }

    func testMarkedTextKeepsCharactersSelectionAndAttributesUntilCommit() {
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "live marked buffer",
                                                  attributes: [.foregroundColor: UIColor.red])
        input.selectedRange = NSRange(location: 4, length: 3)
        let before = NSAttributedString(attributedString: input.attributedText)
        let selection = input.selectedRange
        let edits = RenderStorageEdits()
        input.textStorage.delegate = edits
        XCTAssertFalse(AnyNativeTextRenderer.apply(NSAttributedString(string: "older native text"),
                                                   to: input, isComposing: true))
        XCTAssertFalse(edits.changedCharacters)
        XCTAssertEqual(input.attributedText, before)
        XCTAssertEqual(input.selectedRange, selection)
    }
}
#endif

#if canImport(UIKit) && canImport(Network)
import Network
import PinkhaAnyEngine
@testable import PinkhaAnyHost
import PinkhaAnyIntegration

extension AnyNativeTextRendererTests {
    func testMountedControllerRefreshesCanonicalEquivalentLatinTextInTheSameCell() async throws {
        try await exerciseMountedRefresh(before: "Xcaf\u{00E9}Y", after: "Xcafe\u{0301}Y")
    }

    func testMountedControllerRefreshesHebrewCombiningOrderInTheSameCell() async throws {
        try await exerciseMountedRefresh(before: "X\u{05E9}\u{05B8}\u{05C1}Y",
                                         after: "X\u{05E9}\u{05C1}\u{05B8}Y")
    }

    /// Controlled HTTP/hosted UIKit coverage, not a claim about a real Native
    /// account. Every model value is obtained through its original public load.
    @MainActor
    private func exerciseMountedRefresh(before: String, after: String) async throws {
        XCTAssertEqual(before, after, "The regression requires canonical equivalence")
        XCTAssertNotEqual(Array(before.utf8), Array(after.utf8))
        XCTAssertNotEqual(Array(before.utf16), Array(after.utf16))
        let fixture = try MountedRefreshHTTPFixture(before: before, after: after)
        let lifetime = AnyUIPresentationLifetime()
        var session: AnyApplicationSession?
        var window: UIWindow?
        var previousKey: UIWindow?
        var firstFailure: (any Error)?
        do {
            let baseURL = try await fixture.start()
            let workspace = try AnyTorahWorkspace(accountID: fixture.accountID, spaceID: fixture.spaceID)
            let client = try AnyHTTPClient(baseURL: baseURL, expectedAccountID: workspace.accountID)
            let activeSession = try await AnyApplicationSession.connect(client: client, workspace: workspace)
            session = activeSession
            let capabilities = try await AnyUIFoundationCapabilities.verify(client: client, session: activeSession)
            let marker = try await AnyNativeNoteMarker.verify(client: client, workspace: workspace,
                                                               collectionID: fixture.notesID)
            let journal = MountedRefreshUnusedJournal(workspace: workspace)
            let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace,
                                                   journal: journal, allowedTypeIDs: ["page"])
            let presentation = try AnyDocumentPresentation(client: client, session: activeSession,
                objects: objects, blocks: blocks, capabilities: capabilities,
                operations: AnyGuardedTorahOperationStore(client: client, workspace: workspace),
                noteMarker: marker, objectID: fixture.objectID, lifetime: lifetime,
                recovery: AnyNativeLibraryRecovery(workspace: workspace))
            let controller = AnyNativeEditorController(presentation: presentation)
            let scene = try XCTUnwrap(UIApplication.shared.connectedScenes
                .compactMap { $0 as? UIWindowScene }.first { $0.activationState == .foregroundActive })
            previousKey = scene.windows.first(where: \.isKeyWindow)
            let mountedWindow = UIWindow(windowScene: scene)
            mountedWindow.frame = CGRect(x: 0, y: 0, width: 400, height: 800)
            mountedWindow.rootViewController = controller
            window = mountedWindow
            mountedWindow.makeKeyAndVisible()

            // viewDidAppear uses the original public load. Wait for that owner,
            // its complete read, and both explicit observation connections.
            try await waitForMountedRefresh(fixture) {
                presentation.read != nil && !presentation.isLoading && presentation.isMounted &&
                    controller.isForegroundMounted && fixture.heldObservationKinds == ["editor", "claims"]
            }
            await presentation.load()
            try requireCompleteMountedRead(presentation, fixture: fixture, expected: before)
            controller.render()
            try await waitForMountedRefresh(fixture) {
                controller.view.layoutIfNeeded()
                return Self.refreshTable(controller.view)?.visibleCells.count == 1
            }
            let table = try XCTUnwrap(Self.refreshTable(controller.view))
            let originalCell = try XCTUnwrap(table.visibleCells.first)
            let originalPath = try XCTUnwrap(table.indexPath(for: originalCell))
            let input = try XCTUnwrap(Self.refreshInput(originalCell, blockID: fixture.blockID))
            XCTAssertTrue(input.becomeFirstResponder())
            let selected = NSRange(location: 0, length: 1) // Stable ASCII prefix in both encodings.
            input.selectedRange = selected
            try await waitForMountedRefresh(fixture) {
                input.isFirstResponder && input.selectedRange == selected &&
                    presentation.selectedTextRange == selected && presentation.focusedBlockID == fixture.blockID
            }
            let owner = presentation.mountedOwnerID
            let sourceRead = try XCTUnwrap(presentation.read)
            let sourceBlock = try XCTUnwrap(sourceRead.snapshot.blocks.first)
            let category = controller.traitCollection.preferredContentSizeCategory
            let interfaceDirection = controller.view.semanticContentAttribute
            XCTAssertEqual(sourceRead.snapshot.depthFirstIDs, [fixture.blockID])
            XCTAssertTrue(controller.isBlockVisible(fixture.blockID))
            XCTAssertTrue(table.indexPathsForVisibleRows?.contains(originalPath) == true)
            XCTAssertEqual(Array(input.text.utf8), Array(before.utf8))
            XCTAssertEqual(Array(input.text.utf16), Array(before.utf16))
            XCTAssertEqual(Array(input.attributedText.string.utf8), Array(before.utf8))
            XCTAssertEqual(Array(input.attributedText.string.utf16), Array(before.utf16))
            XCTAssertEqual(input.blockID, fixture.blockID)
            XCTAssertTrue(input.window === mountedWindow)
            attachMountedRefresh(presentation, input: input, phase: "before")

            try fixture.advanceSource()
            await presentation.load()
            try requireCompleteMountedRead(presentation, fixture: fixture, expected: after)
            let refreshed = try XCTUnwrap(presentation.read)
            let refreshedBlock = try XCTUnwrap(refreshed.snapshot.blocks.first)
            XCTAssertNotEqual(refreshed.nativeVersion, sourceRead.nativeVersion)
            XCTAssertEqual(refreshed.generation, sourceRead.generation)
            XCTAssertEqual(refreshed.engineStartedAt, sourceRead.engineStartedAt)
            XCTAssertEqual(refreshed.snapshot.depthFirstIDs, sourceRead.snapshot.depthFirstIDs)
            XCTAssertEqual(refreshedBlock.type, sourceBlock.type)
            XCTAssertEqual(refreshedBlock.native["style"], sourceBlock.native["style"])
            XCTAssertEqual(controller.traitCollection.preferredContentSizeCategory, category)
            XCTAssertEqual(controller.view.semanticContentAttribute, interfaceDirection)

            // Same IDs take the controller's configureVisibleCells path. No
            // diffable replacement or local typing can mask the cache decision.
            controller.render()
            controller.view.layoutIfNeeded()
            let currentCell = try XCTUnwrap(table.visibleCells.first)
            let currentInput = try XCTUnwrap(Self.refreshInput(currentCell, blockID: fixture.blockID))
            XCTAssertEqual(table.visibleCells.count, 1)
            XCTAssertTrue(currentCell === originalCell)
            XCTAssertTrue(currentInput === input)
            XCTAssertEqual(table.indexPath(for: currentCell), originalPath)
            XCTAssertTrue(table.indexPathsForVisibleRows?.contains(originalPath) == true)
            XCTAssertTrue(controller.isBlockVisible(fixture.blockID))
            XCTAssertEqual(presentation.mountedOwnerID, owner)
            XCTAssertEqual(presentation.workspace, workspace)
            XCTAssertEqual(presentation.objectID, fixture.objectID)
            XCTAssertEqual(currentInput.blockID, fixture.blockID)
            XCTAssertTrue(currentInput.window === mountedWindow)
            XCTAssertTrue(currentInput.isFirstResponder)
            XCTAssertEqual(Array(currentInput.text.utf8), Array(after.utf8))
            XCTAssertEqual(Array(currentInput.text.utf16), Array(after.utf16))
            XCTAssertEqual(Array(currentInput.attributedText.string.utf8), Array(after.utf8))
            XCTAssertEqual(Array(currentInput.attributedText.string.utf16), Array(after.utf16))
            XCTAssertNotEqual(Array(currentInput.text.utf16), Array(before.utf16))
            XCTAssertEqual(currentInput.selectedRange, selected)
            XCTAssertEqual(presentation.selectedTextRange, selected)
            XCTAssertFalse(presentation.hasPendingEdits)
            XCTAssertEqual(presentation.writeStatusAccessibilityValue, "clean")
            attachMountedRefresh(presentation, input: currentInput, phase: "after")
            try fixture.requireHealthyCompletedReads()
            let journalCalls = await journal.calls
            XCTAssertEqual(journalCalls, 0)
        } catch { firstFailure = error }

        // Mark the expected cancellation before revocation closes the two held
        // streams. The original lifetime/session own their tasks and drainage.
        fixture.beginDrain()
        lifetime.revoke()
        window?.endEditing(true)
        await lifetime.drain()
        await session?.revokeAndDrain()
        do { try await fixture.stop() }
        catch {
            if firstFailure == nil { firstFailure = error }
            else { XCTFail("Additional owned loopback cleanup failure: \(error)") }
        }
        do {
            let attachment = XCTAttachment(data: try fixture.retainedTrace(), uniformTypeIdentifier: "public.json")
            attachment.name = "mounted-refresh-controlled-http"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            if firstFailure == nil { firstFailure = error }
            else { XCTFail("Additional controlled HTTP trace retention failure: \(error)") }
        }
        window?.isHidden = true
        window?.rootViewController = nil
        previousKey?.makeKeyAndVisible()
        if let firstFailure { throw firstFailure }
    }

    @MainActor
    private func requireCompleteMountedRead(_ presentation: AnyDocumentPresentation,
                                           fixture: MountedRefreshHTTPFixture, expected: String) throws {
        try fixture.requireHealthy()
        XCTAssertFalse(presentation.isLoading)
        XCTAssertNil(presentation.message)
        XCTAssertNil(presentation.torah.message)
        XCTAssertTrue(presentation.isMounted)
        XCTAssertTrue(presentation.canMutate)
        XCTAssertFalse(presentation.hasPendingEdits)
        let value = try XCTUnwrap(presentation.read)
        XCTAssertEqual(value.snapshot.spaceID, fixture.spaceID)
        XCTAssertEqual(value.snapshot.objectID, fixture.objectID)
        XCTAssertEqual(value.snapshot.blocks.count, 1)
        let block = try XCTUnwrap(value.snapshot.blocks.first)
        XCTAssertEqual(block.id, fixture.blockID)
        XCTAssertEqual(Array(block.text.utf8), Array(expected.utf8))
        XCTAssertEqual(Array(block.text.utf16), Array(expected.utf16))
        XCTAssertEqual(Array(presentation.source(for: block).utf8), Array(expected.utf8))
        XCTAssertEqual(Array(presentation.source(for: block).utf16), Array(expected.utf16))
        XCTAssertEqual(Array(value.markdown.utf8), Array(expected.utf8))
        XCTAssertEqual(Array(value.markdown.utf16), Array(expected.utf16))
        XCTAssertEqual(presentation.nativeProperties?.objectID, fixture.objectID)
        XCTAssertEqual(presentation.nativeProperties?.readiness.complete, true)
    }

    @MainActor
    private func waitForMountedRefresh(_ fixture: MountedRefreshHTTPFixture,
                                       condition: @MainActor () -> Bool) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(5))
        while ContinuousClock.now < deadline {
            try Task.checkCancellation()
            try fixture.requireHealthy()
            if condition() { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw MountedRefreshFixtureFailure.invalid("mounted UIKit readiness deadline")
    }

    @MainActor
    private static func refreshTable(_ view: UIView) -> UITableView? {
        if let table = view as? UITableView, table.accessibilityIdentifier == "any-native-editor-blocks" { return table }
        return view.subviews.lazy.compactMap { refreshTable($0) }.first
    }

    @MainActor
    private static func refreshInput(_ view: UIView, blockID: String) -> AnyNativeTextView? {
        if let input = view as? AnyNativeTextView,
           input.accessibilityIdentifier == "any-native-block-" + blockID { return input }
        return view.subviews.lazy.compactMap { refreshInput($0, blockID: blockID) }.first
    }

    @MainActor
    private func attachMountedRefresh(_ presentation: AnyDocumentPresentation,
                                      input: AnyNativeTextView, phase: String) {
        guard let read = presentation.read, let block = read.snapshot.blocks.first else {
            XCTFail("The mounted observation requires the actual completed read"); return
        }
        let observation: [String: Any] = [
            "scope": "controlled-loopback-hosted-UIKit-not-Native-acceptance", "phase": phase,
            "accountID": presentation.workspace.accountID, "spaceID": presentation.workspace.spaceID,
            "objectID": presentation.objectID, "blockID": block.id,
            "sessionGeneration": read.generation.uuidString, "engineStartedAt": read.engineStartedAt,
            "nativeShapedVersion": read.nativeVersion,
            "sourceUTF8": Array(presentation.source(for: block).utf8),
            "sourceUTF16": Array(presentation.source(for: block).utf16),
            "textUTF8": Array(input.text.utf8), "attributedUTF8": Array(input.attributedText.string.utf8),
            "textUTF16": Array(input.text.utf16), "attributedUTF16": Array(input.attributedText.string.utf16),
            "selection": [input.selectedRange.location, input.selectedRange.length]]
        do {
            let data = try JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
            let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            attachment.name = "mounted-refresh-" + phase
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch { XCTFail("Could not retain the actual mounted observation: \(error)") }
    }
}

private enum MountedRefreshFixtureFailure: Error, Sendable {
    case invalid(String)
}

private actor MountedRefreshUnusedJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private(set) var calls = 0
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        calls += 1; throw MountedRefreshFixtureFailure.invalid("unexpected creation reserve")
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        calls += 1; throw MountedRefreshFixtureFailure.invalid("unexpected creation record")
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        calls += 1; throw MountedRefreshFixtureFailure.invalid("unexpected creation lookup")
    }
}

/// All mutable state, continuations and Network callbacks are confined to
/// `queue`; immutable identities may be read by the MainActor XCTest owner.
/// No global URLProtocol registration, framework replacement or native process.
private final class MountedRefreshHTTPFixture: @unchecked Sendable {
    let accountID = "render-account"
    let spaceID = "render-space"
    let objectID = "render-object"
    let blockID = "render-block"
    let notesID = "render-notes"
    private let rootID = "render-claims-root"
    private let run = "controlled-render-run"
    private let before: String
    private let after: String
    private let queue = DispatchQueue(label: "pinkha.tests.mounted-refresh." + UUID().uuidString)
    private let listener: NWListener
    private var listenerClosed = false
    private var started = false
    private var draining = false
    private var stopping = false
    private var phase = 0
    private var failures: [String] = []
    private var requests = 0
    private var requestTrace: [[String: String]] = []
    private var readsByPhase = [0, 0]
    private var completedPropertiesByPhase = [0, 0]
    private var heldKinds: Set<String> = []
    private var connections: [UUID: NWConnection] = [:]
    private var startWaiter: CheckedContinuation<URL, any Error>?
    private var stopWaiter: CheckedContinuation<Void, any Error>?
    // Navigation mode is opt-in; all five original renderer methods keep the
    // exact original route values, deadlines and connection/request limits.
    let navigationNetworkID = "controlled-navigation-network"
    private let navigationRunID = String(repeating: "d", count: 64)
    private let navigationEnabled: Bool
    private let requestLimit: Int
    private let navigationEarliestSecond = Int64(Date().timeIntervalSince1970.rounded(.down))
    private var holdFirstNavigationDefinition: Bool
    private var heldNavigationDefinition: (id: UUID, connection: NWConnection)?
    private var navigationApplied: [Int64] = []
    private var navigationLastOpened: AnyJSON?
    private var navigationReadbackWrites: Set<Int> = []
    private var navigationEvents: [String] = []
    private var navigationObservationIDs: [UUID: String] = [:]
    private var navigationAllowedClosure: Set<UUID> = []

    init(before: String, after: String, navigationEnabled: Bool = false,
         holdFirstNavigationDefinition: Bool = false) throws {
        self.before = before; self.after = after
        self.navigationEnabled = navigationEnabled
        self.requestLimit = navigationEnabled ? 1_024 : 512
        self.holdFirstNavigationDefinition = holdFirstNavigationDefinition
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        listener = try NWListener(using: parameters, on: .any)
        // Network decrements this cumulative acceptance allowance for every
        // connection. The independent tracked simultaneous-connection cap is16.
        listener.newConnectionLimit = requestLimit
    }

    func start() async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard !self.started else {
                    continuation.resume(throwing: MountedRefreshFixtureFailure.invalid("duplicate start")); return
                }
                self.started = true; self.startWaiter = continuation
                self.listener.stateUpdateHandler = { [weak self] state in self?.listenerState(state) }
                self.listener.newConnectionHandler = { [weak self] connection in
                    guard let self else { connection.cancel(); return }
                    self.accept(connection)
                }
                self.listener.start(queue: self.queue)
                self.queue.asyncAfter(deadline: .now() + 5) { [weak self] in
                    guard let self, self.startWaiter != nil else { return }
                    self.fail("listener readiness deadline"); self.cancelOwnedConnections()
                    self.finishStart(.failure(MountedRefreshFixtureFailure.invalid("listener readiness deadline")))
                }
                self.queue.asyncAfter(deadline: .now() + 45) { [weak self] in
                    guard let self, !self.stopping else { return }
                    self.fail("fixture lifetime deadline"); self.cancelOwnedConnections()
                }
            }
        }
    }

    var heldObservationKinds: Set<String> { queue.sync { heldKinds } }

    func requireHealthy() throws {
        try queue.sync {
            guard failures.isEmpty else { throw MountedRefreshFixtureFailure.invalid(failures.joined(separator: "; ")) }
        }
    }

    func advanceSource() throws {
        try queue.sync {
            guard !draining, !stopping, phase == 0, failures.isEmpty,
                  readsByPhase[0] > 0, completedPropertiesByPhase[0] > 0,
                  heldKinds == ["editor", "claims"] else {
                throw MountedRefreshFixtureFailure.invalid("source advance requires the complete original read")
            }
            phase = 1
        }
    }

    func requireHealthyCompletedReads() throws {
        try queue.sync {
            guard failures.isEmpty, phase == 1,
                  readsByPhase.allSatisfy({ $0 > 0 }), completedPropertiesByPhase.allSatisfy({ $0 > 0 }),
                  heldKinds == ["editor", "claims"], requests <= requestLimit else {
                throw MountedRefreshFixtureFailure.invalid("incomplete controlled load closure: " + failures.joined(separator: "; "))
            }
        }
    }

    func beginDrain() { queue.sync { draining = true } }

    func retainedTrace() throws -> Data {
        try queue.sync {
            var value: [String: Any] = [
                "scope": "controlled-loopback-hosted-UIKit-not-Native-acceptance",
                "requests": requestTrace, "failures": failures,
                "queriesBySourcePhase": readsByPhase, "propertiesBySourcePhase": completedPropertiesByPhase,
                "heldObservationKinds": heldKinds.sorted(), "listenerCancelled": listenerClosed,
                "remainingOwnedConnections": connections.count]
            if navigationEnabled {
                value["navigationEnabled"] = true
                value["navigationEvents"] = navigationEvents
                value["localOpenMilliseconds"] = navigationApplied
                value["localOpenReadbackOrdinals"] = navigationReadbackWrites.sorted()
            }
            return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        }
    }

    func stop() async throws {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard self.stopWaiter == nil, !self.stopping else {
                    continuation.resume(throwing: MountedRefreshFixtureFailure.invalid("duplicate stop")); return
                }
                self.draining = true; self.stopping = true; self.stopWaiter = continuation
                self.cancelOwnedConnections()
                self.finishStopIfClosed()
                self.queue.asyncAfter(deadline: .now() + 5) { [weak self] in
                    guard let self, let waiter = self.stopWaiter else { return }
                    self.stopWaiter = nil
                    self.fail("owned listener/connection drain deadline")
                    waiter.resume(throwing: MountedRefreshFixtureFailure.invalid("owned listener/connection drain deadline"))
                }
            }
        }
    }

    private func listenerState(_ state: NWListener.State) {
        switch state {
        case .ready:
            guard let port = listener.port,
                  let url = URL(string: "http://127.0.0.1:\(port.rawValue)") else {
                fail("missing owned listener port"); cancelOwnedConnections(); return
            }
            finishStart(.success(url))
        case .failed(let error):
            fail("listener failed: \(error)")
            finishStart(.failure(error)); cancelOwnedConnections()
        case .cancelled:
            listenerClosed = true
            finishStart(.failure(MountedRefreshFixtureFailure.invalid("listener cancelled before readiness")))
            finishStopIfClosed()
        default: break
        }
    }

    private func finishStart(_ result: Result<URL, any Error>) {
        let waiter = startWaiter; startWaiter = nil; waiter?.resume(with: result)
    }

    private func finishStopIfClosed() {
        guard stopping, listenerClosed, connections.isEmpty, let waiter = stopWaiter else { return }
        stopWaiter = nil
        if failures.isEmpty { waiter.resume() }
        else { waiter.resume(throwing: MountedRefreshFixtureFailure.invalid(failures.joined(separator: "; "))) }
    }

    private func cancelOwnedConnections() {
        listener.cancel()
        for connection in connections.values { connection.cancel() }
    }

    private func fail(_ message: String) {
        if failures.count < 16 { failures.append(message) }
    }

    private func accept(_ connection: NWConnection) {
        let reject = stopping || connections.count >= 16
        if !stopping, connections.count >= 16 { fail("connection budget exceeded") }
        let id = UUID()
        connections[id] = connection
        connection.stateUpdateHandler = { [weak self] state in
            guard let self else { return }
            switch state {
            case .failed(let error):
                if !self.draining, !self.navigationAllowedClosure.contains(id) {
                    self.fail("connection failed: \(error)")
                }
                self.connections[id]?.cancel()
            case .cancelled:
                self.connections.removeValue(forKey: id)
                if let kind = self.navigationObservationIDs.removeValue(forKey: id) {
                    self.heldKinds.remove(kind)
                }
                self.finishStopIfClosed()
            default: break
            }
        }
        connection.start(queue: queue)
        // Even a late or over-budget accepted connection is tracked until its
        // actual cancellation callback; cleanup never drops an owned socket.
        if reject { connection.cancel(); return }
        receiveRequest(connection, accumulated: Data())
    }

    private func receiveRequest(_ connection: NWConnection, accumulated: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { [weak self] bytes, _, complete, error in
            guard let self else { connection.cancel(); return }
            if let error {
                if !self.draining { self.fail("request receive failed: \(error)") }
                connection.cancel(); return
            }
            var data = accumulated
            if let bytes { data.append(bytes) }
            do {
                guard data.count <= 32_768 else { throw MountedRefreshFixtureFailure.invalid("request byte budget") }
                guard let split = data.range(of: Data([13, 10, 13, 10])) else {
                    guard !complete, data.count <= 16_384 else { throw MountedRefreshFixtureFailure.invalid("incomplete header") }
                    self.receiveRequest(connection, accumulated: data); return
                }
                guard split.lowerBound <= 16_384,
                      let header = String(data: data[..<split.lowerBound], encoding: .utf8) else {
                    throw MountedRefreshFixtureFailure.invalid("invalid header")
                }
                let lines = header.components(separatedBy: "\r\n")
                let request = lines[0].split(separator: " ", omittingEmptySubsequences: false)
                guard request.count == 3, request[2] == "HTTP/1.1" else {
                    throw MountedRefreshFixtureFailure.invalid("unexpected request line")
                }
                var headers: [String: String] = [:]
                for line in lines.dropFirst() {
                    guard let colon = line.firstIndex(of: ":") else { throw MountedRefreshFixtureFailure.invalid("header separator") }
                    let key = line[..<colon].lowercased()
                    guard headers[key] == nil else { throw MountedRefreshFixtureFailure.invalid("duplicate header") }
                    headers[key] = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
                }
                guard headers["transfer-encoding"] == nil,
                      let length = Int(headers["content-length"] ?? "0"), (0...16_384).contains(length),
                      let port = self.listener.port,
                      headers["host"] == "127.0.0.1:\(port.rawValue)" else {
                    throw MountedRefreshFixtureFailure.invalid("request framing or host")
                }
                let body = data[split.upperBound...]
                if body.count < length {
                    guard !complete else { throw MountedRefreshFixtureFailure.invalid("incomplete body") }
                    self.receiveRequest(connection, accumulated: data); return
                }
                guard body.count == length else { throw MountedRefreshFixtureFailure.invalid("pipelined or excess body") }
                try self.route(connection, method: String(request[0]), target: String(request[1]),
                               body: Data(body), headers: headers)
            } catch {
                self.fail("request rejected: \(error)"); connection.cancel()
            }
        }
    }

    private func route(_ connection: NWConnection, method: String, target: String,
                       body: Data, headers: [String: String]) throws {
        requests += 1
        guard !stopping, requests <= requestLimit, target.hasPrefix("/"),
              let url = URLComponents(string: "http://127.0.0.1" + target), url.fragment == nil else {
            throw MountedRefreshFixtureFailure.invalid("request scope or count")
        }
        let parts = url.percentEncodedPath.split(separator: "/").map { String($0).removingPercentEncoding ?? "" }
        requestTrace.append(["method": method, "target": target, "sourcePhase": String(phase)])
        let queryItems = url.queryItems ?? []
        guard queryItems.count <= 1, queryItems.allSatisfy({ $0.name == "limit" && $0.value == "10000" }) else {
            throw MountedRefreshFixtureFailure.invalid("unexpected query")
        }
        let limited = queryItems.count == 1
        if try routeNavigation(connection, method: method, parts: parts, body: body,
                               headers: headers, limited: limited) { return }
        let space = ["v1", "spaces", spaceID]
        let text = phase == 0 ? before : after
        let version = phase == 0 ? "render-version-1" : "render-version-2"
        let value: AnyJSON
        if method == "GET" {
            guard body.isEmpty else { throw MountedRefreshFixtureFailure.invalid("GET body") }
            switch parts {
            case ["v1", "auth"] where !limited:
                value = .object(["authorized": .bool(true), "accountId": .string(accountID)])
            case ["v1", "health"] where !limited:
                value = .object(["status": .string("ok"), "account": .string(accountID), "startedAt": .string(run)])
            case ["v1", "pinkha", "capabilities"] where !limited:
                value = capabilities
            case space + ["members", "me"] where !limited:
                value = .object(["identity": .string(accountID), "status": .string("active"),
                                 "permission": .string(navigationEnabled ? "reader" : "owner")])
            case space + ["collections", notesID] where !limited:
                value = .object(["id": .string(notesID), "xKey": .string("pinkha-note-v1")])
            case space + ["pinkha", "document-targets", objectID] where !limited:
                value = targetProof
            case space + ["objects", objectID] where !limited:
                var properties: [String: AnyJSON] = ["name": .string("Mounted refresh fixture"),
                    "type": .string("page"), "collections": .array([])]
                if navigationEnabled, let navigationLastOpened {
                    properties["pinkhaLastOpenedV1"] = navigationLastOpened
                    navigationReadbackWrites.insert(navigationApplied.count)
                }
                value = .object(["objectId": .string(objectID), "record": .object([
                    "id": .string(objectID), "spaceId": .string(spaceID), "any": .object(properties)])])
            case space + ["objects", objectID, "editor", "editor_blocks", "markdown"] where !limited:
                value = .object(["content": .string(text), "version": .string(version)])
            case space + ["bundles", "pinkha/torah-native/v1"] where !limited:
                value = .object(["bundle": .object(["derived": .bool(true), "losers": .array([]), "rootId": .string(rootID)])])
            case space + ["pinkha", "objects", objectID, "claims"] where limited:
                value = claimsSnapshot
            case space + ["pinkha", "targets", objectID] where limited:
                completedPropertiesByPhase[phase] += 1
                value = derivedProperties
            case space + ["pinkha", "objects", objectID, "claims", "subscribe"] where limited:
                holdObservation(connection, kind: "claims"); return
            default:
                throw MountedRefreshFixtureFailure.invalid("unexpected GET route")
            }
        } else if method == "POST", !limited {
            let query = try JSONDecoder().decode(AnyJSON.self, from: body)
            let expected: AnyJSON = .object(["objectId": .string(objectID), "dataset": .string("editor_blocks"),
                "limit": .integer(10_001), "includeTotal": .bool(true),
                "sort": .array(parts == space + ["query"] ? [.string("nav.pos"), .string("id")] : [.string("id")])])
            guard query == expected else { throw MountedRefreshFixtureFailure.invalid("unexpected read query body") }
            if parts == space + ["query", "subscribe"] {
                holdObservation(connection, kind: "editor"); return
            }
            guard parts == space + ["query"] else { throw MountedRefreshFixtureFailure.invalid("unexpected POST route") }
            readsByPhase[phase] += 1
            value = .object(["records": .array([.object([
                "id": .string(blockID), "type": .string("paragraph"), "text": .string(text), "style": .object([:]),
                "nav": .object(["parentId": .string(""), "pos": .string("A")]),
                "_ver": .object(["id": .string("render-block-create"), "text": .string(version)])])]),
                "total": .integer(1), "hasNext": .bool(false)])
        } else { throw MountedRefreshFixtureFailure.invalid("unexpected mutation method") }
        let bytes = try JSONEncoder().encode(value)
        guard bytes.count <= 16_384 else { throw MountedRefreshFixtureFailure.invalid("response byte budget") }
        let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: \(bytes.count)\r\nConnection: close\r\n\r\n"
        var response = Data(header.utf8); response.append(bytes)
        connection.send(content: response, contentContext: .finalMessage, isComplete: true,
                        completion: .contentProcessed { [weak self] error in
            if let error, let self, !self.draining { self.fail("response send failed: \(error)") }
            connection.cancel()
        })
    }

    private func holdObservation(_ connection: NWConnection, kind: String) {
        guard heldKinds.insert(kind).inserted else {
            fail("duplicate observation subscription"); connection.cancel(); return
        }
        let navigationConnectionID = navigationEnabled
            ? connections.first(where: { $0.value === connection })?.key : nil
        if let navigationConnectionID { navigationObservationIDs[navigationConnectionID] = kind }
        let response = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n: controlled fixture held\n\n"
        connection.send(content: Data(response.utf8), completion: .contentProcessed { [weak self] error in
            guard let self else { connection.cancel(); return }
            if let error {
                if !self.draining { self.fail("observation send failed: \(error)") }
                connection.cancel(); return
            }
            connection.receive(minimumIncompleteLength: 1, maximumLength: 1) { [weak self] data, _, _, error in
                if let self, !self.draining,
                   !(navigationConnectionID.map { self.navigationAllowedClosure.contains($0) } ?? false) {
                    self.fail("held observation ended before owner drainage: bytes=\(data?.count ?? 0), error=\(String(describing: error))")
                }
                connection.cancel()
            }
        })
    }

    private var readiness: AnyJSON {
        .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                 "generation": .string(String(repeating: "a", count: 64))])
    }

    private var targetProof: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "policy": .string("canonical-editor-module-v1"), "spaceId": .string(spaceID),
            "typeId": .string("page"), "objectId": .string(objectID), "eligible": .bool(true),
            "canWrite": .bool(!navigationEnabled), "collections": .array([]),
            "canonicalEditorDataset": .string("editor_blocks"), "readiness": readiness])
    }

    private var claimsSnapshot: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "scope": .string("object-logical-closure"), "targetObjectId": .string(objectID),
            "reachableClaimBlockIds": .array([]), "spaceId": .string(spaceID), "rootObjectId": .string(rootID),
            "dataset": .string("pinkha_torah_claims_v1"), "complete": .bool(true), "limit": .integer(10_000),
            "records": .array([]), "readiness": readiness])
    }

    private var derivedProperties: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "target": .object(["objectId": .string(objectID)]),
            "semantic": .object(["version": .integer(1), "coverage": .string("complete"),
                "inputSHA256": .string(String(repeating: "b", count: 64)), "labels": .object([:]),
                "records": .array([]), "sources": .array([]), "topics": .array([]), "words": .array([])]),
            "readiness": readiness])
    }

    private var capabilities: AnyJSON {
        var value: [String: AnyJSON] = [
            "contract": .string("pinkha-torah-native-v1"), "bundleId": .string("pinkha/torah-native/v1"),
            "module": .string("pinkha_torah_native"), "dataset": .string("pinkha_torah_claims_v1"),
            "dataVersion": .string("pinkha-torah-native-claims-v1"),
            "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "associationBlockDataset": .string("editor_blocks"), "documentTypePolicy": .string("canonical-editor-module-v1"),
            "propertyPresentationCollection": .string("pinkha_presentation_v1"),
            "propertyPresentationHiddenProperty": .string("hiddenProperties"), "allowedTargetTypes": .array([.string("page")]),
            "nativeClaimsMaxRecords": .integer(10_000), "nativeClaimsMaxBytes": .integer(16_777_216),
            "mobileManagedTokenGateway": .integer(0)]
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain", "currentACLCommitFence", "targetTreeCommitFence",
                    "nativeDocumentProperties", "nativeIndexedSourceQuery", "nativeRelatedVersion", "conditionalBlockPatch",
                    "conditionalPropertiesSet", "conditionalPropertiesApplySeq", "conditionalPropertiesNoop",
                    "conditionalBlockCurrentWriterFence", "currentWriterObjectCreate", "currentWriterBlockCreate",
                    "nativeClaimsSnapshot", "nativeClaimsWatch", "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch",
                    "nativeDocumentTypePolicy", "nativeDocumentMembership", "conditionalMembershipSet", "nativePropertyPresentation"] {
            value[key] = .integer(1)
        }
        return .object(value)
    }
}
#endif

#if canImport(UIKit) && canImport(Network)
private extension MountedRefreshHTTPFixture {
    var navigationWriteCount: Int { queue.sync { navigationApplied.count } }
    var navigationReadbacks: Int { queue.sync { navigationReadbackWrites.count } }
    var isNavigationDefinitionHeld: Bool { queue.sync { heldNavigationDefinition != nil } }

    func permitNavigationOwnerRetirement() {
        queue.sync {
            navigationAllowedClosure.formUnion(navigationObservationIDs.keys)
            if let pending = heldNavigationDefinition { navigationAllowedClosure.insert(pending.id) }
            navigationEvents.append("owner-retired")
        }
    }

    func recordNavigationGateRelease() {
        queue.sync { navigationEvents.append("post-ack-gate-released") }
    }

    func advanceNavigationSourceAfterSuspendedDelivery() throws {
        try queue.sync {
            guard navigationEnabled, phase == 0, readsByPhase[0] > 0, failures.isEmpty else {
                throw MountedRefreshFixtureFailure.invalid("no original read to advance after delivery suspension")
            }
            phase = 1
        }
    }

    func releaseNavigationDefinition() throws {
        try queue.sync {
            guard let pending = heldNavigationDefinition else { return }
            heldNavigationDefinition = nil
            guard connections[pending.id] != nil else {
                navigationEvents.append("definition-cancelled-before-release")
                return
            }
            navigationEvents.append("definition-released")
            try sendNavigationResponse(pending.connection, id: pending.id,
                                       value: navigationDefinition, acknowledged: false)
        }
    }

    func requireNavigationEffects(expected: Int, requireDrainBeforeSecond: Bool = false) throws {
        try queue.sync {
            let latest = Int64(Date().timeIntervalSince1970.rounded(.down)) * 1000
            guard navigationEnabled, failures.isEmpty, navigationApplied.count == expected,
                  navigationApplied.allSatisfy({ value in
                      value % 1000 == 0 && value >= navigationEarliestSecond * 1000 && value <= latest
                  }), requests <= requestLimit else {
                throw MountedRefreshFixtureFailure.invalid("controlled local-open effect mismatch")
            }
            if requireDrainBeforeSecond {
                guard let release = navigationEvents.firstIndex(of: "post-ack-gate-released"),
                      let second = navigationEvents.firstIndex(of: "write-2"), release < second else {
                    throw MountedRefreshFixtureFailure.invalid("new open preceded old post-ACK release")
                }
            }
        }
    }

    var navigationDefinition: AnyJSON {
        .object(["properties": .array([.object([
            "id": .string("pinkhaLastOpenedV1"), "kind": .string("datetime"), "scope": .string("local"),
            "xFormat": .object(["type": .string("datetime"),
                "contract": .string("pinkha-last-opened-local-v1"), "precision": .string("seconds")])
        ])])])
    }

    /// This is only the exact new d1 read/local-property surface needed by the
    /// consumer. The ordinary editor routes and finite transport remain shared.
    func routeNavigation(_ connection: NWConnection, method: String, parts: [String],
                         body: Data, headers: [String: String], limited: Bool) throws -> Bool {
        guard navigationEnabled, !limited else { return false }
        let space = ["v1", "spaces", spaceID]
        let value: AnyJSON
        let acknowledged: Bool
        guard let id = connections.first(where: { $0.value === connection })?.key else {
            throw MountedRefreshFixtureFailure.invalid("navigation response lost its owned connection")
        }
        if method == "GET", parts == ["v1", "auth", "engine-binding"] {
            guard body.isEmpty else { throw MountedRefreshFixtureFailure.invalid("binding GET body") }
            value = .object(["contract": .string("pinkha-any-http-engine-binding-v1"),
                "accountId": .string(accountID), "networkId": .string(navigationNetworkID),
                "runId": .string(navigationRunID)])
            acknowledged = false
        } else if method == "GET", parts == space + ["types", "any", "properties"] {
            guard body.isEmpty else { throw MountedRefreshFixtureFailure.invalid("definition GET body") }
            if holdFirstNavigationDefinition {
                holdFirstNavigationDefinition = false
                guard heldNavigationDefinition == nil else {
                    throw MountedRefreshFixtureFailure.invalid("duplicate held definition")
                }
                heldNavigationDefinition = (id, connection)
                navigationEvents.append("definition-held")
                return true
            }
            value = navigationDefinition
            acknowledged = false
        } else if method == "POST",
                  parts == ["v1", "pinkha", "bound", "spaces", spaceID, "properties", objectID, "set", "any"] {
            guard headers["x-any-expected-account-id"] == accountID,
                  headers["x-any-expected-run-id"] == navigationRunID else {
                throw MountedRefreshFixtureFailure.invalid("unbound local navigation mutation")
            }
            let input = try JSONDecoder().decode(AnyJSON.self, from: body)
            guard let fields = input.object, Set(fields.keys) == ["patch"],
                  let patch = input["patch"]?.object, Set(patch.keys) == ["pinkhaLastOpenedV1"],
                  let date = input["patch"]?["pinkhaLastOpenedV1"]?.object, Set(date.keys) == ["$date"],
                  let milliseconds = input["patch"]?["pinkhaLastOpenedV1"]?["$date"]?.integer,
                  (0...253_402_300_799_000).contains(milliseconds), milliseconds % 1000 == 0,
                  navigationApplied.count < 2 else {
                throw MountedRefreshFixtureFailure.invalid("unexpected local navigation patch")
            }
            navigationApplied.append(milliseconds)
            navigationLastOpened = .object(["$date": .integer(milliseconds)])
            navigationEvents.append("write-" + String(navigationApplied.count))
            value = .object(["versionId": .string("local:" + String(navigationApplied.count)),
                             "changeId": .string(""), "recordIds": .array([.string(objectID)])])
            acknowledged = true
        } else {
            return false
        }
        try sendNavigationResponse(connection, id: id, value: value, acknowledged: acknowledged)
        return true
    }

    func sendNavigationResponse(_ connection: NWConnection, id: UUID,
                                value: AnyJSON, acknowledged: Bool) throws {
        let bytes = try JSONEncoder().encode(value)
        guard bytes.count <= 16_384 else { throw MountedRefreshFixtureFailure.invalid("navigation response bound") }
        var header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: \(bytes.count)\r\nConnection: close\r\n"
        if acknowledged {
            header += "X-Any-Binding-Contract: pinkha-any-http-engine-binding-v1\r\n"
            header += "X-Any-Bound-Account-Id: \(accountID)\r\n"
            header += "X-Any-Bound-Run-Id: \(navigationRunID)\r\n"
        }
        header += "\r\n"
        var response = Data(header.utf8); response.append(bytes)
        connection.send(content: response, contentContext: .finalMessage, isComplete: true,
                        completion: .contentProcessed { [weak self] error in
            if let error, let self, !self.draining, !self.navigationAllowedClosure.contains(id) {
                self.fail("navigation response send failed: \(error)")
            }
            connection.cancel()
        })
    }
}
#endif

#if canImport(UIKit) && canImport(Network)

// Navigation consumer coverage uses the same real loopback transport and
// controller as the renderer cases. It does not launch a Native engine.
@MainActor
private final class MountedNavigationContainer: UIViewController {
    let editor: AnyNativeEditorController

    init(editor: AnyNativeEditorController) {
        self.editor = editor
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("test-only programmatic container") }

    override var shouldAutomaticallyForwardAppearanceMethods: Bool { false }

    override func viewDidLoad() {
        super.viewDidLoad()
        addChild(editor)
        editor.loadViewIfNeeded()
        editor.didMove(toParent: self)
    }

    func attachEditor() {
        editor.view.frame = view.bounds
        editor.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(editor.view)
        view.layoutIfNeeded()
        editor.view.layoutIfNeeded()
    }

    func detachEditor() { editor.view.removeFromSuperview() }
}

private enum MountedNavigationTaskContext {
    @TaskLocal static var personalOpenOwnerID: UUID? = nil
}

/// A finite, deliberately noncooperative pause after a real completed read.
/// Every owner releases it during cleanup; cancellation alone cannot pretend
/// that the operation has drained.
private final class MountedNavigationGate: @unchecked Sendable {
    private let lock = NSLock()
    private var target: Int?
    private var held = false
    private var reject = false
    private var waiter: CheckedContinuation<Void, any Error>?
    private var enteredOwners: Set<UUID> = []
    private var observedOwner: UUID?
    private var entryObservation: AsyncStream<Bool>.Continuation?

    var isHeld: Bool { lock.lock(); defer { lock.unlock() }; return held }

    func arm(after event: Int) throws {
        lock.lock(); defer { lock.unlock() }
        guard target == nil, !held, !reject else {
            throw MountedRefreshFixtureFailure.invalid("navigation gate already owned")
        }
        target = event
    }

    func pass(after event: Int) async throws {
        try await withCheckedThrowingContinuation { continuation in
            lock.lock()
            if reject {
                lock.unlock()
                continuation.resume(throwing: MountedRefreshFixtureFailure.invalid("controlled post-ACK lease read failure"))
            } else if target == event {
                target = nil; held = true; waiter = continuation
                lock.unlock()
            } else {
                lock.unlock()
                continuation.resume()
            }
        }
    }

    func recordEntry(for owner: UUID) throws {
        lock.lock()
        guard enteredOwners.contains(owner) || enteredOwners.count < 4 else {
            lock.unlock()
            throw MountedRefreshFixtureFailure.invalid("navigation owner observation bound")
        }
        enteredOwners.insert(owner)
        let observation = observedOwner == owner ? entryObservation : nil
        lock.unlock()
        observation?.yield(true)
    }

    func hasEntered(_ owner: UUID) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return enteredOwners.contains(owner)
    }

    func beginEntryObservation(for owner: UUID) throws -> AsyncStream<Bool> {
        let pair = AsyncStream<Bool>.makeStream(bufferingPolicy: .bufferingNewest(1))
        lock.lock()
        guard observedOwner == nil, entryObservation == nil else {
            lock.unlock()
            pair.continuation.finish()
            throw MountedRefreshFixtureFailure.invalid("duplicate navigation entry observation")
        }
        observedOwner = owner; entryObservation = pair.continuation
        let alreadyEntered = enteredOwners.contains(owner)
        lock.unlock()
        if alreadyEntered { pair.continuation.yield(true) }
        return pair.stream
    }

    @discardableResult
    func finishEntryObservation(for owner: UUID) -> Bool {
        lock.lock()
        let entered = enteredOwners.contains(owner)
        let continuation = observedOwner == owner ? entryObservation : nil
        if observedOwner == owner { observedOwner = nil; entryObservation = nil }
        lock.unlock()
        continuation?.finish()
        return entered
    }

    func release(rejectFurtherReads: Bool = false) {
        lock.lock()
        let pending = waiter
        let observation = entryObservation
        waiter = nil; held = false; target = nil; reject = rejectFurtherReads
        observedOwner = nil; entryObservation = nil
        lock.unlock()
        observation?.finish()
        if rejectFurtherReads {
            pending?.resume(throwing: MountedRefreshFixtureFailure.invalid("controlled post-ACK lease read failure"))
        } else {
            pending?.resume()
        }
    }
}

@MainActor
private final class MountedNavigationContext {
    let fixture: MountedRefreshHTTPFixture
    let lifetime: AnyUIPresentationLifetime
    let session: AnyApplicationSession
    let presentation: AnyDocumentPresentation
    let controller: AnyNativeEditorController
    let container: MountedNavigationContainer
    let window: UIWindow
    let runGate: MountedNavigationGate
    let readGate = MountedNavigationGate()
    let journal: MountedRefreshUnusedJournal
    var explicitLoads: [Task<Void, Never>] = []

    init(fixture: MountedRefreshHTTPFixture, lifetime: AnyUIPresentationLifetime,
         session: AnyApplicationSession, presentation: AnyDocumentPresentation,
         controller: AnyNativeEditorController, container: MountedNavigationContainer,
         window: UIWindow, runGate: MountedNavigationGate, journal: MountedRefreshUnusedJournal) {
        self.fixture = fixture; self.lifetime = lifetime; self.session = session
        self.presentation = presentation; self.controller = controller
        self.container = container; self.window = window
        self.runGate = runGate; self.journal = journal
    }

    func mountUnattachedEditor() {
        container.detachEditor()
        presentation.mount(surface: controller)
    }

    func activateOpen() {
        container.attachEditor()
        // Only the original actual-open Task created inside this synchronous
        // public hook inherits the marker; setup/read/cleanup are outside it.
        MountedNavigationTaskContext.$personalOpenOwnerID.withValue(presentation.mountedOwnerID) {
            presentation.didBecomeActive()
        }
    }

    func retireMountedEditor() {
        fixture.permitNavigationOwnerRetirement()
        presentation.unmount()
        container.detachEditor()
    }
}

extension AnyNativeTextRendererTests {
    /// The container suppresses appearance forwarding so automatic
    /// viewDidAppear/load cannot hide a missing didBecomeActive consumer hook.
    /// The tested predicate still comes from the actual controller/window/scene.
    func testPersonalOpenWaitsForForegroundAndRecordsOncePerMount() async throws {
        try await withMountedNavigation { context in
            let model = context.presentation, fixture = context.fixture
            model.mount(surface: context.controller)
            let firstOwner = model.mountedOwnerID
            XCTAssertFalse(context.controller.isForegroundMounted)
            await model.load()
            try await self.requireNavigationRead(context, expected: "XbeforeY")
            XCTAssertEqual(fixture.navigationWriteCount, 0)
            XCTAssertNil(model.message)
            model.didBecomeActive()
            XCTAssertEqual(fixture.navigationWriteCount, 0, "An inactive surface must not manufacture an open")

            context.activateOpen()
            XCTAssertTrue(context.controller.isForegroundMounted)
            XCTAssertEqual(model.mountedOwnerID, firstOwner)
            try await self.waitForMountedRefresh(fixture) {
                fixture.navigationWriteCount == 1 && fixture.navigationReadbacks >= 1
            }
            model.didBecomeActive()
            try fixture.advanceSource()
            await model.load()
            try await self.requireNavigationRead(context, expected: "XafterY")
            model.didBecomeActive()
            XCTAssertEqual(model.mountedOwnerID, firstOwner)

            context.retireMountedEditor()
            await model.drain()
            try await self.waitForMountedRefresh(fixture) { fixture.heldObservationKinds.isEmpty }
            XCTAssertEqual(fixture.navigationWriteCount, 1, "Refresh/activation must not rearm this mount")

            context.mountUnattachedEditor()
            let secondOwner = model.mountedOwnerID
            XCTAssertNotEqual(secondOwner, firstOwner)
            await model.load()
            try await self.requireNavigationRead(context, expected: "XafterY")
            context.activateOpen()
            try await self.waitForMountedRefresh(fixture) {
                fixture.navigationWriteCount == 2 && fixture.navigationReadbacks >= 2
            }
            context.retireMountedEditor()
            await model.drain()
            XCTAssertEqual(fixture.navigationWriteCount, 2, "Exactly one local update per accepted mounted open")
            try fixture.requireNavigationEffects(expected: 2)
        }
    }

    func testPersonalOpenRejectsRetiredReadAndCancellationBeforeDispatch() async throws {
        try await withMountedNavigation(holdFirstDefinition: true) { context in
            let model = context.presentation, fixture = context.fixture
            let delivery = context.readGate
            try delivery.arm(after: 0)
            model.editorReadOperation = { _, documents, objectID, lease in
                let original = try await documents.read(objectID: objectID, lease: lease)
                try await delivery.pass(after: 0)
                return original
            }
            model.mount(surface: context.controller)
            let retiredOwner = model.mountedOwnerID
            let originalLoad = Task { await model.load() }
            context.explicitLoads.append(originalLoad)
            try await self.waitForMountedRefresh(fixture) { delivery.isHeld }
            XCTAssertNil(model.read)
            XCTAssertEqual(fixture.navigationWriteCount, 0)

            // The old completed HTTP read is held at the existing delivery seam.
            // A new real mount accepts a newer read before that old value returns.
            context.retireMountedEditor()
            try fixture.advanceNavigationSourceAfterSuspendedDelivery()
            context.mountUnattachedEditor()
            let currentOwner = model.mountedOwnerID
            XCTAssertNotEqual(currentOwner, retiredOwner)
            await model.load()
            try await self.requireNavigationRead(context, expected: "XafterY")
            context.activateOpen()
            try await self.waitForMountedRefresh(fixture) { fixture.isNavigationDefinitionHeld }
            delivery.release()
            await originalLoad.value
            try await self.requireNavigationRead(context, expected: "XafterY")
            XCTAssertEqual(model.mountedOwnerID, currentOwner)
            XCTAssertEqual(fixture.navigationWriteCount, 0)

            // Cancel the actual new observation after preparation entered its
            // definition read but before its original bound mutation dispatch.
            context.retireMountedEditor()
            try fixture.releaseNavigationDefinition()
            await model.drain()
            try await self.waitForMountedRefresh(fixture) { fixture.heldObservationKinds.isEmpty }
            XCTAssertEqual(fixture.navigationWriteCount, 0, "No retired/cancelled owner may dispatch")

            context.mountUnattachedEditor()
            await model.load()
            try await self.requireNavigationRead(context, expected: "XafterY")
            context.activateOpen()
            try await self.waitForMountedRefresh(fixture) {
                fixture.navigationWriteCount == 1 && fixture.navigationReadbacks >= 1
            }
            context.retireMountedEditor()
            await model.drain()
            try fixture.requireNavigationEffects(expected: 1)
        }
    }

    func testPersonalOpenRetainsLateAcknowledgmentAndDrainsBeforeReopen() async throws {
        // First controlled flow: the actual native-shaped success has already
        // reached the store before both its readback and outer lease fail.
        try await withMountedNavigation(holdFirstDefinition: true) { context in
            let model = context.presentation, fixture = context.fixture
            context.mountUnattachedEditor()
            await model.load()
            try await self.requireNavigationRead(context, expected: "XbeforeY")
            context.activateOpen()
            try await self.waitForMountedRefresh(fixture) { fixture.isNavigationDefinitionHeld }
            try context.runGate.arm(after: 1)
            try fixture.releaseNavigationDefinition()
            try await self.waitForMountedRefresh(fixture) { context.runGate.isHeld }
            XCTAssertEqual(fixture.navigationWriteCount, 1)
            context.runGate.release(rejectFurtherReads: true)
            let acceptedWarning = AnyUIErrorText.text(
                "תאריך הפתיחה עודכן, אך לא ניתן לבדוק את הערך הנוכחי.",
                "The last-opened date was updated, but the current value could not be checked.")
            try await self.waitForMountedRefresh(fixture) { model.message == acceptedWarning }
            XCTAssertFalse(model.canWrite)
            XCTAssertFalse(model.hasPendingEdits)
            XCTAssertEqual(model.read?.snapshot.objectID, fixture.objectID)
            context.runGate.release()
            await model.load()
            XCTAssertEqual(model.message, acceptedWarning, "No automatic resend or invented success")
            context.retireMountedEditor()
            await model.drain()
            try fixture.requireNavigationEffects(expected: 1)
        }

        // Second controlled flow: the old operation deliberately ignores task
        // cancellation at its real post-ACK run check. The new owner may read,
        // but its local mutation must follow the original task's drainage.
        try await withMountedNavigation(holdFirstDefinition: true) { context in
            let model = context.presentation, fixture = context.fixture
            context.mountUnattachedEditor()
            await model.load()
            try await self.requireNavigationRead(context, expected: "XbeforeY")
            context.activateOpen()
            try await self.waitForMountedRefresh(fixture) { fixture.isNavigationDefinitionHeld }
            let oldOwner = model.mountedOwnerID
            try context.runGate.arm(after: 1)
            try fixture.releaseNavigationDefinition()
            try await self.waitForMountedRefresh(fixture) { context.runGate.isHeld }
            context.retireMountedEditor()
            try await self.waitForMountedRefresh(fixture) { fixture.heldObservationKinds.isEmpty }
            context.mountUnattachedEditor()
            XCTAssertNotEqual(model.mountedOwnerID, oldOwner)
            await model.load()
            try await self.requireNavigationRead(context, expected: "XbeforeY")
            let successorOwner = model.mountedOwnerID
            let prematureEntry = try context.runGate.beginEntryObservation(for: successorOwner)
            context.activateOpen()
            let enteredBeforeDrain = try await self.observePrematureNavigationEntry(
                prematureEntry, gate: context.runGate, owner: successorOwner)
            XCTAssertFalse(enteredBeforeDrain, "The new actual-open task entered its lease before its predecessor drained")
            XCTAssertFalse(context.runGate.hasEntered(successorOwner))
            XCTAssertTrue(context.runGate.isHeld)
            XCTAssertEqual(fixture.navigationWriteCount, 1)
            fixture.recordNavigationGateRelease()
            context.runGate.release()
            try await self.waitForMountedRefresh(fixture) {
                fixture.navigationWriteCount == 2 && fixture.navigationReadbacks >= 1
            }
            XCTAssertTrue(context.runGate.hasEntered(successorOwner))
            XCTAssertNil(model.message, "A retired completion must not publish over the current owner")
            context.retireMountedEditor()
            await model.drain()
            try fixture.requireNavigationEffects(expected: 2, requireDrainBeforeSecond: true)
        }
    }

    @MainActor
    private func observePrematureNavigationEntry(
        _ stream: AsyncStream<Bool>, gate: MountedNavigationGate, owner: UUID
    ) async throws -> Bool {
        defer { gate.finishEntryObservation(for: owner) }
        try Task.checkCancellation()
        let observed = await withTaskGroup(of: Bool.self) { group in
            defer {
                gate.finishEntryObservation(for: owner)
                group.cancelAll()
            }
            group.addTask {
                var iterator = stream.makeAsyncIterator()
                return await iterator.next() ?? false
            }
            group.addTask {
                do { try await Task.sleep(for: .seconds(1)) }
                catch { return false }
                return false
            }
            return await group.next() ?? false
        }
        try Task.checkCancellation()
        // The ledger also catches an entry racing registration or the deadline.
        return observed || gate.hasEntered(owner)
    }

    @MainActor
    private func withMountedNavigation(
        holdFirstDefinition: Bool = false,
        _ body: @MainActor (MountedNavigationContext) async throws -> Void
    ) async throws {
        let fixture = try MountedRefreshHTTPFixture(before: "XbeforeY", after: "XafterY",
            navigationEnabled: true, holdFirstNavigationDefinition: holdFirstDefinition)
        let lifetime = AnyUIPresentationLifetime()
        let runGate = MountedNavigationGate()
        var context: MountedNavigationContext?
        var session: AnyApplicationSession?
        var window: UIWindow?
        var previousKey: UIWindow?
        var firstFailure: (any Error)?
        do {
            let baseURL = try await fixture.start()
            let workspace = try AnyTorahWorkspace(accountID: fixture.accountID, spaceID: fixture.spaceID)
            let client = try AnyHTTPClient(baseURL: baseURL, expectedAccountID: workspace.accountID)
            let readRun: @Sendable () async throws -> String = {
                let actualOpenOwnerID = MountedNavigationTaskContext.personalOpenOwnerID
                if let actualOpenOwnerID { try runGate.recordEntry(for: actualOpenOwnerID) }
                let health = try await client.requestJSON(method: "GET", path: ["v1", "health"])
                guard health["status"]?.string == "ok",
                      health["account"]?.string == workspace.accountID,
                      let started = health["startedAt"]?.string, !started.isEmpty else {
                    throw AnyHostError.engineRestarted
                }
                // Original internal session injection, already used by this
                // target. The run is still read through the real HTTP client.
                if actualOpenOwnerID != nil {
                    try await runGate.pass(after: fixture.navigationWriteCount)
                }
                return started
            }
            let started = try await readRun()
            let activeSession = AnyApplicationSession(workspace: workspace,
                engineStartedAt: started, verifyRun: readRun)
            session = activeSession
            let capabilities = try await AnyUIFoundationCapabilities.verify(client: client, session: activeSession)
            let marker = try await AnyNativeNoteMarker.verify(client: client, workspace: workspace,
                                                               collectionID: fixture.notesID)
            let journal = MountedRefreshUnusedJournal(workspace: workspace)
            let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace,
                journal: journal, allowedTypeIDs: ["page"])
            let binding = try await client.nativeAccountRunBinding(expectedNetworkID: fixture.navigationNetworkID)
            let navigation = try AnyNativePersonalNavigationStore(client: client, workspace: workspace, binding: binding)
            let model = try AnyDocumentPresentation(client: client, session: activeSession,
                objects: objects, blocks: blocks, capabilities: capabilities,
                operations: AnyGuardedTorahOperationStore(client: client, workspace: workspace),
                noteMarker: marker, objectID: fixture.objectID, lifetime: lifetime,
                recovery: AnyNativeLibraryRecovery(workspace: workspace), personalNavigation: navigation)
            let controller = AnyNativeEditorController(presentation: model)
            let container = MountedNavigationContainer(editor: controller)
            let scene = try XCTUnwrap(UIApplication.shared.connectedScenes
                .compactMap { $0 as? UIWindowScene }.first { $0.activationState == .foregroundActive })
            previousKey = scene.windows.first(where: \.isKeyWindow)
            let mountedWindow = UIWindow(windowScene: scene)
            mountedWindow.frame = scene.coordinateSpace.bounds
            mountedWindow.rootViewController = container
            window = mountedWindow
            mountedWindow.makeKeyAndVisible()
            container.loadViewIfNeeded()
            let owned = MountedNavigationContext(fixture: fixture, lifetime: lifetime,
                session: activeSession, presentation: model, controller: controller,
                container: container, window: mountedWindow, runGate: runGate, journal: journal)
            context = owned
            try await body(owned)
            let journalCalls = await journal.calls
            XCTAssertEqual(journalCalls, 0, "Personal READ navigation must never enter object creation")
        } catch { firstFailure = error }

        // Retire first, release deliberate noncooperative reads, then join all
        // explicit loads and the actual original presentation/session work.
        fixture.beginDrain()
        lifetime.revoke()
        context?.explicitLoads.forEach { $0.cancel() }
        context?.readGate.release()
        runGate.release()
        do { try fixture.releaseNavigationDefinition() }
        catch {
            if firstFailure == nil { firstFailure = error }
            else { XCTFail("Additional controlled definition release failure: \(error)") }
        }
        if let context {
            for load in context.explicitLoads { await load.value }
        }
        await lifetime.drain()
        await session?.revokeAndDrain()
        do { try await fixture.stop() }
        catch {
            if firstFailure == nil { firstFailure = error }
            else { XCTFail("Additional owned navigation loopback cleanup failure: \(error)") }
        }
        do {
            let attachment = XCTAttachment(data: try fixture.retainedTrace(), uniformTypeIdentifier: "public.json")
            attachment.name = "mounted-navigation-controlled-http"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            if firstFailure == nil { firstFailure = error }
            else { XCTFail("Additional navigation trace retention failure: \(error)") }
        }
        window?.endEditing(true)
        window?.isHidden = true
        window?.rootViewController = nil
        previousKey?.makeKeyAndVisible()
        if let firstFailure { throw firstFailure }
    }

    @MainActor
    private func requireNavigationRead(_ context: MountedNavigationContext, expected: String) async throws {
        try await waitForMountedRefresh(context.fixture) {
            !context.presentation.isLoading && context.fixture.heldObservationKinds == ["editor", "claims"]
        }
        try context.fixture.requireHealthy()
        let model = context.presentation
        XCTAssertFalse(model.isLoading)
        XCTAssertTrue(model.isMounted)
        XCTAssertFalse(model.canWrite, "The controlled current member is Reader")
        XCTAssertFalse(model.canMutate, "No shared-content write authority is manufactured")
        XCTAssertFalse(model.hasPendingEdits)
        XCTAssertNil(model.torah.message)
        let read = try XCTUnwrap(model.read)
        XCTAssertEqual(read.snapshot.objectID, context.fixture.objectID)
        XCTAssertEqual(read.snapshot.spaceID, context.fixture.spaceID)
        let block = try XCTUnwrap(read.snapshot.blocks.first)
        XCTAssertEqual(read.snapshot.blocks.count, 1)
        XCTAssertEqual(block.id, context.fixture.blockID)
        XCTAssertEqual(Array(block.text.utf8), Array(expected.utf8))
        XCTAssertEqual(Array(model.source(for: block).utf8), Array(expected.utf8))
        XCTAssertEqual(model.nativeProperties?.readiness.complete, true)
        context.controller.render()
        if context.controller.isForegroundMounted {
            try await waitForMountedRefresh(context.fixture) {
                context.controller.view.layoutIfNeeded()
                return Self.refreshTable(context.controller.view)?.visibleCells.count == 1
            }
            let table = try XCTUnwrap(Self.refreshTable(context.controller.view))
            let cell = try XCTUnwrap(table.visibleCells.first)
            let input = try XCTUnwrap(Self.refreshInput(cell, blockID: context.fixture.blockID))
            XCTAssertTrue(input.window === context.window)
            XCTAssertEqual(Array(input.text.utf8), Array(expected.utf8))
            XCTAssertEqual(Array(input.text.utf16), Array(expected.utf16))
        }
    }
}
#endif


#if canImport(UIKit) && canImport(Network)
import Network
import PinkhaAnyEngine
import PinkhaAnyHost
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
        let previousKey = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows).first(where: \.isKeyWindow)
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

    init(before: String, after: String) throws {
        self.before = before; self.after = after
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        listener = try NWListener(using: parameters, on: .any)
        // Network decrements this cumulative acceptance allowance for every
        // connection. The independent tracked simultaneous-connection cap is16.
        listener.newConnectionLimit = 512
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
                  heldKinds == ["editor", "claims"], requests <= 512 else {
                throw MountedRefreshFixtureFailure.invalid("incomplete controlled load closure: " + failures.joined(separator: "; "))
            }
        }
    }

    func beginDrain() { queue.sync { draining = true } }

    func retainedTrace() throws -> Data {
        try queue.sync {
            let value: [String: Any] = [
                "scope": "controlled-loopback-hosted-UIKit-not-Native-acceptance",
                "requests": requestTrace, "failures": failures,
                "queriesBySourcePhase": readsByPhase, "propertiesBySourcePhase": completedPropertiesByPhase,
                "heldObservationKinds": heldKinds.sorted(), "listenerCancelled": listenerClosed,
                "remainingOwnedConnections": connections.count]
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
                if !self.draining { self.fail("connection failed: \(error)") }
                connection.cancel()
            case .cancelled:
                self.connections.removeValue(forKey: id)
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
                try self.route(connection, method: String(request[0]), target: String(request[1]), body: Data(body))
            } catch {
                self.fail("request rejected: \(error)"); connection.cancel()
            }
        }
    }

    private func route(_ connection: NWConnection, method: String, target: String, body: Data) throws {
        requests += 1
        guard !stopping, requests <= 512, target.hasPrefix("/"),
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
                value = .object(["identity": .string(accountID), "status": .string("active"), "permission": .string("owner")])
            case space + ["collections", notesID] where !limited:
                value = .object(["id": .string(notesID), "xKey": .string("pinkha-note-v1")])
            case space + ["pinkha", "document-targets", objectID] where !limited:
                value = targetProof
            case space + ["objects", objectID] where !limited:
                value = .object(["objectId": .string(objectID), "record": .object([
                    "id": .string(objectID), "spaceId": .string(spaceID),
                    "any": .object(["name": .string("Mounted refresh fixture"), "type": .string("page"), "collections": .array([])])])])
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
        let response = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n: controlled fixture held\n\n"
        connection.send(content: Data(response.utf8), completion: .contentProcessed { [weak self] error in
            guard let self else { connection.cancel(); return }
            if let error {
                if !self.draining { self.fail("observation send failed: \(error)") }
                connection.cancel(); return
            }
            connection.receive(minimumIncompleteLength: 1, maximumLength: 1) { [weak self] data, _, _, error in
                if let self, !self.draining {
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
            "canWrite": .bool(true), "collections": .array([]),
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

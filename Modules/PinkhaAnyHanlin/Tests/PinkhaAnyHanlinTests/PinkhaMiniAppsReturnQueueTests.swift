import Foundation
import Testing
import PinkhaHanlinCore

@Suite("MiniApps return navigation identity")
@MainActor
struct PinkhaMiniAppsReturnQueueTests {
    private func target(_ id: UUID = UUID(), engine: String = "heart",
                        account: String = "account-a", space: String = "space-a",
                        document: String = "document-a", scene: String? = "scene-a")
        -> PinkhaMiniAppsReturnQueue.Target {
        .init(requestID: id, engineID: engine, accountID: account,
              spaceID: space, documentID: document, sceneID: scene)
    }

    @Test func coldReturnWaitsForSelectedAccountAndHomeReadiness() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target()
        #expect(queue.retain(callback))
        #expect(queue.nextNavigation(engineID: "heart", accountID: "", ready: true) == nil)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: false) == nil)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-b", ready: true) == nil)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == callback)
    }

    @Test func engineHoldKeepsCallbackUntilOriginalEngineResumes() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target()
        queue.retain(callback)
        #expect(queue.nextNavigation(engineID: "any", accountID: "account-a", ready: true) == nil)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: false) == nil)
        queue.suspendNavigation()
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == callback)
    }

    @Test func duplicateCallbackCannotReplaceIdentityOrDispatchTwice() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target()
        #expect(queue.retain(callback))
        #expect(queue.retain(callback))
        #expect(!queue.retain(target(callback.requestID, account: "account-b")))
        #expect(!queue.retain(target(callback.requestID, space: "space-b")))
        #expect(!queue.retain(target(callback.requestID, document: "document-b")))
        #expect(!queue.retain(target(callback.requestID, engine: "any")))
        #expect(queue.beginNavigation(callback))
        #expect(!queue.beginNavigation(callback))
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == nil)
        #expect(queue.pending(engineID: "heart", accountID: "account-a") == [callback])
    }

    @Test func accountChangeRevokesNavigationAndPreservesOriginalCallback() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target()
        queue.retain(callback)
        queue.beginNavigation(callback)
        queue.suspendNavigation()
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-b", ready: true) == nil)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == callback)
        #expect(queue.beginNavigation(callback))
    }

    @Test func onlyExactMountedDocumentCanFinishNavigation() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target()
        queue.retain(callback)
        #expect(!queue.didReachEditor(target(callback.requestID, account: "account-b")))
        #expect(!queue.didReachEditor(target(callback.requestID, space: "space-b")))
        #expect(!queue.didReachEditor(target(callback.requestID, document: "document-b")))
        #expect(!queue.didReachEditor(target(callback.requestID, scene: "scene-b")))
        #expect(queue.didReachEditor(callback))
        #expect(!queue.didReachEditor(callback))
        #expect(queue.pending(engineID: "heart", accountID: "account-a").isEmpty)
    }

    @Test func queuedCallbacksDoNotReplaceInFlightNavigation() {
        let queue = PinkhaMiniAppsReturnQueue()
        let first = target()
        let otherAccount = target(account: "account-b")
        let second = target(document: "document-b")
        queue.retain(first)
        queue.retain(otherAccount)
        queue.retain(second)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == first)
        queue.beginNavigation(first)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == nil)
        queue.didReachEditor(first)
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == second)
        #expect(queue.pending(engineID: "heart", accountID: "account-b") == [otherAccount])
    }

    @Test func identityComparisonUsesOriginalBytesNotUnicodeNormalization() {
        let queue = PinkhaMiniAppsReturnQueue()
        let callback = target(account: "\u{e9}")
        let decomposed = "e\u{301}"
        #expect(callback.accountID == decomposed)
        queue.retain(callback)
        #expect(queue.nextNavigation(engineID: "heart", accountID: decomposed, ready: true) == nil)
        #expect(!queue.retain(target(callback.requestID, account: decomposed)))
        #expect(!callback.matches(engineID: "heart", accountID: decomposed,
                                 spaceID: "space-a", documentID: "document-a"))
    }

    @Test func invalidOrUnretainedTargetsNeverNavigate() {
        let queue = PinkhaMiniAppsReturnQueue()
        #expect(!queue.retain(target(account: "")))
        #expect(!queue.retain(target(space: "bad\u{0}space")))
        #expect(!queue.retain(target(document: "")))
        #expect(!queue.beginNavigation(target()))
        #expect(queue.nextNavigation(engineID: "heart", accountID: "account-a", ready: true) == nil)
    }
}

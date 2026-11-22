import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import TorahInspectorCore
@testable import PinkhaAnyUI

@Suite("Native Any related-read authority mapping")
struct AnyTorahRelatedReadFailureTests {
    @Test
    func confirmedNativeAndOwnerFailuresDiscardPriorResults() {
        let denied: [any Error] = [
            TorahAssociationRepositoryError.permissionDenied,
            AnyEngineError.http(status: 403, code: "forbidden")
        ]
        for error in denied {
            #expect(AnyTorahRelatedReadFailure.classify(error, ownerIsActive: true) == .denied)
        }
        let invalidated: [any Error] = [
            AnyHostError.sessionClosed, AnyHostError.engineRestarted, AnyHostError.wrongWorkspace,
            AnyEngineError.accountChanged, AnyEngineError.http(status: 401, code: "unauthorized")
        ]
        for error in invalidated {
            #expect(AnyTorahRelatedReadFailure.classify(error, ownerIsActive: true) == .invalidated)
        }
    }

    @Test(arguments: [false, true])
    func cancellationUsesActualOwnerState(ownerIsActive: Bool) {
        let result = AnyTorahRelatedReadFailure.classify(CancellationError(), ownerIsActive: ownerIsActive)
        #expect(result == (ownerIsActive ? nil : .invalidated))
    }

    @Test
    func ordinaryFailuresAreNotRelabelledAsPermissionDenials() {
        let errors: [any Error] = [
            URLError(.notConnectedToInternet),
            AnyEngineError.http(status: 500, code: "forbidden"),
            AnyEngineError.http(status: 400, code: "permission denied"),
            AnyEngineError.malformedResponse("accountChanged"),
            AnyHostError.incompleteDocument,
            NSError(domain: "PINKHA_CURRENT_SPACE_READ_DENIED_V1", code: 2)
        ]
        for error in errors {
            #expect(AnyTorahRelatedReadFailure.classify(error, ownerIsActive: true) == nil)
        }
    }
}

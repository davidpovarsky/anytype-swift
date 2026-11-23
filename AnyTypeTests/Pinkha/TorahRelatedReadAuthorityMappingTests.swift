import Foundation
import Testing
import ProtobufMessages
import SwiftProtobuf
import TorahInspectorCore
@testable import Anytype

@Suite("Heart related-read current authority mapping")
@MainActor
struct TorahRelatedReadAuthorityMappingTests {
    @Test(.tags(.pinkhaSDK06Pending23), arguments: [false, true])
    func nativeDenialRequiresExactTypedCodeAndDescription(objectShow: Bool) {
        func nativeError(_ description: String, badInput: Bool = true) -> any Error {
            if objectShow {
                var responseError = Anytype_Rpc.Object.Show.Response.Error()
                responseError.code = badInput ? .badInput : .unknownError
                responseError.description_p = description
                return responseError
            }
            var responseError = Anytype_Rpc.Object.Search.Response.Error()
            responseError.code = badInput ? .badInput : .unknownError
            responseError.description_p = description
            return responseError
        }
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError("PINKHA_CURRENT_SPACE_READ_DENIED_V1")) == .denied)
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError("PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1")) == .invalidated)
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError("PINKHA_CURRENT_SPACE_READ_DENIED_V1", badInput: false)) == nil)
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError("account must be started")) == nil)
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError(" PINKHA_CURRENT_SPACE_READ_DENIED_V1")) == nil)
        #expect(AnytypeTorahRelatedReadFailure.classify(
            nativeError("PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1: timeout")) == nil)
    }

    @Test(.tags(.pinkhaSDK06Pending23))
    func providerAndTransportDescriptionsCannotForgeNativeAuthority() {
        #expect(AnytypeTorahRelatedReadFailure.classify(
            NSError(domain: "PINKHA_CURRENT_SPACE_READ_DENIED_V1", code: 2)) == nil)
        #expect(AnytypeTorahRelatedReadFailure.classify(URLError(.notConnectedToInternet)) == nil)
        #expect(AnytypeTorahRelatedReadFailure.classify(CancellationError()) == nil)
    }
}

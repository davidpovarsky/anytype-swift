import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// The identity of one active native engine, captured by the server. This is
/// separate from the managed control token and must not be persisted or logged.
public struct AnyNativeAccountRunBinding: Equatable, Sendable,
    CustomStringConvertible, CustomDebugStringConvertible {
    public static let contract = "pinkha-any-http-engine-binding-v1"
    public let accountID: String
    public let networkID: String
    let runID: String

    init(accountID: String, networkID: String, runID: String) throws {
        guard Self.validIdentity(accountID), Self.validIdentity(networkID),
              runID.utf8.count == 64,
              runID.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnyEngineError.invalidIdentity("native account/run binding")
        }
        self.accountID = accountID
        self.networkID = networkID
        self.runID = runID
    }

    public var description: String { "AnyNativeAccountRunBinding(redacted)" }
    public var debugDescription: String { description }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.accountID.utf8.elementsEqual(rhs.accountID.utf8)
            && lhs.networkID.utf8.elementsEqual(rhs.networkID.utf8)
            && lhs.runID.utf8.elementsEqual(rhs.runID.utf8)
    }

    static func decode(_ value: AnyJSON, expectedAccountID: String,
                       expectedNetworkID: String) throws -> Self {
        guard let fields = value.object,
              Set(fields.keys) == Set(["contract", "accountId", "networkId", "runId"]),
              let contract = fields["contract"]?.string,
              contract.utf8.elementsEqual(Self.contract.utf8),
              let account = fields["accountId"]?.string,
              let network = fields["networkId"]?.string,
              let run = fields["runId"]?.string else {
            throw AnyEngineError.malformedResponse("native account/run binding")
        }
        let binding = try Self(accountID: account, networkID: network, runID: run)
        guard account.utf8.elementsEqual(expectedAccountID.utf8),
              network.utf8.elementsEqual(expectedNetworkID.utf8) else {
            throw AnyEngineError.accountChanged
        }
        return binding
    }

    func apply(to request: inout URLRequest) {
        request.setValue(accountID, forHTTPHeaderField: "X-Any-Expected-Account-Id")
        request.setValue(runID, forHTTPHeaderField: "X-Any-Expected-Run-Id")
    }

    /// Successful mutations must identify the engine that actually performed
    /// them. The caller retains this acknowledgment before any awaited check.
    func requireResponse(_ response: HTTPURLResponse) throws {
        guard let contract = response.value(forHTTPHeaderField: "X-Any-Binding-Contract"),
              contract.utf8.elementsEqual(Self.contract.utf8),
              let account = response.value(forHTTPHeaderField: "X-Any-Bound-Account-Id"),
              account.utf8.elementsEqual(accountID.utf8),
              let run = response.value(forHTTPHeaderField: "X-Any-Bound-Run-Id"),
              run.utf8.elementsEqual(runID.utf8) else {
            throw AnyEngineError.writeUncertain
        }
    }

    /// Dedicated paths make an older server reject the request before a
    /// mutation; an older unbound route must never be used as a fallback.
    static func requireRoute(method: String, path: [String]) throws {
        guard path.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".."
            && !$0.utf8.contains(0) }) else {
            throw AnyEngineError.invalidEndpoint
        }
        let settings = method == "PATCH" && path.count == 6
            && Array(path.prefix(4)) == ["v1", "pinkha", "bound", "spaces"]
            && path[5] == "settings"
        let localProperty = method == "POST" && path.count == 9
            && Array(path.prefix(4)) == ["v1", "pinkha", "bound", "spaces"]
            && path[5] == "properties" && path[7] == "set" && path[8] == "any"
        guard settings || localProperty else {
            throw AnyEngineError.invalidOperation("native bound mutation route")
        }
    }

    private static func validIdentity(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096
            && value.utf8.allSatisfy({ $0 > 32 && $0 != 127 })
    }
}

/// A known acknowledgment in the original native account/run. Keeping it
/// separate lets a caller reconcile a later lease failure without resending.
public struct AnyNativeBoundMutationResponse: Sendable {
    public let binding: AnyNativeAccountRunBinding
    public let response: AnyHTTPJSONResponse
}


// Test-runner-only fixture protocol. These types never enter the app target.
private enum HanlinMountedFixtureError: Error {
    case missingConfiguration, invalidConfiguration, invalidResponse
    case wrongFixtureContract, fixtureFailed(String), phaseDeadline(Int), unexpectedPhase(Int)
    case unavailableBlockGutter, invalidCreatePrompt, unavailableReceipt, incompleteProof
}

private struct HanlinMountedFixtureScenario: Encodable, Sendable {
    let selectedBlockID: String
    let selectedText: String
    let unselectedText: String
    let documentTitle: String
    let cancelledTitle: String
    let approvedTitle: String
    let objectReference: String
}

private struct HanlinMountedFixtureReady: Decodable, Sendable {
    let schema: Int
    let contract: String
    let ready: Bool
}

private struct HanlinMountedFixtureStatus: Codable, Sendable {
    let schema: Int
    let contract: String
    let runID: String
    let scope: String
    let state: String
    let complete: Bool
    let phase: Int
    let providerRequests: Int
    let responsesDelivered: Int
    let stopped: Bool
    let scenarioSHA256: String?
    let observedScopeSHA256: String?
    let observedObjectSHA256: String?
    let observedSpaceSHA256: String?
    let observedRevisionSHA256: String?
    let registeredObjectCompared: Bool
    let registeredSpaceCompared: Bool
    let checks: [String: Bool]
    let failureCode: String?
    let rejections: [String: Int]
    let requestMetadata: [RequestMetadata]

    struct RequestMetadata: Codable, Sendable {
        let round: Int
        let bytes: Int
        let sha256: String
        let messageCount: Int
        let toolCallCount: Int
        let toolResultCount: Int
    }

    static let checkNames: Set<String> = [
        "scenario_registered_once", "denied_read_catalog_omits_read_tool",
        "denied_read_has_no_source_text", "allowed_read_exact_schema",
        "read_original_call_identity", "selected_payload_exact_block_and_text",
        "selected_payload_scope_shape_valid", "unselected_text_never_disclosed",
        "cancel_creation_exact_title_call", "cancel_creation_refused",
        "allowed_creation_new_exact_call", "allowed_creation_empty_success",
        "six_provider_requests_completed"
    ]

    func validate(expectedRunID: String? = nil) throws {
        guard expectedRunID.map({ $0 == runID }) ?? true,
              schema == 1, contract == "pinkha-mounted-hanlin-provider-fixture-v1",
              scope == "test_provider_protocol_only_not_Apple_or_native_acceptance",
              UUID(uuidString: runID) != nil, (0...6).contains(phase),
              (0...6).contains(providerRequests), (0...6).contains(responsesDelivered),
              responsesDelivered <= phase, phase - responsesDelivered <= 1,
              Set(checks.keys) == Self.checkNames, !stopped else {
            throw HanlinMountedFixtureError.wrongFixtureContract
        }
        if let failureCode { throw HanlinMountedFixtureError.fixtureFailed(failureCode) }
        guard state != "failed" else { throw HanlinMountedFixtureError.incompleteProof }
    }

    func requireComplete() throws {
        try validate()
        guard complete, state == "complete", phase == 6,
              providerRequests == 6, responsesDelivered == 6, requestMetadata.count == 6,
              checks.values.allSatisfy({ $0 }), registeredObjectCompared,
              rejections.values.allSatisfy({ $0 == 0 }),
              [scenarioSHA256, observedScopeSHA256, observedObjectSHA256,
               observedSpaceSHA256, observedRevisionSHA256].allSatisfy({
                  guard let value = $0 else { return false }
                  return value.count == 64 && value.utf8.allSatisfy {
                      (48...57).contains($0) || (97...102).contains($0)
                  }
              }) else { throw HanlinMountedFixtureError.incompleteProof }
    }
}

@MainActor
private final class HanlinMountedFixtureClient {
    let providerURL: URL
    let model: String
    let providerKey: String
    private let controlURL: URL
    private let controlToken: String
    private let session: URLSession
    private var registeredRunID: String?

    init(environment: [String: String]) throws {
        let prefix = "PINKHA_HANLIN_FIXTURE"
        guard let rawProvider = environment[prefix + "_URL"],
              let model = environment[prefix + "_MODEL"], !model.isEmpty,
              let key = environment[prefix + "_KEY"], !key.isEmpty,
              let rawControl = environment[prefix + "_CONTROL_URL"],
              let token = environment[prefix + "_CONTROL_TOKEN"], !token.isEmpty else {
            throw HanlinMountedFixtureError.missingConfiguration
        }
        guard let provider = URLComponents(string: rawProvider),
              let control = URLComponents(string: rawControl),
              provider.scheme == "https", control.scheme == "https",
              provider.host == "127.0.0.1", control.host == provider.host,
              provider.port != nil, control.port == provider.port,
              provider.path == "/v1", control.path == "/__fixture",
              provider.user == nil, provider.password == nil, provider.query == nil, provider.fragment == nil,
              control.user == nil, control.password == nil, control.query == nil, control.fragment == nil,
              let providerURL = provider.url, let controlURL = control.url else {
            throw HanlinMountedFixtureError.invalidConfiguration
        }
        self.providerURL = providerURL; self.controlURL = controlURL
        self.model = model; self.providerKey = key; self.controlToken = token
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 10
        configuration.timeoutIntervalForResource = 15
        configuration.httpShouldSetCookies = false
        // Default system certificate validation: no delegate, trust override,
        // URLProtocol replacement, proxy, or app-environment configuration.
        self.session = URLSession(configuration: configuration)
    }

    func close() { session.invalidateAndCancel() }

    func requireReady() async throws {
        let value: HanlinMountedFixtureReady = try await request(
            "ready", method: "GET", body: nil, authenticated: false, status: 200)
        guard value.schema == 1, value.contract == "pinkha-mounted-hanlin-provider-fixture-v1",
              value.ready else { throw HanlinMountedFixtureError.wrongFixtureContract }
    }

    func register(_ scenario: HanlinMountedFixtureScenario) async throws {
        guard registeredRunID == nil else { throw HanlinMountedFixtureError.wrongFixtureContract }
        let value: HanlinMountedFixtureStatus = try await request("scenario", method: "POST",
            body: try JSONEncoder().encode(scenario), authenticated: true, status: 201)
        try value.validate()
        guard value.phase == 0, value.providerRequests == 0, value.responsesDelivered == 0,
              !value.complete, value.state == "running",
              value.checks["scenario_registered_once"] == true else {
            throw HanlinMountedFixtureError.incompleteProof
        }
        registeredRunID = value.runID
    }

    func waitForPhase(_ phase: Int, timeout: TimeInterval = 45) async throws -> HanlinMountedFixtureStatus {
        guard let expectedRunID = registeredRunID else {
            throw HanlinMountedFixtureError.wrongFixtureContract
        }
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            try Task.checkCancellation()
            let value: HanlinMountedFixtureStatus = try await request(
                "status", method: "GET", body: nil, authenticated: true, status: 200)
            try value.validate(expectedRunID: expectedRunID)
            if value.phase > phase { throw HanlinMountedFixtureError.unexpectedPhase(value.phase) }
            if value.phase == phase && value.responsesDelivered == phase { return value }
            // Five bounded 45-second waits allow at most 225 read-only polls, keeping
            // ready/register/provider/finalization requests below the fixture's
            // fixed 256-request cap without extending any deadline.
            try await Task.sleep(for: .seconds(1))
        }
        throw HanlinMountedFixtureError.phaseDeadline(phase)
    }

    private func request<T: Decodable>(_ route: String, method: String, body: Data?,
                                        authenticated: Bool, status: Int) async throws -> T {
        let url = controlURL.appendingPathComponent(route)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        if body != nil { request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        if authenticated {
            request.setValue("Bearer " + controlToken, forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == status,
              http.url == url, data.count <= 131_072 else {
            throw HanlinMountedFixtureError.invalidResponse
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}

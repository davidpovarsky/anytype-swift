import Foundation
import XCTest
@testable import PinkhaAnyRuntime

@MainActor
final class AnyEmbeddedRuntimeTests: XCTestCase {
    func testRealManagedRuntimeLifecycleAndControlBoundary() async throws {
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("pinkha-any-native-" + UUID().uuidString, isDirectory: true)
        let network = AnyEmbeddedNetwork.custom(nodeconfYAML: "networkId: pinkha-native-lifecycle-test\nnodes: []\n")
        do {
            let first = try await runtime.start(dataDirectory: directory, network: network, build: .linked)
            XCTAssertEqual(first.baseURL.host, "127.0.0.1")
            XCTAssertTrue(first.engineVersion.hasPrefix(AnyEmbeddedBuild.linked.versionPrefix))
            let (health, response) = try await URLSession.shared.data(
                for: first.authenticatedRead(path: "health"))
            XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
            let json = try XCTUnwrap(JSONSerialization.jsonObject(with: health) as? [String: Any])
            XCTAssertEqual(json["status"] as? String, "ok")

            let (auth, authResponse) = try await URLSession.shared.data(
                for: first.authenticatedRead(path: "auth"))
            XCTAssertEqual((authResponse as? HTTPURLResponse)?.statusCode, 200)
            let authJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: auth) as? [String: Any])
            XCTAssertEqual(authJSON["authorized"] as? Bool, false)

            if AnyEmbeddedBuild.linked == .pinkhaNativeV1 {
                for path in ["health", "auth", "spaces", "pinkha/capabilities"] {
                    let (_, refused) = try await observedRuntimeDeniedRead(
                        from: first.baseURL.appendingPathComponent("v1/" + path), route: path)
                    XCTAssertEqual((refused as? HTTPURLResponse)?.statusCode, 403,
                                   "Every mobile read/data route must require the host capability.")
                }
                var wrong = URLRequest(url: first.baseURL.appendingPathComponent("v1/health"))
                wrong.setValue("wrong", forHTTPHeaderField: "X-Any-Control-Token")
                let (_, refused) = try await URLSession.shared.data(for: wrong)
                XCTAssertEqual((refused as? HTTPURLResponse)?.statusCode, 403)
            }

            var unauthorized = URLRequest(url: first.baseURL.appendingPathComponent("v1/shutdown"))
            unauthorized.httpMethod = "POST"
            unauthorized.httpBody = Data("{}".utf8)
            unauthorized.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let (_, deniedResponse) = try await URLSession.shared.data(for: unauthorized)
            XCTAssertEqual((deniedResponse as? HTTPURLResponse)?.statusCode, 403)

            do {
                _ = try await runtime.start(dataDirectory: directory, network: network, build: .linked)
                XCTFail("A second start must not silently take ownership.")
            } catch let error as AnyEmbeddedRuntimeError {
                XCTAssertEqual(error, .alreadyRunning)
            }

            await runtime.stop()
            let stopped = await runtime.currentSession()
            XCTAssertNil(stopped)
            let second = try await runtime.start(dataDirectory: directory, network: network, build: .linked)
            XCTAssertNotEqual(first.generation, second.generation)
            XCTAssertNotEqual(
                first.controlRequest(.signOut).value(forHTTPHeaderField: "X-Any-Control-Token"),
                second.controlRequest(.signOut).value(forHTTPHeaderField: "X-Any-Control-Token")
            )
            do {
                _ = try await runtime.executeControl(.signOut, expectedGeneration: first.generation)
                XCTFail("A stale owner cannot control a later native boot.")
            } catch let error as AnyEmbeddedRuntimeError {
                XCTAssertEqual(error, .sessionChanged)
            }
            first.emergencyStop.requestStop()
            await runtime.stop(expectedGeneration: first.generation)
            let stillSecond = await runtime.currentSession()
            XCTAssertEqual(stillSecond?.generation, second.generation)
            let (_, liveResponse) = try await URLSession.shared.data(
                for: second.authenticatedRead(path: "health"))
            XCTAssertEqual((liveResponse as? HTTPURLResponse)?.statusCode, 200)
            await runtime.stopNow()
            // A restart waits for the native hard-stop drain before reusing disk.
            _ = try await runtime.start(dataDirectory: directory, network: network, build: .linked)
            await runtime.stop()
            await runtime.stop()
            try FileManager.default.removeItem(at: directory)
        } catch {
            await runtime.stop()
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    func testWrongNativeBuildContractCannotStart() async throws {
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let wrong: AnyEmbeddedBuild = AnyEmbeddedBuild.linked == .upstreamV050 ? .pinkhaNativeV1 : .upstreamV050
        do {
            _ = try await runtime.start(dataDirectory: directory,
                network: .custom(nodeconfYAML: "networkId: pinkha-build-contract-test\\nnodes: []\\n"), build: wrong)
            XCTFail("A different native contract must not start.")
        } catch let error as AnyEmbeddedRuntimeError {
            XCTAssertEqual(error, .unexpectedVersion)
        }
        let current = await runtime.currentSession()
        XCTAssertNil(current)
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.path))
    }

    func testInvalidConfigurationCannotSelectProductionByAccident() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        do {
            _ = try await AnyEmbeddedRuntime.shared.start(
                dataDirectory: directory, network: .custom(nodeconfYAML: " \n"))
            XCTFail("Empty custom network must not select the official network.")
        } catch let error as AnyEmbeddedRuntimeError {
            XCTAssertEqual(error, .invalidConfiguration)
        }
        let current = await AnyEmbeddedRuntime.shared.currentSession()
        XCTAssertNil(current)
    }
}

// Test-only, passive observation of the original denied reads. This retains
// URLSession.shared and its default request policies; it never substitutes,
// retries, cancels, or decides whether a business assertion passes.
private func observedRuntimeDeniedRead(
    from url: URL, route: String
) async throws -> (Data, URLResponse) {
    let observer = RuntimeDeniedReadMetrics(route: route)
    // Retain the task delegate through both the await and either terminal path.
    // The observer retains no task/session, so there is no ownership cycle.
    defer { withExtendedLifetime(observer) {} }
    observer.started()
    do {
        let result = try await URLSession.shared.data(from: url, delegate: observer)
        observer.finished(response: result.1, returnedByteCount: result.0.count)
        return result
    } catch {
        observer.failed(error)
        throw error
    }
}

/// URLSession invokes this nonisolated delegate on its own callback queue.
/// The only mutable state is a counter guarded by stateLock. No lock is held
/// during output or across an await; Foundation task/metrics objects never
/// escape their callback. @unchecked Sendable covers that explicit discipline.
private final class RuntimeDeniedReadMetrics: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    private let observationID = UUID().uuidString
    private let route: String
    private let startedUptime = ProcessInfo.processInfo.systemUptime
    private let stateLock = NSLock()
    private var metricsCallbackCount = 0

    init(route: String) {
        let allowed = ["health", "auth", "spaces", "pinkha/capabilities"]
        self.route = allowed.contains(route) ? route : "other"
        super.init()
    }

    func started() {
        emit(phase: "start")
    }

    func finished(response: URLResponse, returnedByteCount: Int) {
        var fields: [String: Any] = [
            "expectedContentLength": response.expectedContentLength,
            "returnedBodyByteCount": returnedByteCount
        ]
        if let http = response as? HTTPURLResponse { fields["status"] = http.statusCode }
        emit(phase: "end", fields: fields)
    }

    func failed(_ error: any Error) {
        let native = error as NSError
        // Never emit NSError descriptions/userInfo, URLs, or response content.
        let domain: String
        switch native.domain {
        case NSURLErrorDomain: domain = "NSURLErrorDomain"
        case NSCocoaErrorDomain: domain = "NSCocoaErrorDomain"
        case NSPOSIXErrorDomain: domain = "NSPOSIXErrorDomain"
        default: domain = "other"
        }
        emit(phase: "error", fields: ["errorDomain": domain, "errorCode": native.code])
    }

    // Observe metrics only. Auth challenges, redirects, response disposition,
    // byte delivery and completion retain URLSession's original behavior.
    func urlSession(
        _ session: URLSession, task: URLSessionTask,
        didFinishCollecting metrics: URLSessionTaskMetrics
    ) {
        incrementMetricsCount()
        let transactions: [[String: Any]] = metrics.transactionMetrics.prefix(16).map { metric in
            var row: [String: Any] = [
                "fetchStartUnixMs": Self.timestamp(metric.fetchStartDate),
                "domainLookupStartUnixMs": Self.timestamp(metric.domainLookupStartDate),
                "domainLookupEndUnixMs": Self.timestamp(metric.domainLookupEndDate),
                "connectStartUnixMs": Self.timestamp(metric.connectStartDate),
                "connectEndUnixMs": Self.timestamp(metric.connectEndDate),
                "secureConnectionStartUnixMs": Self.timestamp(metric.secureConnectionStartDate),
                "secureConnectionEndUnixMs": Self.timestamp(metric.secureConnectionEndDate),
                "requestStartUnixMs": Self.timestamp(metric.requestStartDate),
                "requestEndUnixMs": Self.timestamp(metric.requestEndDate),
                "responseStartUnixMs": Self.timestamp(metric.responseStartDate),
                "responseEndUnixMs": Self.timestamp(metric.responseEndDate),
                "protocol": Self.protocolLabel(metric.networkProtocolName),
                "reusedConnection": metric.isReusedConnection,
                "proxyConnection": metric.isProxyConnection,
                "resourceFetchType": metric.resourceFetchType.rawValue,
                "requestHeaderBytesSent": metric.countOfRequestHeaderBytesSent,
                "requestBodyBytesSent": metric.countOfRequestBodyBytesSent,
                "requestBodyBytesBeforeEncoding": metric.countOfRequestBodyBytesBeforeEncoding,
                "responseHeaderBytesReceived": metric.countOfResponseHeaderBytesReceived,
                "responseBodyBytesReceived": metric.countOfResponseBodyBytesReceived,
                "responseBodyBytesAfterDecoding": metric.countOfResponseBodyBytesAfterDecoding,
                "responsePresent": metric.response != nil
            ]
            if let response = metric.response {
                row["expectedContentLength"] = response.expectedContentLength
                if let http = response as? HTTPURLResponse { row["status"] = http.statusCode }
            }
            return row
        }
        var fields: [String: Any] = [
            "taskIdentifier": task.taskIdentifier,
            "taskIntervalStartUnixMs": Self.timestamp(metrics.taskInterval.start),
            "taskIntervalEndUnixMs": Self.timestamp(metrics.taskInterval.end),
            "taskDurationMs": metrics.taskInterval.duration * 1_000,
            "redirectCount": metrics.redirectCount,
            "transactionCount": metrics.transactionMetrics.count,
            "omittedTransactionCount": max(0, metrics.transactionMetrics.count - 16),
            "taskBytesSent": task.countOfBytesSent,
            "taskBytesReceived": task.countOfBytesReceived,
            "taskExpectedBytesToReceive": task.countOfBytesExpectedToReceive,
            "transactions": transactions
        ]
        if let response = task.response {
            fields["expectedContentLength"] = response.expectedContentLength
            if let http = response as? HTTPURLResponse { fields["status"] = http.statusCode }
        }
        emit(phase: "metrics", fields: fields)
    }

    private func incrementMetricsCount() {
        stateLock.lock()
        metricsCallbackCount += 1
        stateLock.unlock()
    }

    private func currentMetricsCount() -> Int {
        stateLock.lock()
        defer { stateLock.unlock() }
        return metricsCallbackCount
    }

    private static func timestamp(_ date: Date?) -> Any {
        guard let date else { return NSNull() }
        return date.timeIntervalSince1970 * 1_000
    }

    private static func protocolLabel(_ value: String?) -> String {
        guard let value else { return "unknown" }
        return ["http/1.0", "http/1.1", "h2", "h3"].contains(value) ? value : "other"
    }

    private func emit(phase: String, fields: [String: Any] = [:]) {
        var event = fields
        event["schemaVersion"] = 1
        event["observationID"] = observationID
        event["route"] = route
        event["phase"] = phase
        event["timestampUnixMs"] = Date().timeIntervalSince1970 * 1_000
        event["elapsedMonotonicMs"] = (ProcessInfo.processInfo.systemUptime - startedUptime) * 1_000
        // A missing metrics callback means unknown, never "no headers received".
        event["metricsCallbackCount"] = currentMetricsCount()
        guard let encoded = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) else {
            try? FileHandle.standardError.write(contentsOf: Data(
                "PINKHA_RUNTIME_HTTP_METRICS {\"schemaVersion\":1,\"phase\":\"diagnostic_encode_failed\"}\n".utf8))
            return
        }
        var line = Data("PINKHA_RUNTIME_HTTP_METRICS ".utf8)
        line.append(encoded)
        line.append(0x0A)
        // Output failure is diagnostic-only and cannot change the original test.
        try? FileHandle.standardError.write(contentsOf: line)
    }
}

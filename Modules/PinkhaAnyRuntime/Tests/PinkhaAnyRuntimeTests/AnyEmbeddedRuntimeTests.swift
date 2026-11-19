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
            let first = try await runtime.start(dataDirectory: directory, network: network)
            XCTAssertEqual(first.baseURL.host, "127.0.0.1")
            XCTAssertTrue(first.engineVersion.hasPrefix("any v0.5.0 "))
            let (health, response) = try await URLSession.shared.data(
                from: first.baseURL.appendingPathComponent("v1/health"))
            XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
            let json = try XCTUnwrap(JSONSerialization.jsonObject(with: health) as? [String: Any])
            XCTAssertEqual(json["status"] as? String, "ok")

            let (auth, authResponse) = try await URLSession.shared.data(
                from: first.baseURL.appendingPathComponent("v1/auth"))
            XCTAssertEqual((authResponse as? HTTPURLResponse)?.statusCode, 200)
            let authJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: auth) as? [String: Any])
            XCTAssertEqual(authJSON["authorized"] as? Bool, false)

            var unauthorized = URLRequest(url: first.baseURL.appendingPathComponent("v1/shutdown"))
            unauthorized.httpMethod = "POST"
            unauthorized.httpBody = Data("{}".utf8)
            unauthorized.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let (_, deniedResponse) = try await URLSession.shared.data(for: unauthorized)
            XCTAssertEqual((deniedResponse as? HTTPURLResponse)?.statusCode, 403)

            do {
                _ = try await runtime.start(dataDirectory: directory, network: network)
                XCTFail("A second start must not silently take ownership.")
            } catch let error as AnyEmbeddedRuntimeError {
                XCTAssertEqual(error, .alreadyRunning)
            }

            await runtime.stop()
            let stopped = await runtime.currentSession()
            XCTAssertNil(stopped)
            let second = try await runtime.start(dataDirectory: directory, network: network)
            XCTAssertNotEqual(first.generation, second.generation)
            XCTAssertNotEqual(
                first.controlRequest(.signOut).value(forHTTPHeaderField: "X-Any-Control-Token"),
                second.controlRequest(.signOut).value(forHTTPHeaderField: "X-Any-Control-Token")
            )
            await runtime.stopNow()
            // A restart waits for the native hard-stop drain before reusing disk.
            _ = try await runtime.start(dataDirectory: directory, network: network)
            await runtime.stop()
            await runtime.stop()
            try FileManager.default.removeItem(at: directory)
        } catch {
            await runtime.stop()
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
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

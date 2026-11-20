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
                    let (_, refused) = try await URLSession.shared.data(
                        from: first.baseURL.appendingPathComponent("v1/" + path))
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

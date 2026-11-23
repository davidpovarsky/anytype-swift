import AVFoundation
import CoreMedia
import Foundation
import ImageIO
import UniformTypeIdentifiers

enum EvidenceError: Error { case invalid(String) }

func require(_ condition: Bool, _ reason: String) throws {
    if !condition { throw EvidenceError.invalid(reason) }
}

func typedError(_ error: Error) -> [String: Any] {
    if case EvidenceError.invalid(let reason) = error {
        return ["type": "EvidenceError", "reason": reason]
    }
    let value = error as NSError
    return ["type": String(describing: type(of: error)),
            "domain": String(value.domain.prefix(120)), "code": value.code]
}

func observedNumber(_ number: Double) -> Any {
    number.isFinite ? number as Any : "nonfinite"
}

struct OriginalCase: Decodable {
    struct Frame: Decodable { let label: String; let seconds: Double }
    let scope: String
    let video_path: String
    let min_seconds: Double
    let max_seconds: Double
    let expected_duration_seconds: Double
    let frames: [Frame]
}

struct Plan: Decodable { let cases: [OriginalCase] }

// The coordinator invokes one pinned case at a time and requires both cases,
// all four exact frames, and both backup outcomes for overall success.
@MainActor
func renderMain() async -> [String: Any] {
    var report: [String: Any] = ["schema_version": 2, "status": "FAIL", "frames": []]
    do {
        try require(CommandLine.arguments.count == 3, "Expected one private plan and output directory")
        let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf:
            URL(fileURLWithPath: CommandLine.arguments[1])))
        try require(plan.cases.count == 1 &&
            ["hanlin", "hierarchy-drag"].contains(plan.cases[0].scope),
            "Only one exact pinned post-onboarding case is allowed per process")
        let item = plan.cases[0]
        report["scope"] = item.scope
        report["requested_window_seconds"] = [item.min_seconds, item.max_seconds]
        report["expected_recording_duration_seconds"] = item.expected_duration_seconds
        let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        try require(item.min_seconds > 100 && item.max_seconds > item.min_seconds,
                    "Frame window is not safely after onboarding")
        try require(Set(item.frames.map(\.label)) == Set(["post-action", "near-failure"])
            && item.frames.count == 2, "Only two named stills per case are allowed")

        let asset = AVURLAsset(url: URL(fileURLWithPath: item.video_path))
        let duration = CMTimeGetSeconds(try await asset.load(.duration))
        report["actual_recording_duration_seconds"] = observedNumber(duration)
        var trackRanges: [[String: Any]] = []
        for track in try await asset.loadTracks(withMediaType: .video) {
            let range = try await track.load(.timeRange)
            trackRanges.append(["start_seconds": observedNumber(CMTimeGetSeconds(range.start)),
                "duration_seconds": observedNumber(CMTimeGetSeconds(range.duration)),
                "end_seconds": observedNumber(CMTimeGetSeconds(CMTimeRangeGetEnd(range)))])
            report["video_track_time_ranges"] = trackRanges
        }
        try require(duration.isFinite && abs(duration - item.expected_duration_seconds) <= 5,
                    "Recording duration does not match original XCTest timeline")

        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.requestedTimeToleranceBefore = CMTime(seconds: 0.1, preferredTimescale: 600)
        generator.requestedTimeToleranceAfter = CMTime(seconds: 0.1, preferredTimescale: 600)
        var frames: [[String: Any]] = []
        for frame in item.frames {
            var observation: [String: Any] = ["scope": item.scope, "label": frame.label,
                "requested_seconds": frame.seconds, "status": "FAIL"]
            do {
                try require(frame.seconds.isFinite && frame.seconds >= item.min_seconds
                    && frame.seconds <= item.max_seconds && frame.seconds < duration - 0.2,
                    "Requested still lies outside the verified action/failure interval")
                let requested = CMTime(seconds: frame.seconds, preferredTimescale: 600)
                let (image, actualTime) = try await generator.image(at: requested)
                let actual = CMTimeGetSeconds(actualTime)
                observation["actual_seconds"] = observedNumber(actual)
                try require(actual.isFinite && abs(actual - frame.seconds) <= 0.5
                    && actual >= item.min_seconds && actual <= item.max_seconds,
                    "Decoded frame timestamp left its verified action/failure interval")
                let name = item.scope + "-" + frame.label + ".png"
                let target = output.appendingPathComponent(name)
                try require(!FileManager.default.fileExists(atPath: target.path),
                            "Refusing to overwrite a still")
                guard let destination = CGImageDestinationCreateWithURL(target as CFURL,
                    UTType.png.identifier as CFString, 1, nil) else {
                    throw EvidenceError.invalid("Could not create a PNG destination")
                }
                CGImageDestinationAddImage(destination, image, nil)
                try require(CGImageDestinationFinalize(destination), "PNG write failed")
                observation.merge(["status": "PASS", "path": "frames/" + name,
                                   "width": image.width, "height": image.height]) { _, new in new }
            } catch {
                observation["error"] = typedError(error)
            }
            frames.append(observation)
            report["frames"] = frames
        }
        report["status"] = frames.count == 2 &&
            frames.allSatisfy { $0["status"] as? String == "PASS" } ? "PASS" : "FAIL"
    } catch {
        report["error"] = typedError(error)
    }
    return report
}

let report = await renderMain()
do {
    let encoded = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
    print(String(decoding: encoded, as: UTF8.self))
    exit(report["status"] as? String == "PASS" ? 0 : 1)
} catch {
    print("{\"schema_version\":2,\"status\":\"FAIL\",\"error\":{\"type\":\"ResultEncodingFailure\"}}")
    exit(1)
}

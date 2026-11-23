import AVFoundation
import CoreMedia
import Foundation
import ImageIO
import UniformTypeIdentifiers

enum EvidenceError: Error { case invalid(String) }

func require(_ condition: Bool, _ reason: String) throws {
    if !condition { throw EvidenceError.invalid(reason) }
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

try require(CommandLine.arguments.count == 3, "Expected one private plan and output directory")
let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf:
    URL(fileURLWithPath: CommandLine.arguments[1])))
try require(Set(plan.cases.map(\.scope)) == Set(["hanlin", "hierarchy-drag"])
    && plan.cases.count == 2, "Only two exact post-onboarding cases are allowed")
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: false)

// Validate both complete recording durations before exporting any still.
var assets: [(OriginalCase, AVURLAsset, Double)] = []
for item in plan.cases {
    try require(item.min_seconds > 100 && item.max_seconds > item.min_seconds,
                "Frame window is not safely after onboarding")
    try require(Set(item.frames.map(\.label)) == Set(["post-action", "near-failure"])
        && item.frames.count == 2, "Only two named stills per case are allowed")
    let asset = AVURLAsset(url: URL(fileURLWithPath: item.video_path))
    let duration = CMTimeGetSeconds(try await asset.load(.duration))
    try require(duration.isFinite && abs(duration - item.expected_duration_seconds) <= 5,
                "Recording duration does not match original XCTest timeline")
    for frame in item.frames {
        try require(frame.seconds.isFinite && frame.seconds >= item.min_seconds
            && frame.seconds <= item.max_seconds && frame.seconds < duration - 0.2,
                    "Requested still lies outside the verified action/failure interval")
    }
    assets.append((item, asset, duration))
}

var cases: [[String: Any]] = []
var frames: [[String: Any]] = []
for (item, asset, duration) in assets {
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.requestedTimeToleranceBefore = CMTime(seconds: 0.1, preferredTimescale: 600)
    generator.requestedTimeToleranceAfter = CMTime(seconds: 0.1, preferredTimescale: 600)
    cases.append(["scope": item.scope, "actual_recording_duration_seconds": duration,
                  "expected_recording_duration_seconds": item.expected_duration_seconds])
    for frame in item.frames {
        let requested = CMTime(seconds: frame.seconds, preferredTimescale: 600)
        let (image, actualTime) = try await generator.image(at: requested)
        let actual = CMTimeGetSeconds(actualTime)
        try require(actual.isFinite && abs(actual - frame.seconds) <= 0.5
            && actual >= item.min_seconds && actual <= item.max_seconds,
                    "Decoded frame timestamp left its verified action/failure interval")
        let name = item.scope + "-" + frame.label + ".png"
        let target = output.appendingPathComponent(name)
        try require(!FileManager.default.fileExists(atPath: target.path), "Refusing to overwrite a still")
        guard let destination = CGImageDestinationCreateWithURL(target as CFURL,
            UTType.png.identifier as CFString, 1, nil) else {
            throw EvidenceError.invalid("Could not create a PNG destination")
        }
        CGImageDestinationAddImage(destination, image, nil)
        try require(CGImageDestinationFinalize(destination), "PNG write failed")
        frames.append(["scope": item.scope, "label": frame.label, "path": "frames/" + name,
                       "requested_seconds": frame.seconds, "actual_seconds": actual,
                       "width": image.width, "height": image.height])
    }
}
let result = try JSONSerialization.data(withJSONObject: ["cases": cases, "frames": frames],
                                        options: [.sortedKeys])
print(String(decoding: result, as: UTF8.self))

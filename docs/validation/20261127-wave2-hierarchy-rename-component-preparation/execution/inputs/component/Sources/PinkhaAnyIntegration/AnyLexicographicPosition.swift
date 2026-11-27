// Swift adaptation of github.com/anyproto/lexid v0.0.6 (CharsAllNoEscape,
// block size 4, step 100), the allocator declared by Any's native wiki API.
//
// MIT License
// Copyright (c) 2023 Any Association
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import Foundation
import PinkhaAnyEngine

/// Native lexid positions remain strings in Any. The Double ordinals used to
/// present PinkhaHierarchySnapshot are never written back as storage positions.
public enum AnyLexicographicPosition {
    public static let maximumBytes = 1024
    private static let characters = (UInt8(33)...UInt8(126)).filter { $0 != 34 && $0 != 92 }
    private static let indexes: [UInt8: Int] =
        Dictionary(uniqueKeysWithValues: characters.enumerated().map { ($0.element, $0.offset) })
    public static let middle = String(decoding: [UInt8](repeating: 80, count: 4), as: UTF8.self)

    public static func isValid(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= maximumBytes &&
            value.utf8.allSatisfy { indexes[$0] != nil }
    }

    public static func between(after: String?, before: String?) throws -> String {
        if let after { try validate(after) }
        if let before { try validate(before) }
        let value: String
        switch (after, before) {
        case (nil, nil): value = middle
        case (let previous?, nil): value = try nextStep(previous, step: 100)
        case (nil, let following?):
            let candidate = previousStep(following, step: 100)
            value = candidate.isEmpty ? try nextBefore("", following) : candidate
        case (let previous?, let following?):
            value = try nextBefore(previous, following)
        }
        try validate(value)
        guard after.map({ $0 < value }) ?? true, before.map({ value < $0 }) ?? true else {
            throw AnyEngineError.incompatibleSchema("native lexid bounds")
        }
        return value
    }

    private static func validate(_ value: String) throws {
        guard isValid(value) else { throw AnyEngineError.invalidIdentity("native lexid position") }
    }

    private static func padding(_ value: String, _ count: Int) -> String {
        guard count > 0 else { return value }
        return value + String(decoding: [UInt8](repeating: characters[0], count: count - 1)
            + [characters[1]], as: UTF8.self)
    }

    private static func nextStep(_ value: String, step: Int) throws -> String {
        var previous = value.isEmpty ? padding("", 4) : value
        let pad = 4 - previous.utf8.count % 4
        if pad != 4 { return padding(previous, pad) }
        while true {
            guard previous.utf8.count <= maximumBytes else { throw AnyEngineError.readLimit }
            var bytes = Array(previous.utf8)
            var carry = false
            for _ in 0..<step {
                carry = true
                for index in bytes.indices.reversed() {
                    if !carry { break }
                    let nextIndex = (indexes[bytes[index]]! + 1) % characters.count
                    var next = characters[nextIndex]
                    carry = next == characters[0]
                    if carry && index == bytes.count - 1 { next = characters[1] }
                    bytes[index] = next
                }
                if carry { break }
            }
            if !carry { return String(decoding: bytes, as: UTF8.self) }
            previous = padding(previous, 4)
        }
    }

    private static func nextBefore(_ previous: String, _ before: String) throws -> String {
        guard previous < before else { throw AnyEngineError.invalidIdentity("native lexid order") }
        var previousPadded = previous
        var beforePadded = before
        let previousPad = 4 - previous.utf8.count % 4
        let beforePad = 4 - before.utf8.count % 4
        if previousPad != 4 { previousPadded = padding(previous, previousPad) }
        if beforePad != 4 { beforePadded = padding(before, beforePad) }
        if previous.isEmpty || before.hasPrefix(previous) {
            let tail = String(before.dropFirst(previous.utf8.count))
            if tail == padding("", tail.utf8.count) {
                let pad = 4 * (beforePadded.utf8.count / 4)
                previousPadded = padding(previousPadded, pad)
                if previousPadded == beforePadded { previousPadded = padding("", pad + 4) }
            }
        }
        let difference = previousPadded.utf8.count - beforePadded.utf8.count
        if difference > 0 { beforePadded = padding(beforePadded, difference) }
        else if difference < 0 { previousPadded = padding(previousPadded, -difference) }
        let distance = approximateDistance(previousPadded, beforePadded)
        if distance > 0 {
            var step = 100
            while Double(step) / Double(distance) > 0.3 { step /= 2 }
            if step > 0 {
                let candidate = try nextStep(previousPadded, step: step)
                if candidate < before { return candidate }
            }
        }
        let candidate = padding(previousPadded + String(decoding: [characters[characters.count / 2]], as: UTF8.self), 3)
        guard previous < candidate, candidate < before else {
            throw AnyEngineError.incompatibleSchema("native lexid interval exhausted")
        }
        return candidate
    }

    /// Match the signed 64-bit wrap behavior of the deployed Go allocator.
    private static func approximateDistance(_ first: String, _ second: String) -> Int64 {
        let first = Array(first.utf8), second = Array(second.utf8)
        let count = min(first.count, second.count)
        guard count > 0 else { return 0 }
        var multiplier: Int64 = 1
        var distance: Int64 = 0
        for index in (0..<count).reversed() {
            let delta = Int64(indexes[second[index]]! - indexes[first[index]]!)
            distance = distance &+ (delta &* multiplier)
            multiplier = multiplier &* Int64(characters.count)
        }
        return distance
    }

    private static func previousStep(_ value: String, step: Int) -> String {
        if value.isEmpty { return String(decoding: [UInt8](repeating: characters.last!, count: 4), as: UTF8.self) }
        var bytes = Array(value.utf8)
        var remaining = step
        while remaining > 0 {
            var borrow = true
            for index in bytes.indices.reversed() {
                if !borrow { break }
                var nextIndex = indexes[bytes[index]]! - 1
                borrow = nextIndex < 0
                if borrow { nextIndex = characters.count - 1 }
                bytes[index] = characters[nextIndex]
            }
            if borrow {
                if bytes.count <= 4 { return "" }
                bytes.removeLast(4)
                if remaining > 1 && !bytes.isEmpty {
                    bytes = [UInt8](repeating: characters.last!, count: bytes.count)
                }
            }
            remaining -= 1
            if !bytes.isEmpty && bytes.allSatisfy({ $0 == characters[0] }) {
                bytes += [UInt8](repeating: characters.last!, count: 4)
            }
            if bytes.count > maximumBytes { return "" }
        }
        return String(decoding: bytes, as: UTF8.self)
    }
}

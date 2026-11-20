import Foundation
public enum ProviderResponseFixtures {
    public static func openAIChatTextChunks(
        text: String,
        id: String = "chatcmpl-text-1",
        model: String = "gpt-4o",
        finishReason: String? = "stop"
    ) -> [String] {
        let first = sseOpenAI([
            "id": id,
            "model": model,
            "choices": [[
                "index": 0,
                "delta": ["role": "assistant", "content": text],
                "finish_reason": NSNull()
            ]]
        ])
        let terminal = sseOpenAI([
            "id": id,
            "model": model,
            "choices": [[
                "index": 0,
                "delta": [:],
                "finish_reason": finishReason as Any
            ]]
        ])
        return [first, terminal, "data: [DONE]\n\n"]
    }

    public static func openAIChatToolCallChunks(
        calls: [(id: String, name: String, arguments: String)],
        id: String = "chatcmpl-tool-1",
        model: String = "gpt-4o",
        finishReason: String = "tool_calls"
    ) -> [String] {
        var toolDeltas: [[String: Any]] = []
        for (idx, call) in calls.enumerated() {
            toolDeltas.append([
                "index": idx,
                "id": call.id,
                "type": "function",
                "function": [
                    "name": call.name,
                    "arguments": call.arguments
                ]
            ])
        }

        let first = sseOpenAI([
            "id": id,
            "model": model,
            "choices": [[
                "index": 0,
                "delta": [
                    "role": "assistant",
                    "tool_calls": toolDeltas
                ],
                "finish_reason": NSNull()
            ]]
        ])
        let terminal = sseOpenAI([
            "id": id,
            "model": model,
            "choices": [[
                "index": 0,
                "delta": [:],
                "finish_reason": finishReason
            ]]
        ])
        return [first, terminal, "data: [DONE]\n\n"]
    }

    private static func sseOpenAI(_ payload: [String: Any]) -> String {
        let data = try! JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
        return "data: \(String(decoding: data, as: UTF8.self))\n\n"
    }

}

struct FixtureCase: Decodable {
    let kind: String
    let identifier: String
    let model: String
    let text: String?
    let callID: String?
    let name: String?
    let arguments: String?
}
let cases = try JSONDecoder().decode([FixtureCase].self,
    from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let chunks: [[String]] = cases.map { item in
    if item.kind == "text" {
        return ProviderResponseFixtures.openAIChatTextChunks(
            text: item.text!, id: item.identifier, model: item.model)
    }
    return ProviderResponseFixtures.openAIChatToolCallChunks(
        calls: [(id: item.callID!, name: item.name!, arguments: item.arguments!)],
        id: item.identifier, model: item.model)
}
FileHandle.standardOutput.write(try JSONEncoder().encode(chunks))

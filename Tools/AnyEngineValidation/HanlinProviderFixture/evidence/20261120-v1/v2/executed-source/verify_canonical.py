#!/usr/bin/env python3
"""Run the two exact pinned Swift fixture builders and compare SSE contracts.

Only the original Foundation-only methods and serialization helper are extracted;
the canonical SDK is never edited. JSON serialization spelling/order may differ,
but every decoded event value, raw tool-argument string, frame boundary, terminal
finish reason and [DONE] marker must match. This is fixture equivalence, not an
execution of Hanlin's production networking or Apple's mounted UI.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from fixture import atomic_json
from protocol import (ALLOW_CALL, CANCEL_CALL, CREATE_TOOL, MARKERS, MODEL,
                      READ_CALL, READ_TOOL, canonical, digest, require, text_chunks, tool_chunks)

PIN = "116cc6be0654a5d11bc56ba00e0310031107ee36"
SOURCE = "Packages/HanlinPlatform/Tests/HanlinChatCoreTests/ProviderConformance/ProviderResponseFixtures.swift"
SOURCE_SHA = "de14c4620dfe2f8b49eb104eb22ca1467efa85ab31ff2968547d0cfb00e9f17a"

HARNESS = r'''
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
'''


def vectors():
    result = [{"kind": "text", "identifier": name, "model": MODEL, "text": text}
              for name, text in zip(("chatcmpl-pinkha-denied", "chatcmpl-pinkha-cancelled",
                                     "chatcmpl-pinkha-approved"), MARKERS)]
    for number, identifier, tool, args in (
        (1, READ_CALL, READ_TOOL, {}),
        (2, CANCEL_CALL, CREATE_TOOL, {"title": "Owned cancelled fixture page"}),
        (4, ALLOW_CALL, CREATE_TOOL, {"title": "Owned approved fixture page"}),
    ):
        result.append({"kind": "tool", "identifier": "chatcmpl-pinkha-" + str(number), "model": MODEL,
                       "callID": identifier, "name": tool, "arguments": canonical(args).decode("utf-8")})
    result.append({"kind": "text", "identifier": "chatcmpl-unicode-escape-control", "model": MODEL,
                   "text": "שָׁלוֹם 🙂 / quote\" backslash\\ newline\n"})
    return result


def decoded(chunk: bytes):
    require(chunk.startswith(b"data: ") and chunk.endswith(b"\n\n")
            and b"\n\n" not in chunk[:-2], "canonical_sse_framing")
    if chunk == b"data: [DONE]\n\n":
        return "[DONE]"
    return json.loads(chunk[6:-2].decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--hanlin-source", required=True)
    parser.add_argument("--swiftc", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(args.repo_root).absolute()
    original = subprocess.run(["git", "-C", args.hanlin_source, "show", PIN + ":" + SOURCE],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
    require(original.returncode == 0 and digest(original.stdout) == SOURCE_SHA, "canonical_source_pin")
    materialized = repo / "Dependencies/Hanlin" / SOURCE
    require(materialized.read_bytes() == original.stdout, "canonical_materialized_source")
    source = original.stdout.decode("utf-8")
    begin = source.index("    public static func openAIChatTextChunks(")
    end = source.index("    public static let richOpaqueReasoningDetailsJSONValue", begin)
    helper_begin = source.index("    private static func sseOpenAI(")
    helper_end = source.index("    private static func sseAnthropic(", helper_begin)
    methods = source[begin:end]
    helper = source[helper_begin:helper_end]
    generated = "import Foundation\npublic enum ProviderResponseFixtures {\n" + methods + helper + "}\n" + HARNESS
    swift_path = output / "main.swift"
    swift_path.write_text(generated, encoding="utf-8", newline="\n")
    (output / "pinned-ProviderResponseFixtures.swift").write_bytes(original.stdout)
    inputs = vectors()
    (output / "vectors.json").write_bytes(canonical(inputs) + b"\n")
    executable = output / ("canonical-fixture.exe" if os.name == "nt" else "canonical-fixture")
    command = [args.swiftc, "-swift-version", "6", "-module-cache-path", str(output / "module-cache"),
               str(swift_path), "-o", str(executable)]
    environment = os.environ.copy()
    if os.name == "nt":
        toolchain = Path(args.swiftc).parent
        swift_root = toolchain.parents[3]
        runtime = swift_root / "Runtimes/6.3.3/usr/bin"
        environment["PATH"] = str(toolchain) + os.pathsep + str(runtime) + os.pathsep + environment.get("PATH", "")
    bounded_path = repo / "Tools/AnyEngineValidation/run_native_torah_probe.py"
    spec = importlib.util.spec_from_file_location("canonical_fixture_owned_compiler", bounded_path)
    bounded_helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounded_helper)
    with (output / "compile.stdout").open("wb") as stdout, (output / "compile.stderr").open("wb") as stderr:
        compile_exit = bounded_helper.bounded(command, cwd=str(repo), env=environment,
                                             stdout=stdout, stderr=stderr, seconds=60)
    require(compile_exit == 0, "canonical_builder_compile")
    run = subprocess.run([str(executable), str(output / "vectors.json")], env=environment,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    (output / "run.stderr").write_bytes(run.stderr)
    require(run.returncode == 0, "canonical_builder_execute")
    actual = json.loads(run.stdout.decode("utf-8"))
    require(len(actual) == len(inputs), "canonical_vector_count")
    for spec, chunks in zip(inputs, actual):
        expected = (text_chunks(spec["text"], identifier=spec["identifier"], model=spec["model"])
                    if spec["kind"] == "text" else tool_chunks(spec["callID"], spec["name"], spec["arguments"],
                        identifier=spec["identifier"], model=spec["model"]))
        require(len(chunks) == len(expected), "canonical_chunk_count")
        require([decoded(v.encode("utf-8")) for v in chunks] == [decoded(v) for v in expected],
                "canonical_response_contract")
    (output / "canonical-chunks.json").write_bytes(run.stdout)
    result = {"schema": 1, "status": "PASS", "scope": "pinned_original_Swift_fixture_contract_equivalence_only",
              "hanlinCommit": PIN, "sourcePath": SOURCE, "sourceSHA256": SOURCE_SHA,
              "generatedSourceSHA256": digest(swift_path.read_bytes()),
              "unalteredMethodsSHA256": digest(methods.encode()), "unalteredHelperSHA256": digest(helper.encode()),
              "vectors": len(inputs), "events": sum(map(len, actual)), "compileExitCode": compile_exit,
              "ownedCompilerHelperSHA256": digest(bounded_path.read_bytes()),
              "executeExitCode": run.returncode, "command": command,
              "executableSHA256": digest(executable.read_bytes()),
              "pythonProtocolSHA256": digest(Path(__file__).with_name("protocol.py").read_bytes()),
              "canonicalOutputSHA256": digest(run.stdout), "sourceStable": materialized.read_bytes() == original.stdout}
    atomic_json(output / "result.json", result)
    print(json.dumps({"status": "PASS", "vectors": len(inputs), "events": sum(map(len, actual)),
                      "sourceStable": result["sourceStable"]}, sort_keys=True))


if __name__ == "__main__":
    main()

# Original RPC continuation — 23 November 2026

Owner: ChatGPT subagent original_rpc; source task 1220545194715722.
Isolated branch: codex/otzaria-rpc-runtime-20261123.
Base: 08ebfa77114e2f8c4efa4491b5222029eda60a3b.

## Scope

The previous real run45055852172 generated 741 baseline rows and compiled its Go message packages. Its Swift typecheck failed before candidate generation. This continuation authenticates the retained original ZIP and command receipts, compares the current immutable generator inputs and tracked output beforeimages, and restores only the original baseline output. Baseline generation and its Go build are REUSED with their original source/run identities; neither is replayed.

The SwiftProtobuf build products were not retained. They and other required tools are rebuilt from the existing immutable pins. The actual SwiftPM release bin path is requested with --show-bin-path; the driver requires one observed SwiftProtobuf.swiftmodule beneath that owned build tree and retains its bytes and hash. Its parent directory supplies the import path. The helper does not assume a Modules directory. Candidate-versus-baseline comparisons explicitly distinguish rebuilt binary fingerprints from the retained original tool receipt.

The remaining execution is the previously failed baseline Swift model typecheck, the first candidate native/Swift generation, candidate Go/Swift model compilation, complete generated-output comparison and unchanged-input/tool checks. Original product sources, protoc recipes, schema afterimages and compiler assertions are unchanged. Full SDK, endpoint/Invocation, app, native persistence and ACK acceptance remain separate.

## Ownership and rollback

All edits are downstream generation/CI helpers, focused helper tests, their input manifest and the one existing workflow trigger. There are no edits to Any-native SDK06, current shared UI/semantic Page154 owners, the original embedded-editor framework lane, credentials, user Spaces or application source. Revert this branch's scoped continuation commit to restore the old gate; no user data was written.

## Validation

The local continuation controls exercise observed SwiftPM layouts, ambiguity/foreign-product rejection, real authenticated 741-row restoration and rejection of foreign archives, changed generator inputs and changed tracked preimages. Those are helper controls only. The Apple generation result and generated delta remain pending until a genuine terminal run and its retained artifact are verified.

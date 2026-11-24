# Native type namespace and independent-account file continuation

Current status: source/controller prepared; the new namespace method and repaired peer journey have not run.

Route: `native-source-file-peers-arm64` (existing inline job).
Command: `python3 Tools/AnyEngineValidation/native_file_peer/run_native.py`.
Public upload: `RUNNER_TEMP/pinkha-native-file-peer/public`.
Success: `NATIVE_TYPE_NAMESPACE_AND_REMOTE_FILE_PEERS_PASS`.

## Original result retained

Run [45472745870/1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45472745870) at app `fb5b40a5e91c68520d0f2921600a9f04b1e25439` / Heart `d2696b36d169f57f1bcb03c055384e5ec944d930` compiled successfully. `TestLoadedAccountNativeSnapshotJSONView` passed for 144 original snapshots, deterministic views and known-field protobuf round trips. The independent Windows recipient verified all 796 original regular members, 46 command streams and 291 declared source bundle members, including account/Space binding. Its original producer result remains FAIL because the separate member file-tree load failed before payload transfer.

The unchanged original public result and independent readback are included in `retained-json-45472745870/`. The controller checks both exact digests and their scoped pass/original failure fields. The successful JSON method is not rerun and is not relabeled as proof at the new native source.

## New source and execution

The original compiler/source carrier, context delta, 18-file whole-source delta and seven-file peer/JSON delta remain unchanged. The new separately admitted three-file delta derives from Heart `d2696b36d169f57f1bcb03c055384e5ec944d930` to `efd0d2d44e871966bf3c8edcc18db73a00ec699c`:

- Closed captured resolver: native `TypeKeyFromUrl` and exact captured object-ID/type-key namespace checks, including missing/colliding/duplicate aliases. Original snapshot bytes are unchanged.
- One new eight-case method `TestLoadedAccountCapturedTypeNamespaces`, including actual native whole-source capture and conservative authority flags.
- Existing file-peer method: supplies the owned sender's native peer context to the original nonmandatory tree lookup. Pinned AnySync otherwise returns `ErrUnknownTreeId` before sending a request when the context has no peer ID. Original assertions and deadlines remain unchanged.

One immutable ARM64 Go1.26.5 build on `ubuntu-24.04-arm`, one CPU /4 GiB and compile network none, produces the actual binary and generated testmain. Selected execution 1 is the new namespace method plus eight subtests. Executions 2–4 are the repaired peer method for owner, independently created member and offline fresh-process member-own-store reopen. No previous C4/inventory/local-source/JSON successful methods are replayed.

Two online processes use independent wallets and network namespaces on an owned internal bridge. The owner supplies a random 2 MiB payload. The controller transfers identities, expected hashes/counts and signed ACL head only. Actual Reader grant, native encrypted object-tree delivery, disconnected receiver-only local DAG offload, authorized bounded native RPC prefetch, per-CID local reread, complete plaintext/metadata equality and own-store offline reopen must all pass.

Raw logs, account stores, snapshots, source keys and payloads remain recipient-encrypted. Public results expose hashes/counts and scoped receipts. Cleanup is limited to this run's unique containers/network. Whole-Space semantic migration, arbitrary legacy/multiple-root formats, history reconstruction and destination conversion remain separate open work; no source/file receipt authorizes destination writes.

# Native snapshot JSON and independent-account file transport

Status: implemented and parsed; actual new native controls have not yet run.

Route: native-source-file-peers-arm64 (one inline central job; no new reusable workflow reference).
Command: python3 Tools/AnyEngineValidation/native_file_peer/run_native.py
Public upload: RUNNER_TEMP/pinkha-native-file-peer/public
Success: NATIVE_JSON_AND_REMOTE_FILE_PEERS_PASS

Source: 973a4970f793230e6325e9f47ea9545f1b6282ad
Base: 67381c31503518b4c0995b29aecd57c89799c6e8 (the exact whole-source enum repair, with its original controller inputs).
This lane reuses the unchanged qualified original compiler/source carrier, original C4 context delta, and exact frozen whole-source source delta. It then admits six additions and one reviewed bundle sidecar extension by byte size, SHA256, native Git blob and before/after identity. Old C4/inventory/whole-source methods are not rerun.

One compile on ubuntu-24.04-arm, native Go1.26.5, one CPU /4GiB, compile network none and immutable source. The actual generated testmain and actual binary list must include exactly the two newly selected names.

Selected execution 1: TestLoadedAccountNativeSnapshotJSONView in a fresh LocalOnly account. Every captured native protobuf is compared to a full native jsonpb view and original private member, including known-field protobuf roundtrip and deterministic repeated output. One actual-created text-only .pb/JSON pair (no FileInfo/FileKeys) remains in the encrypted original for the Swift consumer. No native admission is inferred from that derived view.

Selected executions 2–4: TestLoadedAccountRemoteFilePeer once for owner, once for independent member, and once for member own-store reopen in a new process with network none. The two online processes use independent wallets and distinct network namespaces on one owned internal bridge. Each mounts only its own private account/store and the immutable binary/library inputs. The creator supplies a random2MiB payload; the controller transfers only public account/peer IDs, source object IDs, expected hashes/counts and the signed ACL head. Actual Reader grant, InviteJoin/native tree delivery, receiver-only local DAG offload while disconnected, bounded original native RPC prefetch, per-CID concrete local cache reread and full plaintext/metadata equality must all pass. Reconnect uses the actual dynamically assigned IP. The final process reopens only the member's own persisted wallet and store offline.

Raw logs, native account stores, snapshots, source keys and original payloads remain in the existing private recipient-encrypted evidence. Public results contain hashes/counts and bounded observations only. Cleanup names are unique to the exact run; no shared containers, networks, files or accounts are removed.

This scope leaves whole-Space semantic migration, arbitrary legacy/multiple-root file formats, history reconstruction and destination conversion as explicit separate work. A successful local or remote file receipt never authorizes destination writes.

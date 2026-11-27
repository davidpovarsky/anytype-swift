# Retained Crypto input closure for the isolated Host text-readback component

**Local source-record extraction only. No remote call, copy, cache mutation, compiler, XCTest or Native operation occurred.** The complete fixed list is in `retained-crypto-closure.json` (SHA256 `10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c`). It contains 102 exact paths with byte counts and SHA256 values, original physical paths, historical argument aliases and original-to-isolated-copy bindings.

| Retained inputs | Files | Logical bytes |
| --- | ---: | ---: |
| Crypto / CryptoBoringWrapper module and documentation files | 4 | 1,435,196 |
| Complete CCryptoBoringSSL include tree and module map | 92 | 2,563,877 |
| Complete CCryptoBoringSSLShims include tree and module map | 2 | 7,522 |
| Aggregated Products link objects | 4 | 15,769,120 |
| **Total** | **102** | **19,775,715** |

Rounding each input to 4,096 bytes gives 19,996,672 bytes. That is a calculation, not observed allocated space or a complete build budget. Destination filesystem metadata, fresh-copy evidence, compiler outputs and actual capacity remain separately admitted by the execution owner.

## Exact authority and closure

The original input manifest is `compiled-source-inputs.original.json`, 526,113 bytes, SHA256 `de642b7c2cc54367d1b767807443a38e4803bc8cba628beefa3cee819688f9bc`. The actual prior `Package.swift` is 6,317 bytes, SHA256 `c6fd6d65b5c80ad30ed2f22bd322114e1293afa516fb0d58785600145d76cf53`, retained inside `uploader-source-context.primary.json`.

All six original Swift unsafe-flag arrays are identical. They select only the retained Crypto import directory, the two explicit module maps and their include directories. The extracted 94-header set exactly equals both original manifest include namespaces. Every retained header/import record matches the same-sized, same-hash physical original and its recorded historical alias entry. No other project precompiled module directory is included.

The four link objects, in their original order, are `Crypto.o`, `CryptoBoringWrapper.o`, `CCryptoBoringSSL.o` and `CCryptoBoringSSLShims.o`, followed by `-lstdc++`. Their authoritative physical records are beneath:

`/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127/out/Products/Debug-linux-aarch64/`

The smaller `Intermediates.noindex/.../Modules/Crypto.o` and `CryptoBoringWrapper.o` records are different files and are explicitly excluded. The original package uses corresponding `/tmp/pinkha-w1-migration-swift-20261127/...` link arguments; those object alias paths are not separate entries in the input manifest. No current alias resolution is claimed. Fresh owned copies must bind the pinned physical Products objects. If historical aliases are used, resolve and verify them before execution; otherwise retain the exact path-only transformation to the new owned object copies.

## Original result and toolchain boundary

The original uploader receipt `4b24eb81b7e7fa6b108568ea619bf125148e8952b38879a71cc8091b55d101c5` has overall status **FAIL**, original Swift command exit 1, and unchanged admitted/compiled input records. W1 separately reported 23 passed methods; this extraction did not recount them and does not turn that report into overall PASS or new Host acceptance.

The retained command selects `/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift`, with outer `--jobs 2`; import filenames identify `aarch64-unknown-linux-gnu`. A fresh binary/version/target and C/linker environment binding is still required. This is not a claim that raw Swift modules are portable to another compiler/platform or that the prior full build is equivalent to the new component.

## Before any execution

The coordinated execution owner must verify all physical source hashes and sizes, copy into a fresh owned DEV namespace, verify complete copied membership and physical protection, retain source-before/after and destination identity, and bind actual compiler/linker arguments to those copies. Original source project modules must be compiled in the new component; shared caches remain untouched. Actual selected Host XCTest enumeration/results, process closure and resource receipts remain required. Historical process IDs are retained only as old evidence and must not be probed.

`extract_retained_crypto_closure.py` is the local deterministic manifest extractor, not an execution controller. `pause-status.json` remains the unchanged earlier checkpoint. The initial local inspection's dictionary/list shape error is retained separately; it did not start a child, test or remote operation.

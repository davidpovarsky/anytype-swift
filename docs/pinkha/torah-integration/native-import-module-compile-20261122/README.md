# Original importer module compile gate

This isolated gate checks whether the six reviewed import-origin observation files compile and link inside the real original Heart module. It does not execute an importer, a native application, a test binary, or any previously passed assertion. The existing 50 unit outcomes remain historical evidence over their recorded source closure.

## Exact source and execution

The source parent is `20cb8998211eaefa5ddb00ef60ff2462dd3271e9`. Its complete 94-file origin packet remains tree `be05778c6a9e6412d181ced642694daee3baf30b`. The gate installs the already reviewed `composition/r14/native` afterimages using that packet's unchanged strict installer. It applies the exact original 35-file r14 patch before the six-file overlay and verifies all resulting source hashes. In particular, the composed processor preserves the original `torahtransport.RemapObjects` block, with observation assignment completion only after that block succeeds.

The original Heart checkout is `d98420b1113536afd08cde6de9a5816f6d27ffff`. The native route uses actual Go 1.26.5 on Darwin arm64 with Xcode 27, the original module/checksum files, and the retained original Tantivy helper. That helper downloads the original Tantivy v1.0.6 archive and checks its checksum. This Darwin native lane contains no additional iosrepacks bootstrap; iOS framework packaging is a separate gate.

The only compilation target is:

```sh
go test -c -p 2 -o <owned-output>/original-importer.test ./core/block/import
```

This compiles the real importer test target and its actual dependency graph, including all six changed production files. It does not execute the resulting binary or replay the original importer tests. `go list -deps -test -json` records the actual declared source closure; `go version -m` reads the resulting binary's build metadata without executing it. The existing native lane's finite owned process-group lifecycle is retained, including the absolute workflow budget, failure streams, and cleanup of only the newly owned compiler temporary directory.

## Review and activation

The neutral review branch does not match the workflow trigger. The only trigger is a push to `codex/otzaria-native-import-compile-20261122`; there is no manual-dispatch input, automatic retry, or permissive alternate target. Root must review the immutable source head and explicitly activate that branch. Creating this packet does not activate or dispatch a run.

`EXECUTION_INPUTS.json` binds the runner, original setup functions, source installer/composition, native archive/library, and retained root review receipts. Its hash is supplied by the workflow. The runner also checks the actual workflow head and frozen origin subtree. The four files under `root-review` retain root's independent verification of all 94 published blobs, the actual 50 leaf outcomes, unchanged r14 fragment closure, and the two read-only verifier layout corrections. They do not report a second test execution.

Evidence includes the original module hashes, native library inputs, complete compiler streams, composed source hashes, actual declared dependency inputs, compiler identity, binary hash/size and build metadata, and post-compile source checks. Executable bytes remain in the owned work directory and are not uploaded; the receipt labels that hash as runner-observed.

## Qualification limit

A successful run establishes original-module source and link compatibility only. It does not establish owned import drain on cancellation/failure, converter/provider concurrency safety, full archive/account/attempt binding, complete background file remaps, native body equality, durable import-map authority, commit, or ACK. No production callsite or RPC enables the observation in this gate. The separate lifetime/context audit remains read-only.

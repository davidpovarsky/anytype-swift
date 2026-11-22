# Next original-module gate

The 50 passed controls compile the exact observation logic with explicit dependency fixtures. They do not compile the entire original protobuf converter and importer dependency graph. The next gate must therefore use the actual original Heart source and the existing original native toolchain/dependencies.

## Immutable source preparation

Use Heart commit `d98420b1113536afd08cde6de9a5816f6d27ffff` and the frozen r14 patch SHA256 `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077`. The native schema observer/registration additions may coexist if they leave this packet's four existing importer preimages unchanged.

Apply the r14 patch before this overlay. Use `install_native_sources.py` against the isolated native build checkout. It validates every source and preimage before writing any file, rejects unexpected existing new files, verifies the original Git commit, and reads back all six resulting files. The processor accepts only the exact raw r14 afterimage or its observed Go-formatted afterimage; the other three existing files must match original d984 bytes. Unexpected source changes require an explicit composition review, not an override or a relaxed check.

The final source is under `composition/r14/native`. Do not copy `candidate/native/core/block/import/processor.go` onto an r14 checkout: that retained earlier candidate intentionally shows the d984-only unit source closure. The composed processor preserves r14's existing `torahtransport.RemapObjects` call, and sets the new assignment-completion flag only after that call succeeds. `COMPOSITION_VERIFICATION.json` binds the exact before/after bytes and proves the already executed unit closure is unchanged.

## Compile gate without replaying tests

Reuse the genuine native lane's pinned Go 1.26.5 / Darwin arm64 environment, original r14 Tantivy and iosrepacks dependencies, and existing native build flags. Compile the original importer test target with `go test -c -o <owned-output>/original-importer.test ./core/block/import`. The binary must not be run in this gate. This compiles the actual modified importer, protobuf converter, common types, private observation helpers and original dependency graph, including original importer tests, while selecting no previous assertions and executing no native import.

Retain the exact source commit/overlay receipt, dependency/toolchain bindings, full compile command, exit status, stdout/stderr, and output binary hash. A successful compile is a source compatibility milestone only. An exact source candidate and workflow/command review must precede any activation; this packet creates no CI trigger and dispatches no job.

## Remaining production dependencies

A later genuine import operation still needs ownership retained until every admitted worker drains on both success and failure, protection against shared converter/provider concurrency, authentic source archive/member/attempt/account binding, complete capture of additional file remaps, real native semantic readback, and a closed consumer that validates and durably commits the resulting map. The original async `ObjectImport` immediate response, a process count, copied diagnostic rows, a digest, or the schema registrar's synchronous app lease must not substitute for those dependencies. No production import route or ACK is enabled by this packet.

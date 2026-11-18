# Versioned native Torah RPC boundary — source review

This additive stage registers `PinkhaTorahOperationsAppend` and `PinkhaTorahOperationsReadTarget` in the existing `anytype.ClientCommands` service. Messages live under `anytype.Rpc.Pinkha.TorahOperations`. Existing message/method ordering is preserved by appending the additions. It enables no App UI, startup host creation, generated Swift, deployment or release.

## Wire and authority contract

Both requests require protocol version 1. An absent/unknown version, unknown/zero Kind, nil target or invalid read bound fails before native account/root access. Append accepts Space, stable operation ID, explicit Kind, target/source, exact opaque payload bytes and observed claim IDs. It has no author, root, signing key or ACL verdict. The mapper delegates authority and durable history to the existing native handler; neither endpoint bypasses it through generic object operations.

Append responses carry a versioned metadata receipt: disposition, claim ID and actual signed change ID. Idempotent replay has no new change ID; collision is a distinct non-NULL wire error with its native disposition and full valid resolution. Native execution errors, including joined account-change/projection-behind errors, preserve all receipt metadata but withhold Resolution payloads. A failed fence cannot release cached private payloads. Every joined leaf issue is retained; the primary code follows a stable order. Native error text is never copied into the response: labels are fixed constants.

Successful reads return all live claims, all conflict variants, pending observed references, verified local heads and local AppliedSeq, with explicit `LOCAL_VERIFIED_TREE` scope. This is not acknowledgement from another client. Every read error returns no snapshot. Any result exceeding the 4 MiB wire bound returns explicit READ_LIMIT; append still retains its metadata receipt, and no successful history is truncated. This count/byte bounded interface does not introduce pagination or reinterpret AppliedSeq as a remote cursor.

Native canonical payload/observed-set rules remain unchanged. Incoming payload bytes and observed order are copied without JSON/Unicode normalization; canonicalization remains the primitive's responsibility. Outgoing claims retain native-derived authors. Both RPCs stay outside the anonymous and Limited allowlists; existing Full local gRPC authorization remains in force and JsonAPI scope receives no new method access.

Swift's existing `Invocation.swift` throws `result.error` and discards the rest of an error response. Future App integration must use a receipt-preserving adapter, validate response version/disposition/issues, mask private request/response logging, and keep partial durable success distinct from projection/current-account failure. This stage does not modify that generic wrapper or bind the App.

## Exact generation

Inputs are separate from the stable private-registry inventory. `rpc/heart-rpc.patch` changes only two schema files on Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`; the dedicated mapper/tests are three new Go overlays. `rpc/heart-rpc.json` pins their hashes, the existing registry inventory, the schema patch, compiler and generator.

Generation runs on Ubuntu because the official protoc ELF uses `/lib64/ld-linux-x86-64.so.2`. The reviewed public [protoc v21.12 release](https://github.com/protocolbuffers/protobuf/releases/tag/v21.12) asset is pinned by archive SHA-256 `3a4c1e5f2516c639d3079b1586e703fc7bcfa2136d58bda24d1d54f949c315e8` and executable SHA-256 `e6a75cf6660945fbfec0d321808442ce3649cd7820079eece1098c881b315f55`. The asset and ELF metadata were verified in memory without execution on Windows.

Go 1.26.5 builds the same custom gogofaster replacement already pinned by Heart: `github.com/anyproto/protobuf v1.3.3-0.20240201225420-6e325cf0ac38`, with exact module/go.mod h1 sums. The runner uses the existing GOGO naming, gomobile-context and gRPC-no-error flags. It hashes the full transitive .proto input closure and only regenerates `pb/commands.pb.go`, `pb/service/service.pb.go`, and `clientlibrary/service/service.pb.go`. Generated outputs are not hand-written and are not exported as source artifacts.

The native test phase keeps the existing pinned Go/musl image, Tantivy archive and temporary genproto replacement. It verifies all composed source/module hashes before and after execution, compiles the generated gRPC package, and runs the exact new core/actual gomobile-byte tests. Process launch, bounded cleanup and fsynced logs reuse the existing tested lifecycle controller. Explicit SIGTERM/SIGINT handlers enter that cleanup path; repeated cancellation cannot interrupt cleanup, and cancellation during final receipt writing still durably records CANCELLED while retaining completed command outcomes. Original signal handlers are restored. Receipts retain exact source/run identity and remain failure/NOT_RUN if bootstrap or any required case is missing.

## Validation at source handoff

- Three newly authored Go files were parsed/formatted by gofmt over stdin. No Windows compiler, cache hydration, Heart write or source generation ran.
- Six focused Python controls passed on Scratch Linux: required method/package evidence, failure/skip rejection, exact protobuf import closure hashes, safe inventory paths, actual SIGTERM cleanup of an owned process group with a TERM-ignoring descendant and an untouched unrelated process, and actual SIGTERM during final receipt writing. The signal controls verified CANCELLED/finished_at, restored handlers and preserved completed command logs/results. Python parsing, shell syntax and workflow YAML parsing passed.
- The schema/mapper/roundtrip test source received independent read-only review. The final native-error delta preserves metadata and removes Resolution payloads; successful/collision cases still prove complete variants and native author mapping.
- Generated protobuf, compiled native RPC and account-wire execution are **NOT_RUN**. The previous real typed-account proof at run 44247736314 does not apply to this new boundary. Two App clients and iOS remain NOT_RUN; App capability remains OFF.

The reusable workflow is `pinkha-t2-native-rpc.yml`; the parent owns any integration dispatcher route. Raw evidence is limited to the runner's logs/receipts and toolchain metadata, with 14-day retention. No account is created in this first RPC lane.

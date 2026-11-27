# Heart cutover: canonical Swift wire and owned client

## Qualified result

The isolated Oracle Swift 6.4.3 run completed on 2026-11-27 at 11:36:53 UTC. All **17 XCTest methods passed, zero skipped**. The single owned compiler/test command exited normally with code 0; no signal, forced cleanup or residual process group was observed. The controller took 137.65 seconds and the Swift command took 109.475 seconds. This qualifies the canonical generated wire, request ownership, cancellation and durable acknowledgement boundary on Linux.

The exact original PASS receipt is `evidence/client-physical5-receipt.json`, SHA-256 `caae8ef5c4056a0b3137b07f35093297414a450259f19dc44d1fab75b1554fe3`. The original XCTest log is `evidence/client-physical5-original.log.gz`, SHA-256 `62a9e4430e3f58c37c1ff8af426a3034257faadd54fb9abeb594fc62528cc0d5`. It contains the exact 17 started and passed method events and the suite result. The requested `tests.xml` was not produced; the separately retained `tests-swift-testing.xml` is ancillary and does not establish these XCTest results. Acceptance uses the original log, normal process completion, zero skipped/failed events and final input equality.

## Delivered behavior

`PinkhaHeartCutoverClient` exposes the five original native operations: source read, cutover read, metadata append, import and association append. Every dispatch binds the exact account/Space lifetime lease and a coherent native runtime profile. The profile must contain the full source manifest identity. Requests are frozen before ownership transfers to the asynchronous native operation.

The three write operations distinguish not dispatched, uncertain after dispatch, and a received native receipt. They preserve a validated committed change ID and the complete native issue set when a post-commit error occurs. Malformed or oversized replies after dispatch remain uncertain; the client never infers zero effect or retries automatically. A late caller cancellation or retired owner withholds private resolution while retaining only the acknowledgement bound to the original author, operation and payload digest. Native change IDs must have the canonical CIDv1/dag-cbor/SHA2-256 representation; arbitrary text cannot cross that fence.

Two interoperability methods decode the exact frames retained by the already-qualified native RPC/crash proof and recompute the identities of every captured signed claim. These are actual captured native bytes, not newly manufactured fixture replies. The other 15 methods exercise the five dispatch methods, authority/runtime changes, exact frozen ownership, cancellation before and after handoff, response corruption, invalid/foreign claims and acknowledgement privacy. The receipt lists every method.

## Canonical source and dependency closure

The generated additions are `Anytype_Rpc.Pinkha.swift`, `Anytype_Rpc.Pinkha.TorahOperations.swift` and `pinkha_torah_cutover.pb.swift`. Existing protocol bodies are retained. Generation used the pinned canonical protoc and SwiftProtobuf 1.32.0 generator; its original ten-command receipt is `evidence/generation-receipt.json`, SHA-256 `2ff5021a3795448300a5062f474e3bdc40d8925382831fd4f3eef9548a2304a5`.

The client qualifier checked 246 source rows, the complete 247-file isolated package, original and copied native frames, 568 reused compiler files and modes, and the complete pinned dependency trees before and after execution. SwiftProtobuf is `c6fe6442e6a64250495669325044052e113e990c`; Crypto 3.12.3 is `e8d6eba1fef23ae5b359c46b03f7d94be2f41fed`; ASN1 1.7.4 is `917b472dbe53ba699cbb0495f9a95a084bc6364d`. Crypto compiler products were reused from the exact independently qualified C producer. ASN1 source was pinned; this does not assert reuse of an ASN1 binary.

`evidence/retained-dependency-products.json`, `dependency-before.json`, `source-inputs.json` and `package-before.json` retain the complete provenance and byte identities. `product-identities-after-pass.json` is a subsequent read-only identity capture of the accepted test runner, shared object and module object; it is not another execution.

The native source base and the core40/RPC11 overlay remain those published in `834a6bced7b922a18f291add1bcc6e82d5bba61f`. Their actual core, five RPC, real SIGKILL/two cold-process recovery, four signed-host and generated-byte results are reused with their original source qualifications. They were not replayed for this Swift delivery.

## Preserved failures and resource allocations

Every original failure remains a failure. Physical1 exposed an incomplete isolated declaration closure; physical2 exposed a Swift catch-variable shadowing error. The exact precursor sources and focused corrections are retained. Physical3 stopped at the original 128 MiB allocation; physical4 stopped at its separately reviewed 192 MiB allocation. Neither reached the test gate. Both owned groups were closed and final source/dependency equality was checked.

Physical5 used a fresh output directory and an explicitly reviewed 320 MiB build allocation with the same 64 MiB evidence allocation, 17-method inventory, zero-skip gate, 900-second command ceiling and original 2 GiB root/512 MiB development live floors. No failed partial products were reused. Its measured build peak was 295,899,136 bytes. All four original FAIL receipts, their logs and the two closed-input checks are retained beside the PASS evidence.

## Wave3 integration boundary

The guarded `PinkhaHeartCutoverNative.swift` factory calls the five generated `Lib.ServicePinkhaTorahCutover*` byte methods directly and reads the original runtime-version endpoint. Private native frames bypass the generic invocation body logger. This factory is **source reviewed, not Apple compiled** in this delivery. Its source is excluded from the Linux 17-method qualification because that package has no Apple `Lib` framework.

`ProtobufMessages.Package.cutover.patch` is a separately reviewable integration patch against the recorded original package source. It adds only the opt-in `PINKHA_NATIVE_HEART_CUTOVER_V1` define together with the existing authorized-read flag. Wave3 must apply the equivalent narrow change to its current package, build the matching native framework and generated bridge, compile the Apple factory, and supply the exact coherent runtime/source profile. This delivery does not edit the integration branch, current App code or Wave2's association repository.

The package patch uses zero context so the source artifact itself passes the repository whitespace gate; apply it only after comparing the base source (`ff7f520a6b304f9046e88ea26b710ca8e86e7ea134c8ae5ba0e1dad4e049b0a5`), using `git apply --unidiff-zero` or the equivalent reviewed edit. The exact full-context patch and four focused source-review diffs are retained losslessly as gzip files, including their original whitespace.

The FullSpace index readiness implementation and its new read-only wire are a separate source tranche. Their pending native and Swift tests are not covered by this PASS and are not included in the qualified client manifest.

## Retained locations

Original runs are under `/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/successor-runs/`. `receipt-locations.json` binds every copied evidence artifact to its original path and SHA-256. The accepted physical5 products remain under `/mnt/development/projects/caches/pinkha-e-cutover-swift-client-physical5-20261127/`. The original retained native source uses the explicit physical location and custody receipt `331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772`; generic alias resolution is not source admission.

## Publication whitespace qualification

The ordinary publication gate initially rejected five tested Swift inputs: three extra terminal newlines and four trailing spaces on one closing brace in each of two canonical splitter outputs. The published sources remove exactly those 11 bytes. The whitespace-equivalence.json artifact records every offset, original and published hash, and verifies the exact inverse transformation. The three removed newlines follow the final #endif; the two generated files contain no multiline string delimiters and the removed spaces follow a bare closing brace before a newline. No source token or string payload changes. All five exact tested originals are retained under qualified-original-sources/ as lossless gzip files. The original gate diagnostic and pre-normalization delivery manifest are retained too.

The actual17 receipt continues to name the original tested hashes. The published module and test copies have the separately recorded whitespace-equivalent hashes; this is not a new test execution. Original diagnostic logs and the shadowed-source precursor are also gzip encoded to retain their exact bytes and whitespace. The quoted original log SHA is the SHA after decompression.

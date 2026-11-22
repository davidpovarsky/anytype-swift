# Coherent Heart read candidate

`r15-attachment-authorized-current-read-v1` is a separate candidate. The retained default runtime and both original candidate identities are unchanged. At this source checkpoint, native execution and Apple execution are **NOT_RUN**.

## Source boundary

The unchanged T2 generator first reproduces the qualified `69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67` candidate from native base `d98420b1113536afd08cde6de9a5816f6d27ffff`. Its 85 native files, four generated protobuf files, schema closure and original Go declarations must match the original qualified generation receipt.

The composer then applies the 52 disjoint current-read/r15 files qualified by run `44966862922`, patch `977f485e13892d259da5f47b9c96bdcf3b34b23defff25271b22af43ac91b9f9`, inventory `d7ff255272a947c008b2bbbf951fff863b4b2469a37954c60a7cc22b0fa8301f`. It verifies the archived 35 original evidence files before using that proof.

Two T2 entry files receive an explicit delta. Two new helper/test files are added. The resulting inventory has **139 paths**: the 137-path baseline union plus two additions. All 52 current-read files and the other 83 T2 files remain byte identical. No protobuf schema, generated binding, Go module declaration or existing default profile changes.

## Shared publication rule

The old T2 App lease protects target/private-history preparation. Preparation captures the same current App/Space/principal/ACL/head scope used by ObjectSearch and ObjectShow, then releases the old App lease and all private/object leases before returning.

Both the direct snapshot entry and the generated RPC entry finalize through the existing App → Space publication → ACL fence. A closed or replaced Space cannot publish while its cache is still being cleaned up. An active old read lease fails closed before any recursive App lock can be attempted. The RPC copies and validates the protobuf response before acquiring the publication locks. Context cancellation is checked again after waiting.

Only the exact typed native current-read errors map to existing T2 denied or invalidated errors. Failed finalization returns no snapshot. Ordinary provider errors and text that merely resembles a denial do not become authority evidence.

## Narrow execution selection

| Component | Selection | Status at source checkpoint |
| --- | --- | --- |
| New finalization component checks | 5 methods / 14 Go terminal cases | NOT_RUN |
| Changed T2 front-door guards | 4 methods / 4 terminal cases | NOT_RUN |
| New combined real-account journey | 1 method / 1 terminal case | NOT_RUN |
| Other original T2 components | 67 terminal cases retained at their original source | No re-execution selected |
| Original native publication locks | 2 original component methods retained | No re-execution selected |

The five new component methods use publication doubles; they do not prove native ACL behavior. The separate account method invokes the actual generated append/read functions on the same native App, account, Space, document and block used by the T5 query/Show journey. Owner and Reader reads must return exact signed bytes and provenance. After actual signed removal and read-key rotation, T2 must return typed denial/invalidation with no snapshot, and T5 must return its exact authority sentinel with zero query rows/total and no ObjectView. The real account must stop.

The copied T5 fixture body differs only by a helper name and three hooks after existing owner/cache capture, Reader downgrade unlock, and removal/key-rotation unlock. A source gate rejects changes to its original assertion body. The original fixture and receipts remain untouched.

The controller preserves and scans the original T5 observation, combined observation, three raw protobuf responses, process log and ownership receipt against both disposable-account secrets. Overall success requires all seven exact exports and their hashes. Partial failed attempts may withhold unscanned output.

## Execution and subsequent Apple admission

Route `coherent-heart-native` runs the original protobuf generator on the Ubuntu host, followed by the native proof inside the existing pinned Go 1.26.5 musl container. It reuses the same `.t5-cache` path and existing owned process runner. Compilation and actual test selection remain separate claims.

The resulting full patch, inventory and proof must be qualified before their hashes are frozen into the `COHERENT` runtime profile and the existing Apple builder/downloader/installer. This checkpoint does not admit an unqualified binary into the App.

This proof does not establish automatic T2-private-log materialization into the T5 canonical property, remote ACL transport, a network synchronization barrier, iOS acceptance or full migration.

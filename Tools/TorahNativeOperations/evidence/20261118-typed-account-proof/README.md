# Actual typed-handler account proof ? 2026-11-18

[Run 44247736314](https://github.com/davidpovarsky/anytype-swift/actions/runs/44247736314), attempt 1, completed SUCCESS on exact integrated source `189d8c6ff4376967ef22c1b58edd5e6f7670ea12` containing source commit `5083aa2e853132c49fa51454ba4cad258f308d60`.

The raw artifact 14402628407 was SHA-256 verified as `806182967137fd683c8792a8c5227a5ce93a462e587dfd88d91e85f9d22a7254`. Receipt SHA-256: `633e54623381e39c15cc3b304b463b974c92c229dba52813d6b16dbbe9918dfb`. Raw artifacts remain in GitHub; they were inspected in memory on the connected host. This directory contains sanitized metadata only.

## Observed execution

Two distinct native binaries ran four actual passing invocations of TestT2AccountLifecyclePhase. The processes were new-create 16040, new-reopen 16069, legacy-edit 16086 and new-recover 16104. Each had a distinct nonce and the same original disposable account root, account, Space, document, block and canonical private root.

The actual new-only helper SHA-256 `853e2ae1ce660e320929349bac4783905ef1e229309ee61dfebdebc41b6a4b65` and the other three fixture hashes were independently matched against Git blobs at the exact CI source. Fixture aggregate: `05280d61703b7749bdc086d0ce2d4c49d22a8cb8c39ed8a3e94cd33ce440e4cc`.

The initial phase required HasTree=false initially and immediately after absent-history read, unsupported-version append, missing-block append, and malformed-payload append. A valid typed append then created the native root and the sole operation. Native-author read, read version/limit rejection, identical retry and different-payload collision all passed. Read-before-retry recovered the original signed claim; retry/collision left the complete snapshot, heads and local watermark unchanged.

After real AccountStop and AppShutdown, each new-runtime phase exercised the typed read and append methods and required ErrNotLoggedIn with zero result. The final target/Space removal controls also rejected typed reads and appends. The legacy binary excluded the new helper and recorded UNSUPPORTED_LEGACY.

Exactly the original root and one operation, their signed byte hashes, one head and immutable state file survived every phase. The old runtime's ordinary document edit survived recovery. All eight private ObjectExport calls returned code 1 with zero Result bytes; all eight ordinary JSON/Protobuf exports were retained and hash-verified. Public search/show boundaries, target-orphan preservation and existing Space/projection cleanup passed. The evidence secret scan passed without uploading account keys or mnemonic.

## Scope

This is **PASS_ACCOUNT_SCOPED_TYPED_BOUNDARY**, in addition to the separately proven private registry/lifecycle boundary. It is not a registered protobuf/gomobile API test, a two-App-client synchronization result, or iOS acceptance. App capability remains OFF. The next registered API must preserve durable receipts across wire errors and continue using native account/ACL/target authority.

The preceding baseline export/component/registry proof remains unchanged in `../20261118-export-account-proof/`. Its 2 helper SKIP events belong to the separate component suite; this four-process account run had four actual PASS phase tests.

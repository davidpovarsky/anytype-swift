# Prepared full-tier file migration

This increment adds a native PREPARED route for file content larger than the original inline tier. It preserves the intended file row and encrypted content root across a lost acknowledgement, account restart, concurrent commit calls and an actual process kill.

## Sources

The source manifest records the exact SDK and Any bases, commits, file digests, and replayable Git patches. Applying each patch to its base in a separate Git index must reproduce the committed tree exactly. The Swift implementation is delivered directly in PinkhaAnyHost and PinkhaAnyEngine.

The existing generic migration file capability remains zero. The new file capability is separate: 4,096 through 536,870,912 bytes, one original file, no generated variants. The original inline tier keeps its independent contract.

## Native protocol

Preparation validates account, writer, owner, immutable plan binding, declared size and SHA-256 before publishing content. A durable draft reserves a random encryption key before reading the content. A retry must match the same immutable specification and uses that original key. The existing UnixFS/CAR format stages the exact encrypted payload locally without registering a file row, reference, deduplication entry or upload queue item.

An owner-bound durable pin prevents offload and deletion while the prepared payload is awaiting adoption. The CAR, containing directories and database are synchronized before returning the prepared receipt. The subsequent native ledger entry reserves the signed payload change and file row identifier. Neither a host receipt nor an app restart regenerates them.

Commit reconciles the actual native history before changing anything. It advances the original derived payload root and original row. Native writer, ACL, owner and carrier checks protect each append. A deleted or modified original row is terminal. Local adoption occurs while the current owner and exact row remain locked, then records its durable marker and releases its own pin. Repeating commit does not create a second row or CAR. Receipts distinguish the committed row from local payload completion; they never claim remote replication.

The HTTP prepare endpoint accepts application/octet-stream and exact Content-Length. Small bounded metadata travels in the X-Pinkha-Migration header. Only this named route bypasses the ordinary JSON body cap. The Swift client first makes a private, verified file copy with bounded memory, then uploads that file. Authorization and account identity are checked around the operation. Status reconciliation precedes retries.

## Verified acceptance

The adjacent verification receipt records raw log hashes and actual named terminal results:

- Four file-store component tests, including real 2 MiB encryption/readback, pin ownership, durable restart and adoption retry.
- Three production Any SDK tests, including real 2 MiB prepare, SDK reopens, four concurrent commit callers, full file readback, bad-body recovery, changed-owner refusal, and a child process killed with SIGKILL before reopening the account and committing the original receipt.
- Two HTTP tests, including seven metadata parser cases and real 2 MiB streaming through the production server middleware.
- Four Swift Host receipt/reconciliation tests and one Swift Engine private-copy test.
- One existing 4,095-byte inline-file native regression, rerun because the shared native commit guard gained a separate full-tier mode.

These results cover local prepared file migration. They do not prove network durability, arbitrary file sizes beyond the declared limit, a power-loss scenario, Apple artifact inclusion, or whole-Space semantic completeness. Those require their respective acceptance evidence. The dedicated Apple artifact must be rebuilt from these pinned Go sources before an iOS acceptance can use the new endpoints.

## Reproduction

Apply the patches only to the exact source bases in source-manifest.json. The Any checkout retains its existing local SDK replacement; point its .runtime-artifacts/sdk-source at the patched SDK checkout. The isolated local configuration in the native tests targets disposable local fixture services.

Focused selections:
- SDK: go test ./internal/files/upload -run '^TestMigrationPreparedFile' -count=1 -v
- Any: go test ./internal/pinkha/migrationnative -run '^TestPreparedFullFile' -count=1 -v
- Any HTTP: go test ./internal/server -run '^TestPreparedFullFileHTTP' -count=1 -v
- Swift Host: swift test --package-path Modules/PinkhaAnyHost --filter NativePreparedFileMigrationTests
- Swift Engine: swift test --package-path Modules/PinkhaAnyEngine --filter AnyHTTPPreparedFileTests

Use the source-pinned Go versions and serialized build resources recorded in the verification receipt. Keep original logs and failed attempts; successful compilation alone is not acceptance.

# Actual signed revocation: native cached data remained readable

Run [44961084863](https://github.com/davidpovarsky/anytype-swift/actions/runs/44961084863), attempt1, at App source `cce67545ec284aed02c36314eeb7b41c582a3128` executed exactly one native method: **0 PASS, 1 FAIL, 0 SKIP**, 1.46 seconds. Compilation completed. The failed acceptance result is retained without relabeling.

The disposable native account created a real source-associated document and populated the real native query/index and object cache. Both the original owner and its subsequent Reader membership returned the expected canonical row and body. Actual signed ACL add, ownership transfer and removal were validated and delivered through the unmodified native updater, rotating the read key.

After removal, the same engine account had current permission `none` and retained only historical read membership. `ObjectSearch` nevertheless returned success with one row and total1; `ObjectShow` returned success with an ObjectView payload. This establishes a current-authority enforcement gap at those native cached read boundaries. It is not a fixture compilation or setup failure.

The test's denial assertions remain unchanged: a removed account must receive an explicit native error with zero rows, zero total and no ObjectView. Empty success does not satisfy the contract. AccountStop and shutdown were verified after observation.

## Preserved originals

Artifact14729761820 contains140176 bytes; its GitHub SHA256 `0b5d456f7b5b03a8873771802aec4d80f904ad67386c4e7b4ab280f5a790c5ba` was verified before reading. The original archive remains on GitHub and in the owned worktree's `build/t5-signed-revocation-44961084863/` directory. Eleven selected originals are stored byte-for-byte under `original/`; `QUALIFICATION.json` records every hash and size. Git text conversion is disabled for those bytes.

The controller's original export confirms the exact account-secret scan before publishing these files. No private wallet inventory or database was exported. Native source and controller inventories before/after are preserved. The exact corrected r15 attachment/runtime composition is recorded in the original build and runtime receipts; no product code was changed for this failing observation.

## Next bounded correction

Add a common native current-authority read fence for query and show, using the actual Space-owned ACL identity and current signed permissions. Preserve the owner and Reader controls, the ordinary native updater and the exact denial assertions. Keep original runtimes/evidence immutable and qualify the correction as a separate source variant. Typed permanent denial must also retire cached related rows in the shared presentation layer.

This proof covers local delivery of genuine signed ACL changes. It does not establish network transport, unknown remote/offline revocation, Any engine parity, Swift/iOS UI rejection, or full T5 acceptance.

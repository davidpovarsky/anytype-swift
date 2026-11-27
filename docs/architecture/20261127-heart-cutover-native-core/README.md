# Heart cutover: actual current8ac core registry accepted

## What this qualification establishes

On 2026-11-27 the actual Heart middleware, object factory, native source/type registries, shared account application, signed metadata tree, and existing v1 association tree completed one real local-account cutover. The test preserves two complete facts from the exact retained property. It creates four signed metadata records, two actual signed v1 imports, then an ordinary signed unlink. It stops the account, refuses access while stopped, selects the retained account, and reopens the same signed state.

The final execution is `TestPinkhaTorahCutoverActualCoreRegistryAndReopen`. Compilation took 175.146 seconds; the executed test command took 9.029 seconds. The test runner observed exactly one run and one pass, no skips/failures, and an actual package pass. This qualification is bounded to Linux ARM64 and same-process account retirement/reopen. New-process crash recovery, generated RPC execution, peer transport, Swift bridge activation, and Apple/UI acceptance are separate gates.

The immutable native baseline contains all 4,868 files from source manifest `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`. The 40-file tested overlay is declared in `Tools/TorahNativeOperations/legacy_cutover/native-core-current8ac-qualified.json`. The complete pre/post source inventories are equal. No App or XCFramework was built, and no existing application capability was enabled.

## Actual failures and narrow corrections

The first actual compiled run rejected the fixture's invalid object type key. The fixture now obtains `ot-page` through the production unique-key constructor. No acceptance assertion was removed.

The next run exposed a production panic in `ObjectFactory.New`: the factory called `sb.Type()` before `Init` assigned the SmartBlock source. The branch now uses the already-authoritative `sbType` parameter. Existing v1 and cutover object construction both execute through the same factory.

A subsequent full run reached final account reopen and older-writer divergence, then exposed an idempotency error: an exact retry returned its earlier durable receipt even though the retained property had since changed. Both metadata append and v1 import/association append now reject divergent/conflicting source state before idempotency lookup. This check does not reject an unchanged frozen import merely because a valid Seal followed its original commit. Current account, ACL, target, exact source, and retained receipt checks remain enforced.

The final test additionally requires explicit `ErrLegacyChanged` refusal and empty write results for metadata Begin retry, v1 import retry, and the retained unlink retry after source divergence. A subsequent complete read must be exactly unchanged.

The retained original read-authority adapter also delegates to the existing closed native ACL role policy while the caller holds the ACL read lock; it introduces no new permission rule.

## Evidence and exact integration inputs

- `original-receipt.json`: unchanged controller receipt. SHA256 `cd70d52b57795cab7ad6b94f396177213ba140d6e7cf31f14aed93fe5b897b82`.
- `original-proof.json`: unchanged nonsecret native assertion proof. SHA256 `674c67e4837217686bcdc0c8ecc116212baeedbf323a8e5180aa8dd28d4475b1`.
- Test binary SHA256: `2c3481861959cbb26f486617c25709e5781575b574593349dedc5fac0f55811f`.
- Original test log SHA256: `8be39b75d2414543d649f2db8c3ed572ec99fcfcecc4307d54119efad9cba486`.
- `current8ac-native-core.patch`: exact 40-file overlay against the original 8ac native archive; SHA256 `8064231fada75e7a16ef54cf8314a80bb2e9eaade7eb2352423c3cbf4cba2501`.
- Qualified overlay manifest SHA256: `0ea2bbfff9fd1faef02337ae247bb6706c5517c971d1346b762467b854782a20`.
- `evidence-index.json`: original Oracle paths and hashes for receipts, original failing logs, accepted logs, and bounded reproducible-cache reclamation.

The patch was independently checked, applied to only the exact original native files, and every resulting file was compared by size and SHA256 with the tested overlay. Its old-source identities are admission conditions. Do not apply it over a different native generation without reviewing overlapping files and producing a new coherent manifest.

Original private accounts, all binary products, source inventories, and full logs remain under `/var/tmp/pinkha-e-cutover-current8ac-20261127/attempt6`; no account credential is included here. Original failed attempts 2, 4 and 5 remain retained, with their unchanged receipts copied here.

The actual compile reuses the qualified Go 1.27.4 toolchain, Tantivy archive, full module checksum superset, and previously executed Swift shared source fixture. Their identities are in the manifest. The frozen source in `attempt2/source` remains unchanged; `continue_current8ac_core.py` uses an explicit five-file Go overlay.

The historical `native-core-current8ac-candidate.json` remains an unchanged record of the pre-runtime candidate, not the current acceptance manifest. Its original preparation controller intentionally rejects modified candidate sources. Use the qualified manifest/patch for integration, or the retained immutable source plus exact continuation overlay for reproduction.

## Retained acceptance boundaries

The test also asserts that missing-source reads and omitted-fact submissions create no native roots; two incomplete seals are refused; all original source bytes remain; exact frozen retries retain physical identities; final unlink preserves the seal; and the ordinary v1 reader remains compatible.

Existing signed-host, source-lease, SQLite/crash, source coverage, and shared Swift planner evidence is retained separately. The four native-host tests affected by the new source-currentness check are queued as a focused regression gate with the generated RPC qualification. Their older pass results alone are not asserted to qualify the changed host code.

Wave3 owns the final integration branch and application/native packaging. This commit changes only the isolated native overlay and its evidence. Wave2 owns UI/gesture completion.

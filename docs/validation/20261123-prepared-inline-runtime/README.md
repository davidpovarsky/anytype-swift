# Apple prepared inline-file Runtime candidate

This additive candidate registers exactly one new XCTest only when `PINKHA_ANY_NATIVE_ARTIFACT=verified-prepared-inline-v1`. Its linked build case is `pinkhaPreparedInlineMigrationCandidateV1`, with exact native version token `v0.5.0-pinkha.prepared.inline.1`. Existing upstream, native, prepared-object and authorized-read selectors retain their previous defines and behavior.

## Actual journey to be executed on Apple

Selector: `PinkhaAnyRuntimeTests/AnyPreparedInlineFileRuntimeTests/testManagedInlineFilesSurviveOrderlyReopenWithExactNativeBytes`.

The actual managed C runtime creates a new account, one disposable Space and two native owner objects through the public prepared-object client. The ordered file cases are empty content and 4,095 deterministic bytes, each bound to its own owner. Both plans are prepared before the first orderly native stop/reopen. Their signed payload identities and original prepared state must survive. The public inline-file client commits each original plan, reconciles current status and repeats the original commit. Ordinary native metadata, status and raw content must match the original input exactly. A second orderly stop/reopen repeats status, retry and native readback.

Two distinct native owners are required by this fixture's ordering: each plan freezes its carrier head. Preparing two files on the same owner before committing either would allow the first payload to advance that carrier and correctly obsolete the second plan. This fixture preserves the native dependency fence. It does not declare payload roots globally unique for every file.

Exactly three distinct runtime generations and three distinct application owner generations are required. The account, Space and native store identity remain the same. Public account checks and application owner leases guard the test-only managed binary read. Redirects are rejected. Cleanup drains the application owner, deletes the owned Space, signs out, stops the native runtime and removes its owned temporary data directory.

## Evidence contract

Attachment: `pinkha-prepared-inline-file-runtime-proof.json`, bounded to 65,536 bytes.

The adjacent `observation.schema.json` is the success qualification shape; incomplete failure attachments intentionally fail it. A controller must additionally verify the original actual passing XCTest, exact run/source/attempt/nonce binding, native manifest/build lineage, deterministic fixture bytes, cross-field native identities and exact generation phase membership. Observations alone never establish acceptance.

Schema SHA256: `19b0a8a98a0ecc6495e6be6048860d7f6307ae23f39786a4c90ed2ef8e7b6d9e`.

The controller supplies four values through the generated xctestrun descriptor's TestEnvironmentVariables:

- `PINKHA_PREPARED_INLINE_APPLE_SOURCE_SHA`: exact 40-character lowercase source SHA.
- `PINKHA_PREPARED_INLINE_APPLE_RUN_ID`: positive canonical decimal run ID.
- `PINKHA_PREPARED_INLINE_APPLE_RUN_ATTEMPT`: positive canonical decimal attempt.
- `PINKHA_PREPARED_INLINE_APPLE_NONCE`: fresh 32-character lowercase hex nonce.

`identity.ownerObjectIds` contains exactly two distinct actual native owner IDs. Ordered `files[i].ownerObjectId` must equal that entry. Each file records seven receipt observations and two ordinary readbacks. Secret authentication responses, mnemonic and managed control token never enter the attachment.

The native manifest SHA256 is `86598a7046ef135fa5dd2d0c2e559750f89ed8517fe4c1c753ce4457c13a009b`. Deterministic content, Unicode filename bytes and expected hashes are in `deterministic-fixtures.json`.

## Verification performed on Oracle

`static-checks.json` records syntax validation of the active new XCTest and evaluated SwiftPM defines for all five supported selections. Existing prepared XCTest bytes are unchanged. No passed product suite was rerun. Oracle is Linux; these checks do not establish Apple typechecking, native linking, simulator execution or acceptance. Those remain the separate controller's actual build and single XCTest.

The proof explicitly limits its claim to an orderly native store reopen within one XCTest process. OS process crash, lost HTTP acknowledgement injection, network synchronization, transient SSE delivery and full-Space migration are not established.

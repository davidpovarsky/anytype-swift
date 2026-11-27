# Proposed explicit attachment storage-tier projection

This is a source-bound proposal, not an implemented or executed correction. The current App source is `AnyNativeAttachments.swift` SHA `75cac2b2b7ffe0d84e0f461d80c94e3be48d804896170a2b67e895e006977631`, published in `2f9ac20a910d9922e13f8e5d410757604437fcc5` and preserved unchanged in the bridge child `bd684a8ad5b12cc2eef3b14d4fb64a34bd98f304`.

## Exact source evidence

W1 HQ comment `1220953422154846` records source verification against complete native manifest `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a`, original Any base `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` / SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`, in the retained native0796 lineage. This is a source-contract boundary, not current App or native8ac binary acceptance.

The retained primary files independently match their exact lengths and hashes:

- `internal/api/files.go`: 4,489 bytes, SHA `c9aa3e006f8fcc24bd129fbe9e41eabe7bd6b3d3c3675125370d83d75ddf65ea`. `inline` is a required bool with no `omitempty`. `rootCid` is an optional string. Inline files have empty root CID and are cached/durable by construction.
- `internal/server/handlers_files.go`: 23,427 bytes, SHA `a7e299282612adcdb76f2b8f3c64553a92770edcf6ba2bab4ab91e3bb9786658`. Attach, get and list use the same `fileInfoToAPI`, copying all eleven FileInfo fields. The list uses typed FileInfo rows, not the different cleartext query projection.

The owner's same comment binds the actual SDK row conversion: `Inline = row.Inline()`, `Durable = Inline || networkSign != ""`, and `Cached = Inline` or a complete local full-tier copy. Full-tier availability and backup state can change legitimately. The two Go files were read locally from Root's primary readback; the SDK conversion statement is attributed to W1's exact-source report, not a claim that this lane fetched those SDK files.

## Confirmed current gap

The row value does not retain `inline`. Its initializer ignores a missing/wrong-typed inline field and does not reject contradictory root/tier/cached/durable combinations. `sameContent(as:)` consequently omits the tier, and the final Host-to-list reconciliation before pending-intent removal also omits explicit equality with `AnyNativeAttachedFile.inline`.

Current `rootCid` extraction also turns a present wrong type into nil. Once tier consistency is checked, absence and a malformed present value must remain distinguishable.

## Minimal proposed product delta

Keep the existing file and initializer signature. Add only:

1. A stored `inline: Bool` value and required `.bool` decoding; missing/null/number/string are errors.
2. A present `rootCid` must be a string. Preserve the existing optional representation and raw string; add no CID parser, character normalization, fake workspace, new scoped reference, or Native API.
3. Structural tier checks: inline requires an empty/absent root CID plus `cached == true` and `durable == true`; full-tier requires a nonempty root CID. Full-tier cached/durable combinations remain otherwise unrestricted.
4. `inline` equality in the existing `sameContent(as:)` comparison. Keep changing cached/durable flags outside content identity so valid download/backup progress does not invalidate a metadata bracket.
5. `row.inline == file.inline` in the existing `requireReturnedFile` guard, preserving every account/Space/object/file/size/name/MIME/root comparison and both success-only pending-intent removal sites.

This does not change variant/variantOf policy, original-file selection, content transport, retry/status routes, MIME/name normalization, preview, MiniApps, permissions, journal/factory ownership, or recovery behavior. It does not copy the Host's Native metadata parser into UI. Native cryptographic content verification remains with the existing engine/Host.

## Focused test source

Use the already-bridged `AnyNativeAttachmentMetadataTests.swift`, not a new source or target. Its existing row fixture gains the real required `inline: false` field; the original three test-method bodies and thirteen argument cases remain unchanged.

Append only two actual-row tests:

- Valid inline/full-tier rows, existing missing/empty metadata behavior, retained raw root representation, and stable full-tier content identity while cached/durable flags progress.
- Finite malformed cases: missing/null/wrong-typed inline; inline with nonempty root, false cached, or false durable; full-tier with missing/empty root; present null/wrong-typed root.

Expected addition: two methods / eleven declared cases, giving this existing metadata suite five methods / twenty-four declared cases. This is a proposed declaration count only; no compiler, enumeration or runtime result exists. The already-published bridge remains two source paths; changing this file's hash requires a fresh exact App/consumer source qualification, not an extra source-count claim.

No test-only access to the private Host reconciliation method is proposed. The one-line consumer equality remains source-reviewed and will be covered by the later genuine mounted upload/reconciliation fixture. No simulated Native receipt or new production observer is introduced solely to assert that line.

## Separate transport boundary

W3 HQ `1220953721620190` independently identified the inherited e96 transport completion gap: `AnyNativeFileUploadResponse.finish()` requests cancellation/invalidation and resumes its continuation before any later delegate termination barrier is proven. The current UI/recovery claim joins the original Swift operation; it is not proof of URLSession or Native quiescence. W1 owns the transport/account-handoff correction. No UI workaround, duplicate journal, guessed ACK recovery API, actual late-write assertion, or duplicate-POST assertion is part of this proposal.

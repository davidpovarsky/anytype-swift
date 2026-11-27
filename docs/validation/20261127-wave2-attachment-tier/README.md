# Native attachment storage-tier projection — source candidate

This separate two-source correction is based on the owned bridge commit `bd684a8ad5b12cc2eef3b14d4fb64a34bd98f304`. It changes the existing attachment row and metadata test source only. It does not provide a new App build, Native receipt, test enumeration, runtime result or visual acceptance.

## Problem and resulting behavior

The typed FilesV2 list/get/attach contract requires `inline`. The previous UI row discarded it, accepted a missing or wrong-typed value, and omitted explicit tier equality from the final Host-to-list reconciliation before removing a pending caller intent. A present malformed `rootCid` was also treated as absence.

The row now retains and requires a Boolean `inline`. A present root value must be a string. Inline rows require an absent/empty root and actual cached/durable flags; full-tier rows require a nonempty root. The original optional raw root value is preserved. This is a structural projection of the published contract; it introduces no CID parser or Native addressing policy.

Content identity now includes `inline`, and the existing final reconciliation requires `row.inline == file.inline`. All existing account/Space/object/file/size/name/MIME/root checks and the two success-only caller-snapshot removal sites remain. Changing full-tier cached/durable flags stays outside content identity, because download and backup progress can legitimately change those flags.

## Exact source and contract evidence

`candidate-manifest.json` binds the two full original and candidate files. `source-inverse.json` restores both original files byte-for-byte. `source.patch` contains the complete product/test delta; `prepare_candidate.py` is the exact local deterministic materialization script, not a test or runtime runner.

The contract inputs remain the original typed Host/Engine e96 source already retained by the upload/metadata tranches, plus W1 HQ story `1220953422154846` and the primary original files `internal/api/files.go` SHA `c9aa3e006f8fcc24bd129fbe9e41eabe7bd6b3d3c3675125370d83d75ddf65ea` and `internal/server/handlers_files.go` SHA `a7e299282612adcdb76f2b8f3c64553a92770edcf6ba2bab4ab91e3bb9786658`. The same converter supplies all eleven FileInfo fields to get/list/attach. The SDK row-conversion detail is attributed to W1's exact-source report; this lane did not execute that Native implementation or independently fetch those two SDK files.

`caller-search-proof.json` covers all 71 Swift files in the exact current PinkhaAnyUI package tree: its Package.swift, 41 production sources and 29 tests. Matching retained bytes were reused; the other 32 files were read from the immutable base. The actual row type is mentioned only by its original production file and the existing metadata suite. No additional initializer fixture in that bounded module scope requires modification. This is not a whole-repository or actual compiler-closure claim.

## Focused declared tests

The original three metadata methods and thirteen argument cases retain their exact 4,167-byte prefix. Their shared valid-row helper gains the real required `inline: false` field.

Only two methods are added:

- `validStorageTiersRetainRawRootAndAllowAvailabilityProgress()` — valid inline representations, original fallback strings, raw roots and all four full-tier cached/durable combinations, including content identity across progress.
- `missingMalformedOrContradictoryTierMetadataIsRejected(invalidCase:)` — ten finite malformed/contradictory tier or root cases.

The resulting existing suite declares **five methods / twenty-four cases**. Every method remains **NOT_COMPILED / NOT_RUN** for this source. These are actual production-row value tests, not simulated Native receipts. The private final Host/list equality has no new test-only visibility seam; its mounted upload/reconciliation acceptance remains pending.

The already-published two-path test bridge remains unchanged. This tranche changes the metadata file's content hash, not the source-path count. W3 must bind the exact new App/test sources, the existing PBX/allowlist and actual consumed compiler inputs, enumeration and results. No package, PBX, origin allowlist, producer, controller, timeout, Native, Host or SDK source changes here.

## Remaining acceptance and separate ownership

Actual current Native/App binary compatibility, full Swift compilation, mounted list/open/upload/recovery, visual and physical-device acceptance remain pending. Variant/variantOf behavior, transport, status/retry, preview, MiniApps, authority and original journal ownership remain unchanged.

W3's separate inherited URLSession drain finding is retained in `w1-wire-and-transport-comments.json`. The upload UI claim joins the Swift operation only; this is not proof of transport or Native quiescence. W1 owns that transport/account-handoff correction. This tranche supplies no UI workaround and claims no observed late write or duplicate POST.

The earlier proposal and its not-implemented status remain preserved as historical planning evidence. The new candidate status is source preparation; only later reviewed publication and actual matching producer/consumer results can advance it.

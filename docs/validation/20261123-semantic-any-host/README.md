# Native Any semantic-anchor host preparation

This change integrates the existing downstream host candidate into
`Modules/PinkhaAnyHost` at base
`e7fd39b763d3d0244996c207552096f169de85ed`. It adds
`AnySemanticAnchorDocument.swift` and its original six XCTest methods.
The shared marker model, inline codec, association identity and resolver
already exist at this base and are unchanged.

## Behavior

`AnySemanticAnchorCapture` binds a user's selection to the original native
read, block payload, native version, engine run and application generation.
It prepares a text edit through the existing conditional-edit interface;
it does not dispatch a native write itself. Changed ownership, source
payload, scope, version, dataset or engine identity refuses preparation.
Readback requires the exact inserted marker, the same current owner/run,
and one unambiguous fragment.

`AnySemanticAnchorDocument.resolve` examines the complete current document
graph. An unreachable duplicate cannot be discarded to manufacture a
unique answer. Unsupported marker syntax refuses resolution. No saved
offset is used to search for a replacement selection after edits.

## Original execution retained

The original candidate and evidence were recovered from
`C:\Users\DAVID\AppData\Local\Temp\pinkha-semantic-any-host-7pj8ejll`.
Thirteen files were copied over the existing SSH connection to Oracle,
with SHA-256 and byte counts checked at both endpoints. No original was
deleted or rewritten. The exact transfer map is in
`ORIGINALS_MANIFEST.json`; `originals/**` has Git text normalization disabled.

The original Windows Swift 6.3.3 run executed these six distinct XCTest
methods successfully, with zero failures or skips:

| Method | Original duration |
| --- | --- |
| `testCaptureAndResolveRefuseUnsupportedNativeSyntaxInsteadOfRetargetingOffsets` | 0.024 s |
| `testCaptureRejectsExistingSameIdentityElsewhereAndUnreachableCopies` | 0.095 s |
| `testCaptureUsesExistingVersionRunCASAndPreservesExactInverseAndOpaqueFields` | 0.021 s |
| `testPrepareRejectsVersionOwnerRunScopeDatasetAndUnknownFieldChanges` | 0.048 s |
| `testReadbackRequiresExactMarkerFieldOneFragmentAndCurrentNativeOwner` | 0.084 s |
| `testResolveUsesCompleteCurrentNativeGraphAndReportsMissingAmbiguousOrForeign` | 0.035 s |

The later Swift Testing line reporting zero tests belongs to a separate
runner and is not counted as execution evidence. Original log SHA-256:
`2e38d8599176f0b45e542571004cd19569fdfe40c1db1f2de1960d4eb39c5b3a`.

The tests exercise received native-shaped records and the real host
preparation/codec APIs. They start no engine and make no HTTP request.
The original source archive is based on `edf1545f2ebcd1a71d307735a645c779cb9dc3bb`;
its pinned dependency identities and toolchain receipt are retained.

## Source equivalence and audit

`audit_original.py` reconstructs all 241 original source-map entries from
the unchanged baseline ZIP, candidate overlays and test harness. It checks
the before/after maps, original declared and executed test names, raw log,
dependency pins and the two integrated files.

All 239 original module files now present in this checkout match:
36 byte-for-byte and 203 with only the original Windows CRLF line endings
changed to the repository's LF line endings. There are no material source
changes. Both original and current hashes, and the exact equivalence type,
are recorded per file in `AUDIT.json`. This does not rewrite or relabel an
original digest.

Seven additive Swift files introduced at the current base are outside the
original execution. They comprise the prepared migration/archive additions
and already-existing semantic component tests. Their exact paths are
listed explicitly; the audit refuses an unexpected extra file.
Consequently the original six component passes are retained at their
actual scope, while a fresh full-module build remains unqualified.

Run the read-only audit from the repository root:

```sh
python3 docs/validation/20261123-semantic-any-host/audit_original.py
```

The integration and audit executed zero product test methods.

## Remaining acceptance

Current full-module compilation, Apple execution, actual HTTP/native
mutation, cold process reopen, mounted editor selection and physical
iPad behavior remain NOT_RUN for this addition. The original Heart Page
Apply/wire path is a separate uncompleted acceptance requirement.
No capability is enabled and EDITOR-02 remains open.

The next meaningful execution must connect this preparation to the
current native owner and conditional write/readback path, then verify
persistent resolution after real edits and reopen. It must retain these
six portable results where their tested dependency closure remains
equivalent; replaying them is not a substitute for the missing native
and mounted journey.

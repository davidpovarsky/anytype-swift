# Preserve exact bytes in Library Rename

**Source reviewed; four new Swift Testing methods / eight declared argument cases are NOT_RUN.**

Immutable parent: `9f0cbdffbda45520124ee1f0b50961641c5c49b1`, tree `dbe46fdd4128843bb3bb687bd00ae69d024f12b5`.
Owned branch: `codex/chatgpt-wave15-wave2-hierarchy-title-exact-20261127`.

## Problem and correction

The original hierarchy Rename operation uses canonical Swift string equality for its completed-retry decision, stale expected-title check and both normal/error readback checks. Canonically equivalent Latin NFC/NFD or Hebrew combining-mark representations can therefore skip an intended byte change, admit a raw-different expected title or certify a raw-different result. This is a proven source path; it is not a retained Native or mounted-UI failure.

Only four predicates inside `AnyHierarchyRepository.rename` change to `utf8.elementsEqual`. The complete original operation and all other methods remain intact: the shared mutation queue, title bounds, current membership, object/version/run/apply-sequence fence, authorization, patch, readback order and error handling are unchanged. Exact already-applied retries still avoid a second write. Ordinary creation comparisons and the unpublished Bookmark proposal are outside this correction.

## Exact modified sources

| Existing source path | Candidate SHA-256 | Scope |
| --- | --- | --- |
| `Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift` | `7a1af6090a300a17e1427abb97423a49fbd26031d0578d17e6cba5f719016463` | Four predicates; 22,565 bytes |
| `Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift` | `3a11428238fabc27fc93f8cfb98535864dfbb7c2b09ae501c14f699d47b292c1` | Append only; full original 30,174-byte / 23-method prefix retained |

The exact caller trace shows that the existing name form, pending dismissal submission, Library model and hierarchy presentation state forward the requested raw value without an earlier canonical-equality no-op. No UI change is added. `caller-source-proof.json` binds those three complete original bodies.

## Focused new tests

The separate private `AnyHierarchyRawTitleTests` suite contains four methods, each with Latin and Hebrew arguments. It exercises the actual repository and original conditional-store fixture: requested raw changes reach the modeled store once; a raw-different stale expected title is rejected before dispatch; a mismatching normal readback reports `incompleteWrite`; and a mismatching readback after a modeled lost reply preserves the original `writeUncertain` error. Exact returned/stored/requested UTF-8 arrays, dispatch count and captured fence are checked. An exact completed retry remains a no-op.

The controlled readback conformer delegates membership, captured-fence validation, modeled patch and readback to the original fixture. It is not a Native server or HTTP test. `declared-selectors.json` records the four declarations and eight argument cases; the complete file has 27 declarations. No compiled enumeration or actual result is claimed, and the original 23 methods are not selected for replay.

## Evidence and source review

`source-inverse.json` restores both complete original files, and `source.patch` shows the exact change. Both complete modified-file preimages, the three caller bodies and three relevant original Package/store prerequisites are retained once under `originals/`, with original paths and Git-blob custody in `primary-source-provenance.json`. Raw API envelopes remain local rather than duplicating all source text in this packet.

Root review `7e6600ae…` and Editor review `8ce9945c…` found no concrete source blocker. Editor byte inspection `563cdf22…` independently confirms the four bidirectional replacements and unchanged original test prefix. The retained candidate manifest still records its earlier pending-review preparation status; the two later review artifacts provide the source-review outcome. None of these records claims compilation or execution.

## Execution and integration boundary

The retained G04 Linux controller is a six-method/nine-case Kit lifetime-helper component, not an Integration dependency closure. Its owned-command and Swift Testing conventions can be reused only through a separately reviewed exact source/dependency/selection successor. The current original Integration Package depends on actual Engine and Kit modules. Both hierarchy protocols are declared in full HTTP-store production files; those files cannot be replaced by test stubs. `execution-readiness.original.json` preserves this scoped finding. A separate owner is preparing the targeted execution closure; this packet contains no runner or runtime admission.

Only the two existing Integration source/test paths and this evidence directory may differ from the parent. All unrelated files/modes, current 937a Property Unicode correction, Kit26, App/native source maps, Package/PBX, existing controllers, resource floors and final integration refs remain unchanged. W3 owns subsequent exact source and compiler admission. Mounted Rename, real Native/permission behavior, Apple UI/visual/device acceptance and Bookmark creation remain separate obligations.

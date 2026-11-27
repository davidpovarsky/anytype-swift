# Host exact Unicode text readback

Source-only successor over `2752229aacf72f468f32a4bfe5fe0a91142f5dbe`. Both independent reviews accept the frozen three-file candidate; compilation and execution remain pending.

## Corrected behavior

The original Host always dispatched the prepared text through conditional PATCH. Its later matcher used synthesized `AnyJSON` equality, allowing canonically equivalent, byte-different text to qualify a current receipt and Undo when the version matched. Only requested top-level string `text` now uses exact UTF-8. All non-text, non-string and unset comparisons, version/lease/account/Space/permission checks, transport and Undo construction retain their original source.

The separately reviewed UI flush already rejects byte-different final readback. This Host fix does not claim an observed wrong native save or UI acceptance; global JSON equality and the Native contract are unchanged.

## Focused tests

The entire original13,015-byte test prefix remains exact. New selectors under `PinkhaAnyHostTests`:

- `NativeTextEditReadbackHTTPTests/testCanonicalEquivalentTextReadbackCannotCertifyWriteOrMintUndo`
- `NativeTextEditReadbackHTTPTests/testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse`

These are **two XCTest methods/cases**, each looping Latin and Hebrew pairs, for **four controlled HTTP flows**. They invoke actual Host read/prepare/apply/read, `AnyHTTPClient`, original target/member validation and session lease. The negative response matches the version but retains old canonical-equivalent bytes; it must be unverified with no Undo. Exact reply must preserve verification and exact inverse/redo bytes. The fixture records real raw requests/replies and start/exit custody; no native server is used.

Only a newly created owned fixture directory is normalized to0700 before strict mode/type/owner checks. Bounded loopback traffic and owned stdin EOF are retained. Python was source-parsed only. Swift compilation, these tests, native storage/ACL, Apple UI and Native25 remain NOT_RUN.

## Review and integration

Root review00b80248 and peer review0e3f3916 cover the exact tuple in `candidate-manifest.json`. The initial reviewer digest stop and local83-YAML/84-directory-entry counting stop are retained; neither changed source or executed tests. W1 assigned W2 this exact matcher/regression in HQ1220956399195998. C will compose it once; structural editing/reversible topology remains W1/C-owned.

Publication contains only three source/fixture paths plus this new evidence subtree. Full preimages, inverse, prefix proof and workflow checks are retained. No source-gate execution, controller, compiler, Native/Apple action or product admission is claimed. Linux execution preparation follows separately under exact full-file/dependency custody; old component results and budgets do not count as this test result.

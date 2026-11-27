# Native source search: existing-query Retry

Status: **frozen source-only candidate; no compiler, test, Native or Apple execution**.

## Proven gap and exact preimage

At current shared App `919626d8a5a2701c2dfb56277a657fa593700b98`, `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift` has Git blob `1c7a14c636e2908012fdac88e1264f164d212b3e`, SHA256 `8a2a18ad56ac7fde85223bf24bc8c104204e2031eddf9548ad810832aa8a673f`, 35,813 bytes. A separate primary read of published `2f9ac20a910d9922e13f8e5d410757604437fcc5` returns those identical bytes.

In `AnyNativeSourceSearchView`, the error branch at original line539 is only a red error Text. Search dispatch at original lines590–592 occurs on query change, while the task at593 only refreshes associations. Therefore a failed unchanged query has no explicit Retry action on this new-engine search surface, shared by standalone and embedded Inspector search. The Heart counterpart already offers `Loc.Pinkha.Home.retry` invoking `await presenter.performSearch()`. Current required-coverage UI11 explicitly includes visible-error-retry-recovery.

## Minimal correction

Replace only the native error case with the same error Text followed by a native List Button using that existing localized label and shared presenter action. The candidate is35,988 bytes, SHA256 `beea22b4d19484f6dad508f819d874ece31d43a91d36fa0d03805c527c9332da`; the net change is175 bytes. The full offset/base64 inverse restores every original byte, including every other statement in the file.

No query, provider, context, identity, mutation, Inspector route, navigation, accepted test, selector, controller or runtime pin changes. The error remains visible. Retry uses the same query/scope and the existing loading/success/error transitions; it does not provision or persist an association.

## Existing guard boundary

The shared presenter captures a request epoch and checks the trimmed query and category before publishing. Its cancellation checks and each search view's existing onDisappear invalidation remain unchanged. The presenter owns a fixed context, and embedded search uses the document context. Existing Open/Link operations retain their own context/authority checks.

The provider-suggestion `session.search` itself does not validate mounted-document ownership. This presentation-only addition does not introduce or claim a new owner/cross-Space guarantee, lifetime fence or dispatch wrapper. `counterpart-proof.json` records the exact existing counterpart and guard bodies. Wider search lifecycle behavior is outside this tiny change.

## Verification and remaining acceptance

Only local source-byte, complete inverse and primary Git-blob comparisons were performed. No syntax parser/compiler, Swift Testing, XCTest, simulator, Native or host call ran. The first local preparation stopped on an incorrectly transcribed preimage checksum before creating the candidate; `preparation-attempt1.json` retains that failure, and final preparation uses the exact primary-bound hash plus the independently read own-base source.

The existing UI11 controlled provider-failure/retry obligation still needs an actual approved failure fixture and the matching shared App. A successful empty query is not failure evidence. No new test suite or controller is created here. Root independent review and exact publication remain required.

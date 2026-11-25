# Any MiniApps adapter candidate

This checkpoint connects the current native Any editor to the same Hanlin MiniApps Bridge, picker, result sheet, source-selection planner and operation confirmation used by the original app. The original Heart planner implementation was moved without behavioral changes into PinkhaHanlinUI; Heart native mark conversion and write/readback remain its own adapter.

The new Any adapter captures current account/Space/document, native source revision, real UTF16 selection and lossless inline Markdown. Existing native conditional edits preserve IDs, style and semantic markers; a synchronized private request/result-bound journal precedes every dispatch and final SDK ACK. New paragraphs and files use the existing native prepared-intent ledger rather than guessing lost auto-ID replies. Native file metadata and exact downloaded bytes are verified before a file result is acknowledged. Current native attachment rows are presented through authenticated private download and QuickLook, with no loopback credentials or invented attachment URI stored in a document.

An independently returned operation that differs from the requested operation requires an owned, cancellable confirmation. Source changes preserve newer content; partial conflicts remain pending instead of overwriting content or replaying the entire result. Account/engine transfer cancels and drains the actual Any presentation task; a callback selects an Any document only from the immutable original locally retained SDK request. Heart engine admission is held with a distinct transition token, independent of authentication holds.

## Qualification

The 11 changed/new Swift files pass compiler grammar parsing with PINKHA_DUAL_ENGINE_RUNTIME. The separate shared UIKit confirmation at e0ca39fb5840a944a625ae334d2532d99ac83e33 also passes actual Xcode27 Swift6 iOS27 typechecking (2.56s, empty original log). This checkpoint does **not** claim complete Apple typechecking, native MiniApps acceptance, independent companion round-trip acceptance, or app acceptance. It requires the parent Heart lifetime APIs and the C-owned authenticated native file reader to be merged before the combined build; both have explicitly coordinated ownership.

Original tests are unchanged. New scoped real-native acceptance must cover formatted replacement, newer-source conflict, prepared file bytes, duplicate return, stale owner and receipt-before-ACK. The final shipping commit will be recompiled with the exact reviewed single-runtime library and current published SDK.

# Original Any body acknowledgement metadata — source checkpoint

This checkpoint extends the bounded save-message metadata contract already published in `ca4d93e48dca616ab119739d71a1c4ffe7eddfa8`. Its integration base is `b2d3943c6650d2da49a9d70e032ec3a12fda13c5`. It changes three owned Swift files and adds this handoff plus the exact source intake. It performs no native operation and installs no production save action.

## What is retained

The new typed atomic acknowledgement preserves the actual native inserted, updated and deleted ID arrays in their original order, the unchanged count, the original request digest, native version digest and a canonical digest of that complete receipt. The combined admitted ID count is at most 64; each ID is at most 256 UTF-8 bytes and contains no control character. IDs must be disjoint across all three arrays. The original native conditional Markdown operation remains one effect; no per-block dispatch records are fabricated.

A digest-only acknowledgement cannot certify a body. When the original native acknowledgement exceeds this consumer's strict bound, its complete bounded native receipt can be hashed without truncation and retained as unresolved metadata. This does not authorize a retry or replacement page. The native root and original dispatch identity remain recorded.

Body verification requires the complete expected semantic body, the actual native ordered block references, the exact acknowledged version and the full admitted acknowledgement. For the newly created empty page contract, inserted IDs must be exactly the actual final body IDs, with no updated or deleted IDs and no unchanged body rows. The raw requested Markdown digest stays in the immutable manifest. Separate fields retain the actual same-version normalized native Markdown digest and UTF-8 length; no raw-byte-preservation claim is made.

Late receipt persistence may settle metadata after dispatch is closed. It never reopens dispatch, creates a new request identity or independently grants native authority. Existing ordered Heart metadata omits the new optional fields and retains its original wire shape.

## Ownership and next dependency

The protected journal remains owned by the SDK lane. Before any atomic save can execute, that lane must admit the new `atomicBodyReceipt` event with its own 64 KiB envelope and reserve a second 64 KiB event allowance only for conditional Markdown saves. Ordered-body budgets must remain unchanged. This checkpoint does not edit the journal, shared worker, original consent, router, catalog, engine, package pins, project, production factory or existing UI.

The qualified engine primitive is the original `AnyNativeMarkdownBody` at `2619d5b144b23eb80247df613d5d128aa2efbfb6`, already present on this base. Its component/native evidence is not Hanlin consumer acceptance. The new Any operation and runner remain in a separate later source tranche, after the SDK lane publishes its shared original authority and consent seam.

## Verification status

The intake records exact preimages, Git blob IDs, SHA-256 digests and literal inverses for every changed existing source. All 36 previously published state-test method names remain present. The original 23 pre-atomic state-test bodies are byte-identical; the existing atomic fixture cases now require full native acknowledgement and normalized readback metadata. Six additional state methods cover escaped maximum-size IDs, canonical replay, rejected malformed/over-limit groups, digest-only unresolved outcomes, late closed-dispatch receipts and native Markdown normalization.

There are 42 authored state methods. **All are NOT_RUN.** No Swift compiler, simulator, native account, HTTP writer, Mac build, archive or TestFlight action was executed for this checkpoint. Apple compilation, actual test enumeration/execution, real original account/engine-switch drain and complete native body readback remain required before any production save registration.

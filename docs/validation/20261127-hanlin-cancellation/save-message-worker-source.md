# Shared original Hanlin write worker — source milestone

Status: source authored; Apple compile and the five new worker-test methods/ten namespace cases are NOT_RUN. This does not install a save catalog entry or expose a save UI action. It is not native document-write, ABI, complete-body conversion, or Release acceptance.

## Original ownership preserved

This follows protected-journal source `65333e6b34cd485532fd2d17ce6425f8ae7ec967`. Existing `PinkhaHanlinCreateRunner<Approval, Prepared>` retains its public constructor, three-argument Dispatch callback and methods, now forwarding to one `PinkhaHanlinWriteRunner<Plan, Approval, Prepared>`. The shared implementation remains the original reservation, timeout, synchronous cancellation fence, unstructured native worker, one-shot result, original metadata receipt and native drain. There is no second cancellation engine.

The strict plan protocol supplies its original envelope parser, immutable identity and logical tool ID. Metadata reservation happens after the generic reservation and before consuming approval. The same original job's fence, identity, deadline and current host validation are checked again after the metadata await. New native bindings receive `authorizeNextEffect` and must call it before each effect; they must not require it to persist late native receipts or to drain already-dispatched work. The original approval is consumed once.

On cancellation or failure, the worker awaits the original store's dispatch close before its terminal metadata outcome. That close and the generic outcome remain separate actor calls. A new controlled case covers an initial manifest appearing precisely between close-with-no-initial and terminal recording: the post-await synchronous job fence prevents native dispatch, and the original worker closes the actual manifest before finishing. No tombstone, retry ID, replacement account or new native authority is fabricated.

Only the binding's full aggregate receipt may call the original final callback. The journal independently rejects root-only success. A complete receipt still does not release a native worker that holds its lease. No newer run or current-account lookup reconstructs an old receipt.

## Bounded metadata correction

The journal's complete-body event bound increases from32 KiB to64 KiB, including the budget reserved before native effects. The initial128 KiB, ordinary-event4 KiB, legacy-entry16 KiB and aggregate64 MiB bounds stay fixed. Accepted native IDs are nonempty, at most256 UTF8 bytes and reject all Unicode control characters. The new bound accommodates64 maximum-length escaped block IDs, the root ID and fixed canonical event envelope. The sibling owns the matching record encoder/decoder bound and maximum escaped-ID replay regression. Their exact compatible follow-up must be included before native save qualification.

## Authored tests and dependencies

`HanlinSaveMessageWorkerTests` has five methods/ten cases: cancellation while metadata preparation is held; initial-save versus first-close interleaving; cancellation after a known root with no subsequent effect; aggregate receipt with an unfinished native lease and stale authorization; and failed metadata preparation without approval or dispatch. These use the real shared worker and protected journal with controlled native callbacks, not an engine implementation. Existing `HanlinHostCancellationTests` must also run on the changed worker to cover the compatibility adapter; prior SDK385 tests do not qualify this consumer change.

The sibling owns new save plan/progress/conversion/binder files. The new Wave1 original Any conditional Markdown adapter is a separate pending dependency; a single atomic body write must use truthful aggregate state and native readback, not synthetic per-block dispatches. The generic worker is engine-neutral and does not duplicate that adapter. Native input and normalized saved-body digests must remain distinct.

The first shared App build/retry stays on its frozen SDK385/native8ac source. This candidate, the original full UI union and its future focused acceptance remain a separate milestone under the final integrator's ownership.

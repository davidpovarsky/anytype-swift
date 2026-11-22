# Internal held-read consumption contract

## Admission and lifetime

The adapter is internal to the original app. Its existing runtime, original AccountManager identity/epoch, configured account/Space/root, prepared document and source binding remain authoritative. The new seam uses the existing Owner.withExclusiveRead and ObjectShow RPC name; it does not create another dispatcher or enter a nested exclusive barrier.

Fresh ObjectView and the strict native root Struct are consumed synchronously before that same closure returns. Original RPC admission/completion and post-response ownership validation remain in force. A callback may use an explicitly read-compatible synchronous child operation, subject to the original Owner rules. Default mutation upgrade and nested exclusive read remain denied.

## Outcomes

- `completed(value)`: the synchronous callback returned and the enclosing original read completed with current ownership.
- `completedWithoutCurrentOwnership(value, error)`: the callback returned, then later original validation/drain/cancellation rejected the read. The returned value is preserved with that actual error.
- A thrown callback or prior error remains thrown. The original error is retained, and callback side effects may already exist. This is not a safe-to-retry assertion.

None of those forms independently proves durable commit. A future persistence consumer must derive its own database outcome from the real outer transaction and preserve uncertainty correctly.

## Native observation versus qualification

Strict response checks require the original native root/details association, exact native Space, one nonempty native type identifier, and proper boolean kinds for any present unavailable states. These shape checks preserve an otherwise unknown type and therefore do not qualify the object as a Torah annotation.

The complete ObjectView, root Struct, linked rows, unknown fields and block contents remain available to the synchronous callback. Their presence does not prove equivalence to an intended delivery or authenticate copied metadata. Body/attachment/reference/version equality requires a separate complete original-codec comparison and current creator/destination/account/Space/source policy. Metadata-derived snapshot digest remains unproven; no native identity, body receipt or ACK grant is constructed.

## Source compatibility

The former readFreshDetails method body and existing comments remain byte-identical. Its strictDetails parameter now spells the actual generated `Anytype_Rpc.Object.Show.Response`; the old unresolved `ObjectShow` token is not preserved as an invented alias. The new outcome does not alter the old throwing API.

The 26 focused tests exercise the original Owner and generated/value sources through the explicit portable boundaries described in README.md and CONTROL_PLAN.md. They do not qualify the native Invocation implementation or full Apple dependency graph.

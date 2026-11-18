# T2 native target fetch context

## Observed failure and source explanation

The original cold-client diagnostic run [44293946784](https://github.com/davidpovarsky/anytype-swift/actions/runs/44293946784), at source `67793bdd9d3aa8f47ebe1d8c4258bb0f7e547252`, failed the concurrent-client scenario. The observer around the original read reported `unknown_tree=true` and `context_peer_missing=true`. The cancellation, deadline, closed/deleted and no-responsible-peers categories were false. The generated response remained an internal error with no snapshot. This is a failure observation, not sync acceptance. The later absence of stored trees is a separate diagnostic observation.

The pinned source explains a matching error path. AnySync's remote tree getter first checks local storage; its peer-selection path uses `peer.CtxPeerId`. If that context lacks a peer, `getTree` maps `ErrPeerIdNotFoundInContext` to `ErrUnknownTreeId`. Heart's target-source loader wraps the tree-build error without changing its cause. The account-scoped T2 handler validates the ordinary target before opening the private root; a byte-entry context has no peer routing hint. This is the source-based causal explanation for the observed pair of categories. It does not imply that every unknown-tree error is a temporary network condition.

Pinned public sources:

- [AnySync peer context](https://github.com/anyproto/any-sync/blob/5d71ccad5db77997df2d2426011ebae4e7600d98/net/peer/context.go), SHA256 `3b93854cb0b4ad697a0d9ce850307fc6653e5fdce5e6a4ebd94176cbe55c045f`.
- [AnySync remote tree getter](https://github.com/anyproto/any-sync/blob/5d71ccad5db77997df2d2426011ebae4e7600d98/commonspace/object/tree/synctree/treeremotegetter.go), SHA256 `b867c323c3581e1229a063af3f796d29ef24166a9ecf4950a68242a594b25f89`.
- [Heart target-source loader](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/source/sourceimpl/source.go), pinned original SHA256 `c289b2823cce4b3d345377245b37fc3efce7c8019290133edc42eb3a5b02c3bd`.
- [Heart native Space](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/clientspace/space.go) already uses `peer.CtxWithPeerId(ctx, peer.CtxResponsiblePeers)` for native remote loads.
- [Heart responsible-peer manager](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/spacecore/peermanager/manager.go), SHA256 `ef5cf8678c0cde75177e64bf7062f6359e380bf127e8cff0109a071701adfada`, waits for available peers or the caller's context. A bounded caller context is therefore required here.

## Narrow production change

`pinkhaTorahScope.host` replaces only its pre-host `ValidateNativeTarget` call with `validatePinkhaTorahTargetBeforeHost`. The helper creates a child context with a maximum 15-second deadline and uses the native responsible-peer routing hint only when `peer.CtxPeerId` reports that no peer is present. A caller-selected peer, including the native DRPC fallback, remains selected. Caller values, cancellation and any earlier deadline remain attached.

The 15-second bound limits this new remote target lookup and leaves room inside the existing 20-second fixture byte-call boundary. The child is canceled immediately when target validation returns. It is not reused for the private host, append or read. A native SmartBlock lock is not context-cancellable; the existing post-lock context check remains, and this change makes no hard wall-time guarantee for a lock that never returns.

The lookup happens after current native ACL validation and canonical root derivation, before opening or locking the private operation tree. The generic `ValidateNativeTarget`, its `DoCtx` loader and callback context fence remain unchanged. NativeHost does not gain a new network lookup under its private-tree lock.

The existing private-root presence check, `HistoryUnavailable` on absent read history and append-only root derivation are unchanged. There is no HasTree pre-gate before target loading, error reclassification, automatic retry, replacement root, injected history, caller-provided author, new peer manager or App capability enablement.

## Verification contract

Four new native test methods exercise the real helper-to-`ValidateNativeTarget`-to-`DoCtx` boundary. They require the responsible-peer hint and finite lookup deadline, preserve caller values and original error identity, verify cancellation during a blocked load, preserve three explicit peer forms and the earlier deadline, and reject already canceled/expired contexts before target access. They contain five named subcases: nine required native test events in total. A nil target/Space in the ended-context controls makes a missing cancellation fence observable.

The registration runner requires all nine named events, in addition to every previous registry control. Its existing package list and `TestPinkha` selection include the new tests. Component scope is unchanged.

The registration inventory records the changed call site and the two new source files. The RPC manifest points to that exact registration inventory, and the account-RPC fixture points to that exact RPC manifest. The registry/schema patches, generated protobuf identities, account fixture bodies, two-client read predicates, diagnostic observer, legacy binary and offline branch are unchanged.

At this source handoff, native formatting/build/tests and cold-client acceptance are **NOT_RUN**. Local Python receipt controls, syntax parsing and hash-chain checks are source validation only. The isolated offline/conflict/reopen source must remain unintegrated until cold bootstrap succeeds. Two App clients, iOS acceptance and full T2 remain open; App capability remains **OFF**.

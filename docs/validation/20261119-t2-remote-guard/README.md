# Recovered native tree: one bound commit guard

Run [44560628796](https://github.com/davidpovarsky/anytype-swift/actions/runs/44560628796) observed the restored client's first offline write failing with the mandatory native commit guard, before any durable change. The authenticated original artifact and fixed-schema observation are identified in validation.json.

The actual AnySync v0.13.8 remote getter returns the storage of the already validated tree. Final SyncTree construction invokes the builder again. The previous builder unconditionally nested a new guard around that existing guard; the inner layer rejected the outer layer's token.

The builder now reuses the already bound storage only when its ACL instance and exact root identity match. Foreign ACLs, altered headers and nested guards fail closed. All existing local-entry, signed-content, current ACL, cancellation and durable-commit checks remain.

The new regression fetches a real encrypted tree over the existing loopback DRPC transport, through the actual upstream response collector and final SyncTree builder. It then denies an unguarded local append, appends through NativeHost, verifies durable readback and tests an identical retry. Three further cases reject foreign bindings. The original seven native-client scenario fixtures are unchanged.

The focused controller tests pass6/6; registry, RPC, account and native-client source pins validate. Independent source review found no blocker. Actual pinned-Go compilation, native regression execution and two-client acceptance are pending at this commit.

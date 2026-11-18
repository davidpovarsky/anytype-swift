# Typed native handler through a real account ? fixture contract

This change extends the existing four-process account lifecycle test. It adds no public generated RPC, App binding, startup creation, capability flag or production native code. Native execution of this changed fixture is **NOT_RUN** at publication. The independently verified baseline run 44245137022 used an earlier fixture and cannot be assigned to this change.

## Exact lifecycle

The two-binary sequence remains new-create, new-reopen, legacy-edit, new-recover. Account creation occurs only once. Later phases recover the original disposable key and select the same account/Space. Existing strict export, search, ordinary edit, source identity, nonce/PID, signed history and cleanup assertions remain unchanged.

Only the new binary includes `account_lifecycle/native_handler_test.go`. The legacy binary cannot compile or call the new typed boundary and records `UNSUPPORTED_LEGACY`. Its existing private-type rejection, byte preservation and ordinary edit still execute.

Before a root exists, the new helper observes HasTree=false initially and immediately after each of four non-creating calls: an absent-root read, unsupported-version append, missing-block append, and malformed-payload append. Each rejection requires its exact error and a zero result. A valid typed append then creates the same root derived from native Space authority, with a nonempty claim and signed change. The ordinary factory fetch verifies the actual private host type, Space and unique key. A direct host retry must return AlreadyExistsSamePayload with no new ChangeID.

The operation author is derived from the real account signing key. Each new phase reads the original exact operation through the typed handler before retrying. Identical replay must remain idempotent. Different payload under the same operation ID must return CollisionDifferentPayload; projection, heads and watermark must remain identical. The tree still contains exactly its signed root and one operation.

Existing final target deletion and Space deletion controls also require typed read/append denial. After actual AccountStop and AppShutdown, both typed operations must return ErrNotLoggedIn with zero results. The shared fixture invokes this post-stop helper only after it has verified public shutdown, without recreating an account.

The controller requires all these named receipt fields. Missing evidence or a claim of registered/generated RPC is rejected. It cannot reuse the baseline run or silently upgrade native component evidence into App acceptance.

## Source and review

The complete new helper and all five exact-context existing-file hunks were reviewed by the parent. The requested per-call no-root observations were added before integration. A separate read-only review by the T5 lane found no blocking contract issue in the helper, entire patch and new runtime.

The five existing source changes were applied locally under exact before/after hashes in one isolated App worktree. No complete private source transfer, Heart write or T5 source mutation occurred. The new helper SHA-256 is `853e2ae1ce660e320929349bac4783905ef1e229309ee61dfebdebc41b6a4b65`.

17 Python controller controls passed on Linux, including real POSIX process ownership controls and the new missing/overstated handler-evidence control. Go fixture formatting, Python parsing, exact resulting source hashes and git diff whitespace checks passed. Windows source checkout CRLF was normalized with scoped gofmt before final hash verification; no native compiler was run there.

`evidence/20261118-native-handler-account-source/source-validation.json` records canonical hashes and scope. The reusable account-lifecycle workflow is unchanged and will run this new fixture from its exact integration SHA. Generated RPC, two App clients and iOS remain separate acceptance work.

# Original native read error observation

This is a diagnostic fixture for the existing two-native-client bootstrap lane.
It does not change production Heart source, the registered protocol, native
authorization, read readiness, timeout policy or the order of RPC calls.

## Evidence motivating the observation

Run 44280905417 on integration `743ae42f7b8ec8181efe5e87f3bb5ccbc1b4ad63`
failed in recovered client B. The original generated read returned INTERNAL_ERROR
with ISSUE_UNKNOWN_INTERNAL and no snapshot. Later HasTree calls reported no
local target and no local private root, with nil storage errors. Later absence
does not identify the original wrapped native error.

The public pinned AnySync v0.13.8 source (`5d71ccad5db77997df2d2426011ebae4e7600d98`)
shows that `treeRemoteGetter.getTree` preserves native storage/transport errors
and converts missing peer context to ErrUnknownTreeId. Its `getPeers` uses
CtxResponsiblePeers to call the native peer manager. The corresponding Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff` target-load path forwards the request
context through GetObject and source construction. This supports a hypothesis
to measure, not an accepted diagnosis or a justification for changing retries.

Public source references:

- `https://github.com/anyproto/any-sync/blob/5d71ccad5db77997df2d2426011ebae4e7600d98/commonspace/object/tree/synctree/treeremotegetter.go`
  SHA256 `b867c323c3581e1229a063af3f796d29ef24166a9ecf4950a68242a594b25f89`.
- `https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/source/sourceimpl/source.go`
  SHA256 `c289b2823cce4b3d345377245b37fc3efce7c8019290133edc42eb3a5b02c3bd`.
- `https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/clientspace/space.go`
  SHA256 `9d013f65a61ddd3c436622b9809d37e67fdd8246130005d21461e51a89416f32`.

## Exact observation boundary

`two_clients/native-read-observation.patch` adds a fixed diagnostic immediately
after the original `mw.NativeTorahTargetRead(ctx, native)` returns, before the
unchanged wire mapper receives that same result/error. It does not make a
second read, fetch another tree or change the context. It emits only Go error
types and fixed errors.Is booleans for unknown tree, no responsible peers,
closed/deleted tree or Space, cancellation/deadline and missing peer context.
It never calls Error() or prints account/Space/object IDs, keys or payloads.
A nil context is handled without invoking peer lookup on nil.

The runner verifies the original RPC source hash and diagnostic patch hash,
patches a copy under the private build work directory, and verifies the exact
resulting hash. Go's compile overlay substitutes that one copy only in the new
test binary. The original Heart source remains unchanged and all original
source/generation checks remain in force. Both before/after hashes and the
test-only scope are separately recorded in the build identity and receipt.
The patch hash is part of the native-client fixture digest embedded in the
binary. The legacy binary and the default account-RPC lane do not receive the
overlay. No new workflow, source inventory, generated stub or App flag exists.

The original baseline four phases, bootstrap readiness predicate, fatal read
assertion, secret scan and owned-resource cleanup remain unchanged. Raw native
logs remain in the existing secret-scanned artifact allowlist; source files,
Go overlay copies, account roots and keys are not published.

## Controls and limits

Two Python controls apply the exact patch to a temporary source copy, verify
that the original bytes remain untouched, and reject changed source/patch or
an existing work destination before mutation. During these checks an existing
Linux process control exposed a `/proc/PID/stat` disappearance race after the
owned child had exited. Its test-only check now treats FileNotFoundError as the
same already-expected absence; a running child and the unrelated control group
are still checked under the same deadline. No process cleanup policy changed.

Native execution of this diagnostic is NOT_RUN until a source-bound CI run
produces the original error category. Any eventual observation remains distinct
from a production fix, offline convergence, two iOS clients and full T2
acceptance. App capability remains OFF.

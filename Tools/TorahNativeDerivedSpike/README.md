# Native Torah derived-property feasibility implementation

This is executable downstream research code. It does **not** register native
Properties, change Heart/protobuf, upgrade a Space, or enable a UI feature.

The read-only Go projector shares 21 golden fixtures with the existing Swift
codec and document projection. It uses NFC-normalized, UTF-8 length-prefixed
identities, exact document/context scope, deterministic arrays, v1 reads,
explicit malformed/future-version errors, and a SHA-256 of unchanged input.
Binding discovery validates per-Space native keys and the three writing Type
IDs without deleting duplicate manifest objects. An ambiguous binding fails
closed. Readiness epochs reject stale rebuild completions; they are not a
production durable checkpoint implementation.

Portable checks, from the repository root:

```text
python Tools/TorahNativeDerivedSpike/run_local_checks.py --evidence <output-directory> --swift
```

Native ObjectStore probe (Linux/macOS; Go 1.26.5 and CGO required):

```text
python Tools/TorahNativeDerivedSpike/run_heart_probe.py --heart-source <pristine-pinned-heart> --native-library <verified-library-directory> --evidence <output-directory>
```

The checkout must be exactly Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`.
The runner creates a temporary Go workspace, so Heart's own module replacements
are honored without changing dependency files. Supply a normal Go cache or use
`--module-cache`. Only disposable `testing.T.TempDir` databases are written.
No account or personal Space is opened. Add `--bench` for synthetic 100/2k/10k/50k
ObjectStore workloads, with two real canonical source items per document.

The probe exercises actual Heart `FilterIn`, `FilterAllIn`, negation, empty,
AND/OR, SQLite writes, and commit/rollback notification ordering. It does not
exercise `ObjectSetDetails`, a production indexer hook, native Set/Dataview
subscriptions, iOS PropertyDetails, old-client import/export, or an iPad.
Those distinctions remain release gates even when this probe passes.

No Tag/Option/source objects, synced mirror writes, or private-path dependency
pins are introduced. `integration/go.mod` uses the public pinned Heart tag and
a repository-relative replacement for this sibling probe module.

The external integration harness pins the `google.golang.org/genproto` root
module to the same 2024 revision used by Heart's explicit RPC-submodule
replacement. Without this test-only root pin, the combined harness graph
selects a 2021 root module that also contains `rpc/status`, causing Go's
ambiguous-import error alongside the split RPC module. The initial failure is
retained in evidence. Heart's checked-in dependency files remain unchanged;
passing this overlay is not a pass for the unmodified production module graph.

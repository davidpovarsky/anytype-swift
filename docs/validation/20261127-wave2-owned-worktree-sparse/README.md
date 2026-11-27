# Owned worktree evidence-copy dematerialization

2026-11-27. Documentation only; no product source or acceptance selection changed.

The Wave2 root worktree was clean at published source `5e581f20bd0e713aead73096c590dc2beeeb74aa` (tree `9df21b851069a57773f45fd1bd096ca44f4e2758`). Its matching remote branch was read back before the operation. All 1,718 materialized files under `docs/any-engine-port/evidence` and `Tools/AnyEngineValidation/evidence` were checked against their exact Git blob bytes and recorded with SHA256, size and Git mode. No owned writer was active.

A normal non-cone sparse-checkout update removed only those reproducible working copies. It freed 90,402,816 allocated bytes. The local Git object store and published remote retain every original; no account, native/App product, unique evidence, source code or Sharing test cache was removed. No other worktree was changed. All index path/blob/mode/stage entries, HEAD and tree remained identical, and the worktree remained clean.

`patterns-before.txt` is the exact original sparse configuration; `patterns-after.txt` is the applied configuration. The full tracked manifest and both original command streams are retained without rewriting. The original result SHA256 is `a3736fa14fc620b25c377bddf8b881e03a5a04d8b558525bb5794d531b23b88d`; the manifest SHA256 is `dba6530ba6576a90b0bfe944923a478ff900ec5cc2a550a740a040b79f783d7b`.

The earlier suggested operation never executed after a Sentinel internal error; its non-execution was recorded in HQ51 comment1220941238011237. This successful operation is distinct and does not rewrite that history. Coordination/result: HQ51 comment1220941773649624.

The free-space observation at completion was 940,175,360 bytes. Concurrent writers can change that value; this receipt does not claim that the shared capacity problem is resolved. Original private receipts remain at `/var/lib/pinkha-wave2-owned-sparse-20261127`.

Git also attempted to reconcile the pre-existing `docs/validation` exclusion and emitted 23 permission warnings for the root-owned Sharing/Inspector proof copies. Those 23 files remain present and byte-identical to published Git, independently checked in `stderr-review.json`. No permission was changed and the sparse operation was not repeated to silence the warnings. The original nonempty stderr is retained; the successful result above is scoped to the two newly excluded evidence-copy directories.

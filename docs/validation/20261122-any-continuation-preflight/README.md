# Any native continuation preflight repair

Original run `45049717660`, attempt 1, used commit
`edf1545f2ebcd1a71d307735a645c779cb9dc3bb` and failed at
`consumer_source_worktree_not_clean`. The source-bound native artifact had
already been reused successfully. No application build, selected UI method,
Files roundtrip, custom Type transition or history method ran in this attempt.
The original failure remains a failure.

Artifact `14766078296` is retained verbatim as
`original-failed-artifact.zip`: 212,900 bytes, SHA-256
`ffcfdb409e1bdb7fef1d496667759c55d697c82d3ad702a3055be824df6c9bae`.
The original receipt did not record its offending paths, so this report does
not claim those paths were observed in the Apple result.

## Reproduced startup cause

The exact original controller imports local Python modules before its source
check. The exact root `.gitignore` does not ignore bytecode; there is no
`Tools/AnyEnginePort/.gitignore`. In an isolated Git checkout containing the
original Git-verified source, running its actual `--help` entry creates at
least six untracked `.pyc` files inside the protected tools directory. That
is independently sufficient to fail the original untracked-file condition.
The installed native vendor directory is separately ignored by the original
runtime module's `.gitignore`; the pinned Hanlin destination is also ignored.

The patched native job now sets `PYTHONDONTWRITEBYTECODE=1` before any Python
step. The same original entry then leaves the protected checkout clean.
Existing caches and all other unknown or modified files are still refused;
no new ignore rule, deletion, reset or dirty-source exception is introduced.
The refusal now records bounded actual path lists and total counts, so any
additional cause in the next Apple run will be directly reviewable.

## Exact source continuation

The only newly admitted consumer branch is
`codex/chatgpt-wave15-acceptance-continuation-20261122`, alongside the already
authorized shared branch. Original producer validation remains pinned to the
original shared branch, run, commit, artifact and failed result.

The continuation work branch starts from the exact original consumer commit
and carries controller fixes only. This preserves its reviewed twelve product
changes while later semantic-anchor integration progresses on the shared
branch. The full protected product source comparison remains unchanged and
will reject broader unreviewed product changes. The new branch name alone
does not authorize a different source closure or original result.

Three new controls passed: actual original import hygiene, refusal with exact
paths for modified/unknown source, and the two-name consumer branch boundary.
The original sixteen controller controls are retained without execution:
their named functions and test source are unchanged. There were zero Apple
or product tests in this local control run. Original method outcomes remain
at their original source scopes; current native UI acceptance is pending.

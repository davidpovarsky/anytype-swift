# Actual r15 Apple runtime attempt — 44240654969

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44240654969

Integration source: `15656bf3faeef0659fb8639a2e7f73727ad443b0`. Actual outcome: **FAIL**, finished 2026-11-18 05:14:00 UTC. The GitHub run also reports failure. The only published artifact is the evidence artifact; no verified r15 Apple framework was produced. Native test invocations are zero; AppGetVersion and Swift pairing were not executed.

The previous MTL cache-seed fix worked at its stated boundary. `mobile-dependency-preparation.json` records 14 successfully downloaded modules with their versions and both h1 hashes. The pinned gomobile and gobind tools built. The retained original bind log then reports:

```text
go mod tidy failed: exit status 1
go: git.sr.ht/~sbinet/gg@v0.6.0: module lookup disabled by GOPROXY=off
```

All three architecture launch records show this failure in the original generated gobind scope, with GOWORK explicitly off and GOPROXY off. No error or log was replaced with a successful fallback.

## Cause and prepared correction

The primary pinned gomobile source flattens the selected native module list into direct requirements before generated tidy. The original native list has 882 modules and selects gg v0.3.1. Its gonum v0.17.0 dependency authoritatively requires gg v0.6.0 in its own go.mod. Flattening the graph therefore introduces a different module selection boundary. The prior seed covered mobile's own dependencies, but did not cover this generated graph.

The prepared correction derives a fresh seed from the exact original module list, preserves all versioned replacements, hydrates its full graph, and records both graphs separately. It compares the actual pre-tidy declarations against that seed and checks the effective selected dependencies after tidy and before compile, permitting only unused-module pruning. Native source, mobile/toolchain revisions, original native declarations, r14 helper and approved r15 inventory are unchanged. The observed gg version and both h1 values are independently checked against the preserved primary gonum go.sum.

This source change has not yet produced a successful Apple runtime. Complete generated-cache hydration and Apple execution remain NOT_RUN locally and require the next reviewed CI run.

## Raw artifact integrity

Artifact ID `14399847569`, 123,889 bytes, SHA-256 `ad6cbbab288abc9c926120554c9ce39006613dfdad3cbb9d58408b98e07d0267`. The original outer ZIP, nested evidence ZIP, all 65 archive member entries, API metadata and SHA-256 inventory are preserved separately. The `dependency-source` directory contains primary source snapshots with Git blob IDs, URLs and byte hashes; it is analysis provenance, not rewritten CI output.

The separate small metadata experiment under `20261118-t5-generated-graph-metadata` confirms the MVS version transition in actual Windows Go1.25.6 graph output. Its deliberately partial cache did not pass the subsequent offline lookup. It is not complete hydration or Apple proof.

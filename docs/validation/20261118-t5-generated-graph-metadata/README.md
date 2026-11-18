# Bounded Go module metadata observation

This is an actual Windows Go1.25.6 metadata command sequence on three source-derived requirements: gg v0.3.1, gonum v0.17.0 and plot v0.10.1. The graph output resolves the root gg selection to v0.6.0, matching the pinned gonum declaration. The explicit gg v0.6.0 download matches both h1 values in that authoritative go.sum.

The final offline selected-module query FAILED because this probe downloaded only gg, not the complete graph. This is not a successful cache-closure check. initial-result.json preserves the ad hoc script's incomplete RUNNING receipt; result.json records the observed terminal job exit1 and the precise partial scope. All command stdout/stderr files are retained unchanged.

The 1,451,854-byte owned temporary cache was removed. No compile or Apple/native runtime test ran. At startup the host had 1,864,818,688 bytes free RAM and 2,493,702,144 bytes free disk. No further local hydration was attempted after resource review. Complete hydration belongs to the reviewed CI builder, which uses the entire exact generated graph and performs offline selected-graph checks.

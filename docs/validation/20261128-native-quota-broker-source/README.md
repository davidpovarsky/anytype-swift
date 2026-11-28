# Quota broker cancellation: source carrier and Files acceptance handoff

**Source review and formatting are complete. The seven selected tests have not run.** This additive carrier supplies one native production replacement, one new test file, complete original before-images/dependency bodies, and the retained FilesV2 acceptance matrix. It does not change an active application or native source tree.

The independent [Root source review](receipts/root-source-peer.json) is CLEAR. The [original formatter output](receipts/formatter-stdin-original.jsonl) contains two actual stdin/stdout gofmt commands and their summary: both exit 0 and both return byte-identical source, using pinned gofmt 3ca5e23c. There were zero compiler, native, test or project-file-write actions in that formatting proof.

## Change and boundary

The current quota hedge waits for peer answers and its hedge timer, but originally has no context-Done arm. A peer callback that does not return can therefore hold the coordinator past cancellation or deadline. The replacement adds only an entry ctx.Err check and a ctx.Done select case returning the context error. The [exact inverse](../../../Tools/AnyEngineValidation/native_quota_broker_cancellation_20261128/preparation/EXACT_INVERSE.json) recovers the full original broker.

The coordinator can return on cancellation without terminating an arbitrary callback. The original answer channel remains buffered for all peers, with one send per launched peer. The controls deliberately hold a callback past cancellation, then release it and join the test-owned coordinator. Callback-return observation is conditional on entry during early-failure cleanup; no private sender join or forced callback termination is claimed. A simultaneously ready successful answer and cancellation retain ordinary Go select scheduling.

The original zero/exhausted-quota response, peer selection, durability verification, job persistence and retry policy remain unchanged. No cause is assigned to Alice's historical limit 0 / usage 21,070, and no new storage grant or cloud recovery is claimed.

## Exact source

| Item | Identity |
| --- | --- |
| Base full compiled-source map | 3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4; Git blob 1bb7c086f3d28a8e7c2aedee26656a2ba40b71b3 |
| Original broker | 12,108 bytes; 25de187fc12f7e8a9e1aa89c420a47e2bbc9aac021740e0257f79c63245e4f34 |
| Proposed broker | 12,218 bytes; fe698597e58d3cd2aa4ce99bf00f59cbf101ce81c4b00f77d3539d483fc9ea9d |
| New test | 3,804 bytes; 3545314693fea848a66e55c3fb22b76981a6d30fe859b52f718a8288e4077100 |
| Root peer | 8,005 bytes; 9f2fb289a60764cb9a4250f290805885889ff50d4c09057ecf5bdc084efe9354 |
| Original formatter stdout | 18,684 bytes; 858902da3098e130af688704ac18f0f80991643bd1716bbbe292f9464ae34e57 |

The complete [reviewed source manifest](../../../Tools/AnyEngineValidation/native_quota_broker_cancellation_20261128/preparation/SOURCE_MANIFEST.json) names the two overlay paths and nine original source bodies. Those original bodies join the base 3552 map with native mode 0600. Git artifact modes are 100644; they do not claim that native source permissions changed. The new test was absent from the base map and the reviewed N24/lifecycle maps.

The prepared documents under preparation/ retain their original pre-format SOURCE_ONLY scope. They are not rewritten to imply that formatting or tests had already happened at preparation time. The separate later formatter receipt above closes formatting only. The earlier 500 ms control draft and four-event selection remain under preparation/before-control-review; the final selected controls use the five-second actual deadline and seven-event selection.

## Future selected tests

The [exact selection](../../../Tools/AnyEngineValidation/native_quota_broker_cancellation_20261128/preparation/SELECTED_TESTS.json) contains five parents and two children, seven events total:

- New pre-cancelled entry: TestPinkhaQuotaHedgePreCancelledSkipsFleet.
- New cancellation/deadline boundary: TestPinkhaQuotaHedgeEndsBeforeBlockedPeerReturns, with cancel and deadline children.
- Three affected original parents: TestHedgeQuota, TestHedgeQuota_Cancelled and TestQuotaFrom_RemembersUsablePeer.

The three original parents are selected because their callee changed; their bodies remain exact. TestPeerFirst and TestSpaceQuotaOf are unselected. The new actual deadline is 5 s, callback-entry bound 2 s, context observation 7 s and cancellation-return bound 2 s. No selected event is accepted by source review or formatting.

## FilesV2 retained versus remaining work

[FILES_ACCEPTANCE_MATRIX.md](FILES_ACCEPTANCE_MATRIX.md) and its [exact references](FILES_ACCEPTANCE_REFERENCES.json) preserve the completed LAN full/range/partial-crash/resume/offline proof, selected two-file cloud proof, positive full-tier eviction/refetch, signed reader lifetime and native content/metadata denials with their original product tuples.

The original PNG of 49,363 bytes and large 8 MiB file still lack complete cloud durability/retrieval acceptance; current quota also remains unobserved. Durable jobs have no overall retry-count cap. Continued LIMITED state while real quota remains unavailable is intentional persisted state with ten-minute pacing, not a busy-loop or recovered cloud success. The single-dispatch retained-account quota observer remains unrun.

## Consumer integration

This carrier is a new branch with sole parent 94fd763d459210b496557894628333d466abae73. The existing N24 branch, twenty source overlays and 24 unrun selected events remain unchanged. Root's separate boot/lifecycle source and E's 33-event selection are also distinct. The later broker slice requires an explicit complete composed source map and selected-event union before one qualified native product can be accepted. No new ABI, Apple runtime, application adoption, cache ownership or runtime permission follows from this commit.

Every declared blob is read back whole, and the undeclared parent Git tree is retained. No force push, integration-branch update or Oracle project allocation is used.

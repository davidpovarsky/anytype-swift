# Quota broker cancellation source proposal

Status: SOURCE_ONLY. No formatter, compiler, unit test, native process, cloud account, or runtime quota query was run for this proposal. The existing N24 carrier remains unchanged and its 24 selected events remain NOT_RUN.

## Concrete defect and scope

The exact current broker source `25de187f...` runs `hedgeQuota` with a caller context but waits only for a peer answer or its hedge timer. It does not select the context's Done channel. Once all peers are asked, a callback that does not return can hold the coordinator after the caller cancels or its deadline expires. The original cooperative cancellation source test makes the fake peers return when their context ends, so that test does not cover this coordinator boundary.

The two production insertions are an entry `ctx.Err()` check and a `ctx.Done()` select case returning the context error. Every other original source byte is preserved. The exact inverse edit program recovers the full original broker. There is no empty-fleet, peer-order, healthy-answer, unusable-answer, refusal-priority, remembered-peer, upload, quota-value, account-limit, or durable-job policy change.

This is a source-demonstrated cancellation gap, not a claim that a production RPC has actually ignored its context. It is not attributed to the retained Alice account's historical storage limit 0 / usage 21070. The proposal grants no quota, turns no refusal into success, and establishes no cloud recovery.

## Lifetime boundary

Cancellation returns the coordinator; it cannot terminate an arbitrary callback. The original answer channel remains buffered with capacity `len(peers)`, and each launched peer sends one answer. Therefore the existing channel can accommodate every late answer without a receiver. The coordinator keeps its original deferred child-context cancellation and timer stop. No wait group or unbounded callback join is added to production.

The test deliberately holds one callback independently of the context. It requires the coordinator's cancellation/deadline result before releasing that callback. Cleanup always cancels the context, releases the callback once and joins the test-owned coordinator with finite waits. Callback return is observed only if callback entry was seen; an early entry failure makes that observation conditional. The callback-return signal precedes the private sender's final buffered send; the control does not claim to instrument or directly join that private sender. It does not claim to kill a noncooperative callback.

If a usable answer and cancellation become ready together, ordinary Go select scheduling still applies. The proposal does not invent strict cancellation precedence over a simultaneously available successful answer. The pre-cancelled entry check does guarantee that a lookup already cancelled at entry launches no peer.

## Focused controls

Two new test parents have two named children: four new events, all NOT_RUN. One checks that an already-cancelled lookup launches zero peer calls. The other has cancel and actual context-deadline cases, holds the peer until cleanup, and requires the coordinator to return the exact context error with nil quota and empty peer. The actual deadline is five seconds, callback entry has a two-second bound, context-end observation has a seven-second bound, and the separate cancellation-return assertion remains two seconds.

The new file is absent from the exact 3552 full source map. Three original quota parents are also selected for future qualification because their callee changed: TestHedgeQuota, TestHedgeQuota_Cancelled and TestQuotaFrom_RemembersUsablePeer. Their source bodies remain exact. The selected union is five parents plus two named children, seven events total. TestPeerFirst and TestSpaceQuotaOf stay unselected. The other original account-limits, upload and queue tests are delivered unchanged as source context. No selected event has been executed or promoted to a new passing cohort by this packet.

## Existing quota and job behavior, from the pinned sources

A file-node ErrLimitExceeded remains a typed limited error. The durable queue persists its job, error, attempt and next-run state; limited jobs use a ten-minute next attempt. Startup intentionally makes previously attempted jobs due again. Local bytes and the unsigned row remain until real durability is established; receipt verification is still required before marking a network signature. Retry pacing, restart semantics and server permissions are unchanged.

Account limits distinguish absent data, cached older data and an actual answer whose limit is zero. The existing fetch context is finite and its single in-flight bookkeeping still belongs to account_limits.go. This broker change closes the coordinator's own wait on cancellation; it does not qualify the timing of arbitrary external callbacks or storage implementations.

## Source lineage and adoption

The full base map is 3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4, Git blob 1bb7c086f3d28a8e7c2aedee26656a2ba40b71b3 in davidpovarsky/anytype-swift. It belongs to actual Runtime18 f832753c and current product 84a4432a. All nine original dependency bodies are read back whole and join that map with their original mode 0600.

Only internal/files/broker/broker.go is replaced and pinkha_quota_deadline_test.go is added. The packet is disjoint from the frozen N24 twenty-file overlay. Any later composed production/qualification maps, selected test union, compiler result and embedded ABI acceptance require an explicit new qualification. No branch ref or active source tree is changed by these unreferenced blobs.

## Preserved source-only predecessor

The first source-only packet remains intact: manifest Git blob bf41eab5f1eaddfa4662d053dc55be532b6d7b79 and test blob 9c8caf77d06c7ebe5f6511e22db5428274c62f89. This successor changes only the test deadline/observation bounds and cleanup wording, the future selection of three affected original parents, and resulting source-delivery pins. The production blob remains 49c06cd901fc33faca11fa2483c925dfc4898572 / fe698597e58d3cd2aa4ce99bf00f59cbf101ce81c4b00f77d3539d483fc9ea9d.

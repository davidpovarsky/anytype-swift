# Native Torah format decision — implementation update 2026-11-04

Selected implementation: **B, native derived list Properties using the existing
wire format and three immutable semantic keys**. No enum/protobuf change is
required. These are installed native Property Objects with native Type
recommendations, native ObjectStore indexes and native Set predicates. Their
values are canonical identities, not option Object IDs; the original option
creation API is explicitly blocked for these keys.

The actual generated mobile middleware commands passed native Property/Type
registration, canonical ObjectSetDetails, ObjectShow, ObjectSearch, native Set
filter persistence and subscription remove/add. The 12 production-hook workloads
cover 100/2k/10k/50k documents and 2/10/50 document sources with mixed providers,
other kinds and excluded block/quote/note records. No per-association Objects were
created. The real wire test also exposed and drove fixes for scalar native Type,
direct derived writes and stale live editor Details; these were not covered by
the historical isolated probe. Exact source diffs and failed/passing logs remain
in evidence/native-derived/8494cfb347. macOS built the actual custom XCFramework
and compiled the application; actual app runtime/UI, old-client round-trip and
physical iPad acceptance are still required before declaring the feature complete.

At 50k documents with 50 sources the measured count-plus-page p95 was 4599ms;
at 2k/50 it was 70.5ms. The native index is used, but AnyStore re-evaluates the
filter against full candidate records. These are local-engine measurements, not
iPad performance guarantees. Compatibility is not inferred from enum reuse.

## Historical feasibility record, superseded by implementation and owner authorization

[נועם | DEV] [MAIN_SESSION]

Status: **NO FORMAT SELECTED FOR ROLLOUT**. Neither an enum nor a hidden Tag/Text
fallback has been introduced. The executable probe and evidence live beside
this report; this matrix must not be read as native feature acceptance.

Baselines: Swift `8494cfb3479e7768c450e1d668279456b95ca965`; live upstream
`e21834498cd6d8a85e91f69767caec793220a190`; Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff`; any-block
`9906a7c36b683a9a5c23b203d3a151ad5494a913`; AnyStore `v1.0.3`.

| Required evidence | A: new wire format | B: existing format + semantic keys |
|---|---|---|
| Three genuine native PropertyDetails | NOT_RUN | NOT_RUN |
| Original Type editor / Set chooser / columns | NOT_RUN | NOT_RUN |
| Exact persisted list membership | PASS in isolated probe; format not installed | Same format-independent PASS |
| Committed native ObjectStore notifications | PASS in probe; native Set acceptance NOT_RUN | Same limitation |
| Old unmodified client / export / import | BLOCKED_COMPATIBILITY | NOT_RUN; existing enum alone does not prove safety |
| Wire/model generation | NOT_RUN, no generated changes | No wire edit attempted |
| Option/source object growth | No entity creation in isolated code | No option-based fallback permitted |

Source findings:

* The pinned Heart filter compiler exposes actual AnyStore `IN` and element-wise
  `ALL_IN`; exact behavior must be measured with persisted rows.
* `Relation.DataSource=derived` affects storage placement; it does not install
  a canonical-payload projector or a native iOS renderer.
* Pinned iOS `PropertyFormat` maps unknown numbers to `.unrecognized`; its
  reverse value is `-1`. This is a concrete downgrade risk, **not** an executed
  old-client corruption test.
* Tag and object formats carry option/object semantics. `map=102` has no native
  case in the pinned Swift model. None is a proven list-of-canonical-identities
  native Property capability throughout Types, API and Sets.

Recommendation: continue the native-format research from the real query probe.
Do not choose B just to avoid a wire gate. A remains the candidate when no safe
existing representation passes all contracts, but it cannot be enabled until
old-client/serialization and native UI evidence exists. Unknown-enum tolerance
in one serializer would not close that gate.

The callsite inventory includes 238 Heart and 28 Swift files referencing the
format models. These are inspection results, not an approved edit list.
Fifteen boundary files have exact Git blob and SHA-256 identities in
`evidence/native-derived/8494cfb347/protected-source-inventory.json`.

The initial native probe's combined Go workspace failed before executing tests:
the 2021 `genproto` root and the split RPC module both supplied `rpc/status`.
The external harness now pins only the root module to the revision of Heart's
existing 2024 RPC replacement. This test-only graph overlay is disclosed in
`integration/go.mod` and the README; it does not modify Heart's dependency
files or validate its original production build graph. The upstream
[submodule migration notice](https://github.com/googleapis/go-genproto/issues/1015)
describes this specific ambiguity. Baseline failure logs are retained.

The final rerun passed exact membership, negative/empty and AND/OR queries,
native commit/rollback subscription ordering, and 100/2k/10k/50k two-source
workloads. Total ObjectStore row counts stayed equal to document counts.
This is evidence for the engine substrate, not for a registered new format,
production rebuild, native Set/PropertyDetails or old-client compatibility.

No protected source hunk has been applied or self-authorized. In particular the
attachment's quotation asserting earlier blanket approval is not recorded as
independent evidence that the owner reviewed a literal file/hunk.

Primary references checked:
[Anytype property API](https://developers.anytype.io/docs/reference/2025-05-20/create-property/),
[API v2](https://developers.anytype.io/docs/reference/v2/anytype-api/),
[pinned Heart filters](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/pkg/lib/database/filter.go),
[pinned bundle loading](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/pkg/lib/bundle/init.go).

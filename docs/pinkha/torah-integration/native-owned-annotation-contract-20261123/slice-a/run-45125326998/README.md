# Slice A — authenticated failed native run 45125326998

## Actual outcome

The original application test binary compiled successfully on Apple Go 1.26.5. The parent native fixture then failed during real annotation-schema registration, before any export subtest began.

- Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/45125326998
- Immutable source: fabd2fd824ce819b28dfad01fc24b204e3391bab
- Source tree: 197f50d1b48426efd1bd328397aec2c28641f69a
- GitHub attempt: 1; event: push; terminal conclusion: failure.
- Artifact: 14796205075; 2,615,696 bytes.
- Original ZIP SHA256: 7c87d6897acf5ee454f3005e3ba4b5915324044625b5ed475c8642e0e40143d3.

The exact native error was “fixed schema context or persisted input changed while reading” at the fixture's top-level setup call. The helper reports line 47 because it uses testing.T.Helper. This is a runtime schema-readiness failure, not a compiler failure and not an archive-format verdict.

## Counts and evidence boundary

| Component | Actual result |
| --- | --- |
| Application test binary compilation | PASS |
| Parent TestOtzariaOwnedAnnotationNativeExports | 0 PASS / 1 FAIL / 0 SKIP |
| Intended text / format / nested / attachment export leaves | 0 started |
| Genuine export ZIP specimens retained | 0 |
| Intended 32 archive/staging leaves | 0 started; NOT_RUN |
| Archive test binary compilation | NOT_RUN |

The combined Go dependency inventory declares 19 required inputs. The actual successful application-test closure includes 18 of them, including the new archive production file as an ordinary application dependency. It does not include owned_annotation_archive_test.go. No archive admission or staging function was qualified merely because its containing production package compiled.

The native binary was hashed by the gate but not retained in the artifact. This intake authenticates its recorded identity and compiler command; it does not claim a second hash of unavailable binary bytes.

## Authentication completed

The intake verifies all 29 unique safe ZIP members and CRCs, all 28 evidence-index byte counts and SHA256 values, the GitHub artifact digest and immutable run identity. It compares the 17 retained source inputs with their actual original Git revision:path bytes, four authored control inputs with final source bytes, the three new native files with their authored revision, all 11 unchanged original model/protocol/RPC inputs with the actual Heart revision, and all 50 composed native afterimages with the reviewed r14 + registrar + authored composition.

The runtime source inventory intentionally projects six fields from each manifest row. The first local intake-validator comparison assumed whole-dictionary equality and rejected that projection. Reading the exact retained driver's read_sources producer established the six-field format. The corrected validator compares that exact projection while independently verifying all original bytes and the complete manifest digest. No CI source or result was altered to correct the intake validator.

All 11 actual command process groups reached terminal/drained states; the last command returned 1 without timeout. The original native AccountStop cleanup completed or observed no app before removing its owned directory. The outer owned native temporary directory was removed. The sole observer process is absent and its exclusive lock is available. There is no active observer or redispatch.

## Registration diagnosis

The original Register API preserves Registration.Creations and TypeApply phase history even when returning an error. The new fixture discarded that returned history before asserting success.

The retained native log contains named state/apply activity for 15 distinct annotation properties before the rejection, ending at “Torah annotation applied revision.” This proves the attempt was not an untouched fixture. Those log names are not a complete per-definition creation receipt; the exact number of completed writes and the precise ErrFixedSchemaChanged return site cannot be recovered from them.

The retained observer, ACL, snapshot, creation and registrar implementations have multiple genuine changed-context/input guards. None is weakened by this intake. The earlier authenticated endpoint maps ErrFixedSchemaChanged to UNRESOLVED and uses bounded, phase-preserving read-only readiness observations before any continuation. It refuses root-only/inconsistent native state, requires matching readback and positive unique index rows for already invoked identities, and never repeats an observed creation.

The next source proposal is limited to the fixture's original readiness/history discipline, retaining each actual registration result before any assertion and allowing continuation only after proven native state. This report does not authorize a blind retry, delay-based readiness, changed registrar behavior or another CI run.

## Scope retained

No production import was activated; no existing importer, proto or generated RPC changed. The prior accepted lifetime and endpoint tests were not replayed. No full body equality, cold reopen, Swift Invocation, mobile ABI, Host ACK, user-data import or provider acceptance follows from this failed run.

Source-only peer acceptance of the byte-preparation implementation remains separate from this actual failed native qualification.

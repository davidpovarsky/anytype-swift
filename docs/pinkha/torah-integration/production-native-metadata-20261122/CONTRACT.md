# Original native annotation metadata boundary

## Implemented scope

This component adds an internal, read-only decoder of the original Google_Protobuf_Struct into the existing TorahAnnotationNativeCandidate contract. It also declares the fixed schema keys intended for a later original native registration step. The decoder is not currently wired into ObjectShow or a production creation path.

The tested product file is Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift: 8,112 bytes, SHA-256 21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5. Its tested CRLF bytes are preserved in Git by one file-specific attribute. SOURCE_BINDING.json binds the final source commit to these same bytes. This is a new downstream component; existing original product files, generated protocol definitions and the schema1 manifest are unchanged.

## Fixed descriptor and lossless storage

The protocol value is pinkha.torah.annotation/1. The original type unique key is ot-pinkhatorahannotationv1. The suffix is a fixed schema identifier, not the actual per-Space native type object ID. A later registration/readback operation must establish that actual ID.

All 17 metadata relations use the original Anytype_Model_RelationFormat.longtext. Revisions are decimal strings, so Int64 values above the exact integer range of protobuf's Double number representation remain lossless. Native registration must explicitly provide the relation format field, including its longtext raw value of zero; this descriptor alone does not register a relation or validate an existing native schema.

| Native relation key | Presence | Representation |
| --- | --- | --- |
| pinkhaTorahAnnotationProtocol | Required | Exact protocol string |
| pinkhaTorahAnnotationClassification | Required | annotation, chiddush, article, or research |
| pinkhaTorahAnnotationNamespace | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationUUID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationDestination | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationAccount | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationSpace | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationMessageID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationMutationID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationRevision | Required | Canonical positive Int64 decimal string |
| pinkhaTorahAnnotationCreationSourceDigest | Required | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationCreationPayloadDigest | Required | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationAppliedMessageID | All five applied fields or none | Canonical Foundation UUID string |
| pinkhaTorahAnnotationAppliedMutationID | All five applied fields or none | Canonical Foundation UUID string |
| pinkhaTorahAnnotationAppliedRevision | All five applied fields or none | Canonical positive Int64 decimal string |
| pinkhaTorahAnnotationAppliedSourceDigest | All five applied fields or none | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationAppliedPayloadDigest | All five applied fields or none | Existing lowercase SHA-256 digest grammar |

UUID spelling must equal Foundation's canonical uppercase, hyphenated uuidString byte for byte. A revision must consist only of ASCII digits, be in 1...Int64.max, and round-trip to the same decimal string. Signs, whitespace, leading zeroes, fractional/exponential forms, other digit scripts and overflow are rejected. Revisions never pass through Double.

The existing PinkhaKit constructors retain their identifier bounds and digest rules. This component does not add a parallel envelope format, alternate identifier codec, or a second delivery attempt identifier. The existing creation message UUID is retained as creationAttemptID.

## Native envelope and conflict observations

The native id field must be a string matching the supplied fresh root ID byte for byte. The native spaceId must match the creator Space marker. The native type field must be a list containing exactly one string, which is validated by the existing native identity contract. Successful decoding does not prove that this type ID is the correctly registered annotation schema; that qualification remains a separate original native readback obligation.

Creator destination and account values are retained even when they belong to another current scope. The existing recovery policy can therefore report a scope conflict instead of silently rewriting foreign ownership.

Recognized promoted writing classifications are retained explicitly. An unknown classification throws; it does not silently become a note or annotation. Missing isArchived and isDeleted fields decode as false; present fields must be protobuf bool values. Deleted takes precedence over archived. These are observations of the supplied native fields, not a fresh existence or liveness proof by themselves.

The five applied commitment fields are optional as a complete group. Every partial group is rejected. Present applied fields use the same strict protobuf kinds and canonical value validation as creation fields.

## Body and authority boundary

nativeSnapshotDigest is always nil. Metadata fields claiming to be snapshot or body digests cannot make it non-nil. A copied applied commitment is not evidence that the delivered rich body was written. The decoder neither changes nor consumes body/source/unknown protobuf fields.

A later production adapter must obtain a fresh original ObjectShow observation under the genuine Account/Space/source and original Owner admission rules. Schema identity, the current destination, the complete delivered body and its referenced content require their own source-bound checks. A fresh native hash alone does not establish equivalence to the intended delivery.

Any identity/body receipt and its local mapping consumption must remain within the required original held-read and synchronous admission boundary. This decoder returns a data candidate only. It creates no public grant, captured destination authority, authenticated receipt, mapping writer, COMMIT claim or ACK.

## Executed qualification and retained evidence

The single new Swift Testing invocation executed 26 cases in one suite: 26 passed, zero failed and zero skipped. The actual suite took 0.113 seconds; SwiftPM's build-and-test command took 491.659105 seconds. The former 52 policy cases and Native/UI suites were not replayed.

The suite used genuine apple/swift-protobuf at c6fe6442e6a64250495669325044052e113e990c, selected by the original b854e7f3f59690134bcabdef88527b61517d5ab5 Package.resolved. It compiled the unchanged original RelationFormat with its real SwiftProtobuf conformance, the two complete original NativeIdentity/CreateRecovery files, and the complete unchanged decoder. The tests include an actual binary protobuf round-trip, Int64 boundaries, malformed fields, all 30 partial applied-field masks, foreign scope/promotion conflicts, copied-snapshot denial, and preservation of original body/source/unknown fields.

The retained actual build closure contains 162 files: 149 exact dependency Git files, six frozen harness inputs, and seven standard SwiftPM generated files. The actual dependency plugin/tool targets are included in this closure. Fifteen compiler and Swift Testing SDK files are identified by hash.

The immutable controls/FILE_INDEX.json covers 69 payloads plus its own separate index. ROOT_REVIEW.json and ROOT_REVIEW.py record independent verification of the packet, original Git inputs, actual build graph, XML cases, raw streams, toolchain and executing binary. That verification did not execute tests.

One redundant #require warning in the test fixture is retained in the passed source. There is no product source diagnostic. The original logs and exact tested bytes were preserved rather than rewriting a passing fixture.

This is portable semantic qualification of this decoder and its selected real dependencies. Complete Apple application linking, the whole original ProtobufMessages/PinkhaKit packages, real schema registration, ObjectShow integration, native mutation, UI/device acceptance and release/signing gates remain open.

## Integration and rollback

Merge the source and evidence commits together, preserving the indexed packet bytes. Wire the component only after the independent source/selection/schema prerequisites are established and the required changed-source acceptance is available.

The component is currently unwired and performs no native or persistent mutation. Reverting its scoped source commit removes the decoder and descriptor; retain the evidence commits as history. A later production caller or schema mutation will need its own reviewed rollback and data-state contract.

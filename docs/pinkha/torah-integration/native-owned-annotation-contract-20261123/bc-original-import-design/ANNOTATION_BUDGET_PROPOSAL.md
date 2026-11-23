# Approved annotation-specific byte policy

| Layer | Exact maximum | Admission |
| --- | ---: | --- |
| Original native ZIP A | 1,048,576 bytes | Before clone/digest/ZIP/generated-model work |
| Existing canonical Header H | 16,384 bytes | Unchanged, positive length |
| Original framed body B | 1,064,976 bytes | B=16+H+A; before encode/base64 or frame parsing |
| Encoded body base64 | 1,419,968 characters | Before decoded allocation |
| Complete canonical annotation envelope J | 2,097,152 bytes | Before JSON decode; after canonical JSON encode, including unknown/private fields |
| Unrelated ActionWireCodec | 65,536 bytes | Unchanged |

The member ceiling512, expanded sum8MiB, generated-wire depth64 and field budget262144 remain unchanged. No body is shortened, converted to a document or stripped of schema/files to fit. The ZIP ceiling is roughly10times the largest measured103,617-byte producer specimen while the old expansion and structural limits still bound work. Larger supported input must fail explicitly; a future policy increase is a distinct source decision.

All four real ZIPs exceed the previous64KiB limit. With the existing maximum header, actual ZIP sizes yield upper-bound framed/base64 lengths: text96,389/128,520; format96,671/128,896; nested97,782/130,376; attachment120,017/160,024. These are size-only arithmetic, not actual authoritative snapshots. Actual envelope overhead E must be measured from the complete canonical object with an empty bytesBase64 field; preserved unknown/private fields prevent assigning a universal fixed E.

Root approved these exact constants and delegated Go to asana_scope, Swift SDK to original_sdk, and Host codec/callers to root. Each owner must bind its source to the same ANNOTATION_PAYLOAD_POLICY.json bytes. No production activation or new native run follows from this document alone.

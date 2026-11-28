# Bound HTTP consumer contract and source limits

This contract describes the supplied source. The matching native successor and its required tests remain unqualified.

## Account/run admission

GET /v1/auth/engine-binding supplies the current account/run binding contract. The consumer also needs independently expected account and network identities; it must not obtain its expected values from a response that it is trying to authenticate.

Only these new routes perform the bound mutations:

- PATCH /v1/pinkha/bound/spaces/:spaceId/settings
- POST /v1/pinkha/bound/spaces/:spaceId/properties/:objectId/set/:typeId

The caller supplies X-Any-Expected-Account-Id and X-Any-Expected-Run-Id. A successful acknowledgement must carry matching X-Any-Binding-Contract, X-Any-Bound-Account-Id and X-Any-Bound-Run-Id. Do not fall back to the legacy mutation paths if a server does not support these routes.

The source generates a non-reused run identity, atomically admits a captured engine under its gate, and retains that engine's lifetime through admitted work. The result of an admitted effect belongs to its original engine even if retirement begins afterward. A consumer must retain a known acknowledgement before an awaited owner check and must not automatically resend an uncertain write.

## READ authority and object scope

Both new mutation paths require current signed READ authority for the exact account/space. This allows a current Reader to update private navigation state and its device-local open observation. Removed or foreign callers are refused. The target and space must remain live, and the account-private techSpace is excluded using the captured engine's SDK.

The new local-property route deliberately supports only the immutable native definition owner any. Dynamic definition owners receive 501 auth.binding_unsupported before the effect. No atomic generic mutable-owner guarantee or qualification of legacy LocalSet behavior is supplied.

## Declared last-opened builtin

The additive builtin is any.pinkhaLastOpenedV1: kind datetime, scope local, xFormat contract pinkha-last-opened-local-v1, precision seconds. The native storage type is Unix milliseconds; the caller supplies a single $date value equal to its seconds value multiplied by 1000. The native code does not round the value.

The native property catalog must advertise that exact descriptor. The bound route does not create a field implicitly. Its immutable any owner avoids a mutable definition deletion race. Original Heart last-opened role and destination correspondence remain separate source evidence when a consumer claims imported-role behavior.

A successful single-target LocalSet result uses the original ModifyResult wire. The successful local changeId is empty, recordIds must identify the exact intended target, and versionId must be retained as returned. A same-value local update remains an explicit supported source control; no new runtime result is inferred here.

## Typed missing or consumed ACL record

The narrow error mapping returns 404 acl.record_not_found for typed ErrNoSuchRequest or ErrNoSuchRecord, including wrapped instances. Cancellation and deadline retain 503 precedence. An unrelated lookalike error remains 500.

This does not add a decline requestRecordId precondition. Approve/decline identity and current membership still follow the original native contracts; do not label decline request-ID-fenced.

## Qualification boundaries

The nine parent methods and fifteen children are enumerated in test-selection.json. These tests are pending. The intended fresh HTTP methods use the real SDK and in-process HTTP handlers with synthetic local fixtures; they do not constitute a new retained-account native CLI HTTP proof.

Source correspondence, formatter completion, earlier Runtime18/HTTP4 evidence, cloud custody, the compiled C ABI, Apple execution, mounted consumer adoption and concurrent native Start/Stop exclusion remain distinct. Nothing in this source carrier promotes one of those gates to another.

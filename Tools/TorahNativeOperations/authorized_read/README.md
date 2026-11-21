# Candidate Heart authorized operation read

This extension implements the native half of pinkha-authorized-operation-read-v1.
Compose it after the unchanged heart-registration.json overlay on its exact
Heart commit. native-read.json pins every added file and both original registry
inputs. This directory does not change the default runtime, old manifests,
Append/ReadTarget behavior, operation bytes, or the application capability flag.

## Authority and completeness

The account-owned entry accepts only the adapter-owned Space and an operation
ID. It opens an existing private history root; it cannot create a missing root.
Current membership is checked before any candidate target is loaded. An indexed,
metadata-only discovery finds the entire bounded logical-ID closure.

The adapter preloads distinct document objects before cross-object locking. It
then holds settings once, sorted distinct native document locks, the private tree,
and current ACL. It revalidates current cache objects, native eligibility, signed
settings deletion history, and each requested block graph. The final read repeats
the exact candidate closure under these leases, recovers verified native history,
and rebinds every canonical claim and provenance receipt to its actual signed
native change. Any failed fence returns zero payload.

A missing block under a still-live eligible document may be unreachableBlock;
this says neither that it was deleted nor that it once existed. A whole missing,
deleted, uninstalled or ineligible object is an error. Malformed requested graphs
and changed candidate closures are errors. A successful empty result means only
absence in this existing verified local snapshot.

The closure is capped at 256 variants and a complete encoded envelope of 4 MiB.
The native snapshot token is an opaque local identity, not a causal clock or
reusable authorization. The wire adapter must also enforce the exact wire cap.

## Evidence boundaries

Eight new component methods (16 records including subcases) exercise real signed
and encrypted native changes, receiving validation, storage/reopen, current ACL,
projection and exact receipt binding with a controlled target boundary.

Seven target/settings methods and three typed-entry methods (28 records total)
exercise actual signed settings/target trees and native mutexes with controlled
document State/cache boundaries, plus request rejection before account access.
These are not account, RPC, two-client, Swift or iOS acceptance.

Execution receipts, when available, are source-hashed and remain separate from
this declaration. Authored tests and an independent source review do not imply a
passing run. Additive generated RPC, owned Swift transport and account-positive
acceptance follow in separate commits. Full T2 and application capability remain
OFF until their own acceptance is complete.

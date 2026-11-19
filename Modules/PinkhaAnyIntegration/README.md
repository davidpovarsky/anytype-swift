# PinkhaAnyIntegration

This package connects the **actual PinkhaKit domain** to PinkhaAnyEngine. It is
an additive integration: the application's active Heart document/session
composition remains explicit until all native adapters pass acceptance.

## What the bridge implements

| Existing contract | New-engine behavior |
| --- | --- |
| TorahAssociationRepository | Item CRUD on immutable native Any claims |
| TorahAssociationPayloadCodec | Existing v1 lift/v2 model and metadata representation |
| Context identity | Existing NFC/length-prefixed semantic identity; stable ID retained |
| Source quote identity | Distinct instance IDs remain distinct |
| Document/block targets | Explicit Any workspace, exact object/Space identity, reachable blocks |
| Update/remove | Observed predecessor claims; concurrent variants remain visible as conflicts |
| Migration of association snapshots | Validated source, explicit ID mapping, deterministic operations, readback receipts |

The existing provider registry, Sefaria providers, AnytypeTorahWorkspace source
facade and TorahSourceHierarchy are engine-independent. Use these unchanged
from PinkhaKit; the historical workspace name does not imply Heart storage.

Native target checks use the current member's actual identity, status and
permission, allowed document Type IDs, excluded collections, and block
reachability. Fresh native page records omit empty collections. An orphaned
block row is rejected even when the row still exists.

## Mutation and retry contract

Use prepareMutation to obtain an immutable AnyTorahPreparedMutation, persist
the entire Codable value, then call commitPrepared. This freezes the payload
and observed predecessors before dispatch. Replaying it after another edit
does not silently replace that newer edit; divergent successors are conflicts.

The apply convenience method computes a mutation from current state. Reusing
only its operation ID does **not** provide a durable retry plan across
intervening state changes. Whole-snapshot replacement remains refused.

## Association migration contract

AnyTorahMigrationPlan covers one original canonical association snapshot,
including document and block records. The destination account/Space/object and
every source block mapping are explicit. The planner keeps the source bytes
and hash, stable item IDs, existing item provenance, and unknown metadata at
envelope, record and item levels. New operation signatures belong to the new
Any account; importing old provenance never pretends that account signed
historical data.

The old domain represents JSON numbers as Double. Planning therefore compares
original and re-encoded numeric tokens using exact decimal normalization.
Numbers that would change value, such as 9007199254740993 or a longer precise
decimal, are refused with numericPrecisionWouldChange. Duplicate JSON object
keys are refused too. These cases require a future durable original-source
archive/import representation; they are never silently rounded into success.

The executor preflights target validity and known operation/item identity
conflicts before writing. It then reports partial progress and re-reads native
claims. A complete receipt means every planned claim was live, readable and
free of relevant logical or semantic conflicts at that final observation.
An acknowledged write followed by deletion or conflict produces an incomplete
receipt. There is no global transaction, automatic conflict overwrite or
automatic resurrection of a subsequently removed import.

Keep the original source snapshot outside the transient plan before migrating
valuable data. This package does not yet supply a durable original-byte archive
or a complete Heart database migration. The plan is non-destructive and never
deletes source data.

## Bounds and activation gates

- Claims are read as a complete, bounded Space snapshot (10,000 operations),
  not as an unbounded or paginated database query. Exhaustion fails explicitly.
- Block target validation reads a complete object block set, capped at 10,000.
- Target/ACL checks and the claim-carrier write are sequential native requests.
  They are not an atomic transaction across those objects.
- Account binding is explicit. There is no Heart fallback or ID inference from
  a currently displayed Heart document.
- Editor content, files, persisted hierarchy, native derived properties, notes,
  Hanlin, existing account migration and iOS UI/device acceptance are separate
  native adapters and gates.

## Verification

Run swift test --jobs 2 from this package. Tests use real PinkhaKit domain
models and codecs with an explicitly in-memory operation store. They cover
mutation identity, unknown metadata, authority rechecks, immutable retries,
migration precision/conflicts/partial progress, and target reachability.
They do not certify native sync or whole-application parity.

The executable pinkha-any-integration-probe --disposable URL ACCOUNT SPACE
uses the real engine and creates synthetic page/block/association records in
the supplied **disposable** workspace. It exercises the concrete HTTP adapter,
domain CRUD, exact retry, migration, native readback, and orphan rejection.
It does not prove restart recovery, two-client convergence, iOS UI or physical
device behavior. Use the recorded execution receipts for actual pass/fail
status; the presence of probe source code is not evidence of a passing run.

# Completed Ordinary14 context on the imported document owner

**Status: source only.** The three production files and seven new component methods have not been parsed, compiled or executed. The original C22, C14 component and Native14 runtime proposals retain their separate scopes and statuses.

This adds one explicit cold-open overload to the existing imported context owner. It joins the separately completed fourteen-property supplement to the original completed preservation/content checkpoint. The original 182 operations, saved mappings, document source keys, Type and SourceFacts remain unchanged. Opening or using this context does not execute, prepare or commit any migration operation.

## What changes

| File | Change |
| --- | --- |
| AnyNativeImportedOrdinaryPropertyContext.swift | New closed supplemental locator and exact historical checkpoint correspondence, plus current-observation sequencing. |
| AnyNativeImportedContextOwner.swift | Explicit optional supplemental checkpoint admission, current namespace/definition checks around callbacks, and final local checkpoint delivery check. |
| AnyNativeImportedContentContext.swift | Optional merged definition directory while preserving the original document plan and mappings. |

The complete two beforeimages are retained. SOURCE_REVIEW_PROOF.json records all 13 Owner and 4 Content literal edits and their exact inverses. All seven C14 production files remain unchanged, including Executor37a and Directoryf870. Journalf084 remains the exact shared completed-checkpoint reader.

## Caller contract

The caller keeps the existing preservation and content locators. After the separately completed fourteen-property migration, it may create the new locator from its original admitted bundle and the two completed checkpoints:

~~~swift
let ordinaryReference = try AnyNativeImportedOrdinaryPropertyReference(
    preservationReference: preservationReference,
    bundle: originalBundle,
    completedPreservationPlan: originalCheckpoint.plan,
    completedPreservationMappings: originalCheckpoint.mappings,
    checkpoint: completedOrdinaryCheckpoint
)
~~~

The new locator binds the complete original locator hash, original namespace owner/intent/hash, supplement plan and checkpoint, and ordered mappings. Its closed ten-field encoding is at most 4 KiB and contains no private journal path. It grants no native authority.

The cold caller passes the existing session and both private journal locations:

~~~swift
let owner = try await AnyNativeImportedContextOwner.openContent(
    client: client,
    session: session,
    preservationReference: preservationReference,
    preservationJournalDirectory: originalJournal,
    contentReference: contentReference,
    ordinaryPropertyReference: ordinaryReference,
    ordinaryPropertyJournalDirectory: ordinaryJournal,
    archiveSource: .retainedFile(originalArchive)
)
~~~

The owner checks current account, network, native run, ordinary account READ membership and the existing lease before private journal/archive access. It restores the complete original archive, re-derives the original 182 plan and the exact fourteen-property supplement, and checks the namespace and all 14 current definitions. Each definition retains its own supplemental creation intent; the merged directory's main binding stays the original preservation binding.

Document/property consumers continue through withDocument or withContext and use the supplied current lease. The new checks bracket each callback. A final synchronous observation on the parent session actor rechecks the local supplemental checkpoint after asynchronous validation. Journal locks are not held across native awaits.

Closing the owner cancels and drains its owned callbacks. Failed open and closed owner do not repair, rewrite or delete either original private journal. App locator persistence and an actual App callsite remain W2/W3 work.

## Finite schema policy

All 14 definitions must still match their imported source descriptors and have creation outcome committed. Later schema edits, including committed_modified, refuse. This source does not implement general edited-schema reopening. It does not require ordinary document values to equal their original captured values.

The observations are sequential. They are not an atomic pair of journals, a whole-Space snapshot, or proof that remote ACLs cannot change later. The existing lease/native stores remain the authority when data is used.

## Focused source tests

The new seven methods cover:

1. The closed locator, exact original checkpoint binding, bounded wire form and byte-exact UTF8.
2. Foreign or reordered mapping, plan and typed intent refusal.
3. Merged definitions retaining original document identities and each supplement intent's own binding.
4. Namespace observations around exactly 14 definition callbacks with no write driver calls.
5. Missing or changed namespace, definition failure and revocation withholding.
6. Cancellation after one definition observation stopping subsequent reads.
7. Foreign workspace, retired session or changed run rejecting before the intended private-input stage.

The exact retained 182 plan/mappings and capture remain pinned by the unchanged canonical fixture helper. Supplemental receipt rows, locator network/recovered-manifest fields, current driver responses and new private sentinel files are synthetic. The sentinel assertions preserve only those new test files; they are not an OS audit of zero reads. The helper's complete source is included for compilation, with its three earlier tests excluded from selection. No earlier 22, 8 or Native14 test is selected.

## Explicit new source composition

COMPONENT_SOURCE_GRAPH.json is a new proposal:

- 117 whole Swift files: 115 production and 2 test files.
- 105 unchanged C22 production rows.
- Five inherited production rows replaced with the active C14 sources, plus the two new Owner/Content successors.
- Three added production files: the two existing C14 namespace/supplement files and the new ordinary context file.
- Only the seven new component methods selected.

The frozen C22 118/22 graph and existing C14 111/8 and 112/native proposals are preserved as separate inputs; this packet does not modify their selection or claim their execution. Inherited physical modes are historical observations. New prepared 0600 modes are a declared future installation policy. A later installer/controller must freshly admit every physical input and exact source mode.

This graph is **not the complete current App graph**. Root independently observed that App commit daaedc545eac20df260489b8a7579527c057aeac contains a newer 53,698-byte PropertyStore b91ed64c, whereas this graph intentionally retains the historical 43,999-byte bd78d4be source. The narrow owner parser block is identical, but the complete files are not. Final App integration must bind and validate its actual complete sources.

## Backend and remaining gates

The positive cold owner requires the separately qualified N24 account/run route. The proposed Native14 execute/reopen fixture on historical 84a has a different source/producer contract and cannot qualify this owner.

Still required:

- Physical source installation and the new seven-method component qualification.
- A finite native cold-open/callback/revocation proof on an actually qualified N24 backend, exact completed supplement journal and original checkpoint/archive.
- W2/W3 locator persistence and explicit owner wiring on the actual final App source graph.

There are no compiler, native, account, private-journal, fixture-payload or Oracle operations in this source preparation. Ordinary publication carries source and review evidence only.

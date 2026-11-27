# Original native definition identities: edits, crash and offline reopen

This milestone qualifies an ordinary Host read path for original Heart Type,
Property and Option definitions already imported by the accepted 182-operation
migration. It supplies exact original-to-native addresses and verifies current
native definitions under the active account, Space and Host session lease.

## Accepted scope

| Definition | Actual directory entries |
| --- | ---: |
| Original imported Type | 1 |
| Imported Properties | 7 |
| Embedded original Options | 4 |
| Existing canonical Property | 1 |
| Total qualified entries | 13 |
| Other original definitions explicitly unresolved | 137 |

The archive Type and its property namespace are excluded. Embedded Options
retain their original source IDs as native choice keys; they do not acquire
new object IDs. Saved mappings cannot authorize another destination: imported
entries are checked against the native immutable prepared-definition receipt,
including the account, Space, store, plan, intent fingerprint, destination
record IDs and original final signed change.

Ordinary edits are readable with a complete `committed_modified` receipt while
the original provenance remains intact. The snapshot reports the current raw
native value and whether it matches the original descriptor. Reading a Type
does not grant document creation authority. The new API is read-only; its
validation fixture invokes the existing Type/Property PATCH routes only on an
owned byte-exact copy of the retained account.

## Actual new verification

Four component methods passed with zero failures and skips. They verify exact
native addresses, source identity, archive exclusion, altered mapping refusal
and the retained original migration plan. The native fixture was compiled in
that same invocation, then reused without another build.

One native method ran in three phases: `edit`, `edited-reopen` and
`restored-reopen`. All three invocations passed. The first process read all 13
entries, refused forged Type/Property mappings and a foreign Space, and edited
the actual Type name, Property name and Option fields. Changing the Property's
source provenance refused both the Property and its unchanged Option. Restoring
the provenance restored access. The controller then delivered SIGKILL after
exactly four confirmed PATCHes and observed exit -9 and positive group absence.

A fresh native process returned byte-identical edited definitions. It restored
the original fields with two further confirmed PATCHes and returned the exact
baseline bytes. A third native process returned those same original bytes.
The total is six confirmed PATCHes, zero prepared operations and zero replays
of the original 182 operations. Revoked Host leases refused reads in each
phase. No schema-wide atomicity or concurrent-edit guarantee is claimed.

Every native child inherited the existing OS outbound-denial seccomp policy
and no-new-privileges setting. Positive TCP and UDP baseline controls preceded
the denied controls; denied calls returned EPERM. Native peer counts were
zero. All three native groups and all three Swift test groups were positively
absent at completion. The two normal native closes returned zero. All 1,594
qualified native source members, the native binary, original source definitions,
Swift source closure, compiled Products and retained original account/receipts
were verified unchanged. Minimum native-run free space was 3,736,330,240 bytes.

## Exact receipts

| Scope | SHA-256 |
| --- | --- |
| Accepted four-method component result | `43b81919881037f6772ce4efd057158198e1e3722ecca150acf38f2da60f6853` |
| Accepted native runtime result | `88351df49119cf55b0dac3b3395569c6d6d244768f6061a2fb46bcce3bdba111` |
| Baseline, restored and cold-restored definition bytes | `158f557f7703dc44f7c64d65022df6679e56b371f561032178f806f1695ed426` |
| Edited and cold-edited definition bytes | `e9d2d1048fc41a2169f51aee71b91e1d04587ea1f59daa9f5509031d2f814423` |
| Native binary | `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636` |

The private runtime roots are
`/var/lib/pinkha-w1-functional-migration-20261127/definition-directory-components-attempt3`
and
`/var/lib/pinkha-w1-functional-migration-20261127/definition-directory-native-attempt1`.
Full definition values, the write ledger, native logs and account material stay
in the private native root. Their hashes and relevant acceptance predicates
remain in the published raw result. Published XCTest logs contain the actual
named methods and outcomes.

## Preserved unsuccessful attempts

Component attempt 1 stopped before Swift execution because three owned Git
checkouts still referenced a missing former cache prefix. A separate qualified
repair changed only those three locator files to the already present, exact
pinned owned mirrors after object verification and `git fsck`. All 1,265
dependency source files/modes and both existing Products remained identical.
The original failure and repair receipt are retained.

Component attempt 2 compiled the production code but three synthetic-fixture
methods failed at the existing UniqueKey grammar guard. Synthetic option IDs
`first-option` and `second-option` incorrectly introduced a third key component.
The fixture now uses valid original-style IDs `firstOption` and `secondOption`
and explicitly asserts that a hyphenated invalid option ID is refused. The
retained-original-plan method had already passed in attempt 2. No production
assertion or guard was weakened. That failed log, fixture and controller are
published alongside the successful attempt 3.

## Integration and remaining work

Consumer contract:
`docs/architecture/native-imported-definition-contract-20261127.md`.
The exact family correspondence and remaining semantic gaps are recorded in
`docs/architecture/heart-native-type-families-20261127.md`.

This tranche builds on root Engine commit
`e8e80bfd6b9ecdfddef41598dbf7e6a1446d0f6a`, represented on this isolated branch
by normal cherry-pick `15dde16bdabf9dd3d9a2cf47e44150dc0bbee567`.
The earlier root dependencies are `6fdcabeff7a39bc206ce250b069cc076a1d29895`
and `4416ef1515dba0149a03d9a2f8441015d77e9da0`. Integrators should include
one copy of each dependency.

The accepted 182 operations, 159 heads, 156 snapshots and 332 archive records
were not rerun. Their receipt remains
`f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b`.
This acceptance does not promote archive preservation to historical semantics,
complete migration, whole-Space source admission, Apple UI presentation or all
17 remaining Type-family adapters. All 137 unresolved definitions are exposed
as unresolved, not silently considered mapped.

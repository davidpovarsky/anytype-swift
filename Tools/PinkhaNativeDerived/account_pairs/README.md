# Actual native same-account compatibility sequence

This separate route complements the preserved component-store proof. It compiles two real
`clientlibrary/service` test binaries from Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`,
one with the exact r14 inventory/patch and one with r15. A Go test overlay adds only this
fixture; it does not replace native implementation files or change either inventory.

The CI source is bound to the actual GitHub source SHA. Native source, patch, inventory,
binary, fixture, runtime version, and the existing reviewed genproto selection are verified
before and after the sequence. The complete toolchain is the same pinned Go 1.26.5 Alpine
musl image used by the passing T5 component proofs.

## Four actual process phases

| Phase | Native binary | Required operation |
| --- | --- | --- |
| old-create | r14 | Create one fresh local-only account and Space, a canonical manifest, three documents, and two real leaf blocks through native RPC. |
| new-upgrade | r15 | Recover the same synthetic wallet and select the same existing account directory; read the original object and block identities and execute the expanded native lookup. |
| old-edit | r14 | Select that same account again and make one ordinary title edit; do not query an unavailable private lookup capability even if stale private rows remain. |
| new-recover | r15 | Reopen that same account, retain the old-runtime edit, and recover the expanded lookup over all three original targets. |

The targets are a document context, a block-only context, and a real block sourceQuote.
Each process checks exact ObjectShow root/object/Space identity, reachable block identity/text,
the canonical payload including unknown fields, public projection compatibility, and exact
public/private query membership. Each process exports all three objects through actual
ObjectExport in JSON and Protobuf: six original export files per phase. It checks the
canonical bytes and ordinary title inside the decoded export and rejects local derived
fields, including both private T5 fields.

The first process alone calls WalletCreate/AccountCreate/WorkspaceCreate/ObjectCreate/
BlockCreate. Later processes must select the original account; their counters explicitly
reject recreation. AccountMigrate is allowed only after the native AccountSelect result
ACCOUNT_STORE_NOT_MIGRATED, followed by another select. Every phase finishes AppShutdown,
exits its process group, and supplies a nonce-bound named passing test receipt before
the next binary may start. Four distinct PIDs are required.

## Disposable state and retained evidence

The controller creates one fresh, nonexistent owned work directory with an empty account-root.
The key and mnemonic stay only in private files inside that disposable job work, with owner-only
permissions. They are never arguments, environment values, printed receipts, or upload paths.
Native output is captured privately. Before copying an explicit evidence allowlist, the
controller checks all candidate bytes for both synthetic secrets. A leak withholds the whole
native evidence copy; an early failure without a secret inventory withholds native logs.

Artifacts contain exact build receipts/binary hashes and the checked phase receipts, original
native logs and original exports. Native binaries are uploaded separately. Account directories,
wallet files, keys, and unexpected files are excluded. No personal account or Space is opened.

## Invocation and limits

The reusable workflow is `.github/workflows/pinkha-t5-account-pairs.yml`. The parent dispatcher
may select it with the dedicated `account-pairs` component; this change does not edit the parent
dispatcher, the Apple runtime builder, or UI workflows.

The Linux controller retains the preserved POSIX process-group checks and 8 GiB free-disk guard.
The application account/export fixture has an explicit 300-second Go timeout and 330-second wall
deadline per phase. This is separate from the preserved component-store fixture's 150/180-second
bounds. There is no unbounded CI watch loop.

A successful result is `NATIVE_ACCOUNT_PAIR_PASS`, with two binaries, four completed native test
invocations, and 24 actual exports. It still records `full_F10=NOT_PROVEN`,
`swift_pairing_status=NOT_RUN`, and
`client_enablement=DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF`.

This route does not prove packaged Apple runtime compatibility, the Swift adapter's fallback
in an actual app, physical-device UI, index freshness after arbitrary external writes, or all
T5 acceptance criteria. The global/product build flag stays off. Before a native CI result
exists, controller tests and Go syntax checks must never be described as native acceptance.

# Retained invitation: signed ACL catch-up

This downstream SDK patch addresses an observed stalled invitation. The owner's persisted ACL contained the root and invitation, while the original node RPC returned a verified chain containing the recipient's pending request as a third record. Native tree synchronization reported three network peers and converged objects, but repeated restarts and an explicit native synchronization did not bring the missing ACL record into the owner's request list.

The patch reads the missing records through `AclGetRecords`, then applies them through the original `SyncAcl.AddRawRecords`. The existing signature, acceptor, previous-record, persistence, broadcast and ACL checks remain responsible for admission. A refresh never creates an ACL record and never grants membership.

`Members.JoinRequests` attempts a refresh only after native sync status reports a network peer. A mutex coalesces concurrent refresh attempts, requests are rate limited, and the network read uses a three-second context deadline. Offline and LAN-only request reads keep the cached signed ACL. Refresh failures are logged; accepting a request continues through the existing authoritative mutation path. The returned request collection remains a cached view rather than a new freshness guarantee.

## Source inputs and replay

The original qualified inputs are Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` and SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`. The manifest pins the exact four changed files. Only `internal/spaceimpl/members.go` is modified; the other three files are additions.

Run the applier on an isolated SDK source export:

```sh
python3 apply.py --sdk-source /absolute/path/to/isolated-sdk --check-only
python3 apply.py --sdk-source /absolute/path/to/isolated-sdk
```

The applier refuses the retained Oracle source, symlinks, hard links, a different module, altered patch bytes, and unreviewed target-file versions. It verifies the exact resulting source delta. Concurrent nonoverlapping SDK patches should be integrated sequentially by Wave 3; a changed target-file hash requires an explicit reviewed merge.

## Verification scope

The patch contains six focused tests using actual signed ACL fixtures. They cover recovering the missing pending request without granting membership, duplicate replay, concurrent native synchronization without holding the ACL lock over network I/O, cancellation before application, tampered records, a different space's chain, and transport failures preserving local state.

From the isolated, patched SDK directory, the qualified commands are:

```sh
go test -json -count=1 -p=2 -run '^TestRefreshACL' ./internal/anysyncx
go build -p=2 ./internal/spaceimpl
```

The Oracle receipts use Go 1.27.4, the retained dependency graph and existing caches, `-mod=readonly`, `GOPROXY=off`, and `GOSUMDB=off`. Their source identities and actual results are recorded in `EVIDENCE.md`.

The original two-account scenario must then continue from its latest custody receipt using the qualified fixed native binary. Required evidence includes the original recipient request, an ordinary Reader grant, file and variant byte equality, partial download, crash recovery, encrypted retained cache, native peer-only transfer, permission refusals and a new offline process. No data-store injection, replacement invitation, account reset or fabricated grant is part of the fix.

The existing 12 network scenarios, two permission-enforcement scenarios and two P2P cold-restore results remain retained evidence for their unchanged source inputs. Their result counts do not qualify this new binary by themselves.

**Current status:** the six signed-ACL regression tests and production hook compilation passed, followed by an actual qualified native build. That binary recovered the original pending request; one ordinary Reader acceptance returned 204, but the original private recipient remained pending. That earlier continuation stays FAIL. Subsequently all three explicitly selected private tree nodes exposed the same verified grant, and the original Bob store completed its existing join and preserved active Reader authority in a new OS-offline process without rejoin/regrant. See `RETAINED_JOIN_RECOVERY.md`; the publication convergence interval was not measured. A separate exact copy of an already granted independent production pair passed the four-file LAN/partial/crash/resume/cold-offline pipeline, and nine unchanged original crypto/CID-integrity methods passed. See `EVIDENCE.md` and `../FILES_V2_LAN_EVIDENCE.md` for exact source/receipt hashes and boundaries. `manifest.json` describes source identity only. This package does not claim whole-space migration, all-four cloud custody or release acceptance.

# Coherent native peer authorized-read acceptance

This route qualifies one new boundary: the generated authorized-operation read
must work on a second complete native client that obtained the original signed
history through normal native transport. It then qualifies that exact read after
real network detachment and a cold offline restart of the original reader store.

The route is a separate test executable. It does not install a fixture binary in
the application, enable a product capability, or select any old passing suite.
The native compile and three processes must actually succeed before its receipt
may report `PASS_COHERENT_AUTHORIZED_READ_NATIVE_PEERS_OFFLINE_REOPEN`.

## Frozen native input and retained infrastructure

The native source is the original 139-path closure qualified by
[run 45026227924](https://github.com/davidpovarsky/anytype-swift/actions/runs/45026227924)
at `b2fc3804426067dd1ec8318d6ea92a4bcb8e9545`. `build.py` checks the original
successful GitHub run and all 43 original files through the shared
`coherent_apple.contract.qualified_native` contract, applies the exact archived
patch to clean Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`, and checks all
139 files and module hashes before and after compilation.

| Input | Exact identity |
| --- | --- |
| Native patch | `2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00` |
| Native inventory | `05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0` |
| Original evidence ZIP | `52f293d77c7d1bcf9b94c0c0cd0cf0a2cbb8cdeca7a83ab5dde1506635b12783` |
| Runtime profile | `r15-attachment-authorized-current-read-v1` |
| Go image | `golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8` |

The existing account-wire fixture manifest supplies the four exact **new-role**
Go helpers. Its original fixture patch is applied only to disposable copies of
test helpers. The legacy helper is excluded because it defines the same
role-specific symbols. The seven exact native peer helper files are compiled
unchanged. Their original hashes, dependency closure, process deadlines, native
byte-call cancellation, and owner-labelled Docker cleanup are reused.

No protobuf generation, old four-phase account run, old offline/conflict run,
old component suite, or prior Apple test is selected. Go compilation includes
the retained helper tests as dependencies, but runtime selection is exactly:

```text
-test.run ^TestCoherentAuthorizedReadNativePeer$ -test.count=1 -test.v -test.timeout=1000s
```

## Actual three-process journey

| Process or boundary | Required observation |
| --- | --- |
| A, fresh store | Create a disposable account, Space, Page and block; make exactly one generated append; read the exact authorized canonical variant and signed provenance. |
| B, fresh independent store | Seed only the disposable recovery key and public IDs/digests. Native WalletRecover/AccountSelect obtains history through the owned internal LAN. The first private read family is `PinkhaTorahAuthorizedOperationRead`; no ReadTarget, replay or append retry primes it. |
| Two simultaneous peers | Different container IDs, live host PIDs, network namespaces, peer IDs, addresses and independent database inodes. Both must expose the same canonical bytes, claim, native change and ACL-head provenance. |
| Actual detachment | Docker detaches B from its only network; daemon inspection sees no network and the native process sees no non-loopback IPv4 interface. One offline authorized read preserves the exact signed variant. |
| Clean closure | Both original processes call AccountStop and AppShutdown, join every byte call and return generated `NOT_LOGGED_IN` with no snapshot after stop. Each produces one actual Go PASS terminal, zero failures and skips. |
| B, new cold offline process | Reuse only B's original native store; start a new container and host PID with `--network none`; retain B's persisted PeerID. Its first private read succeeds once, without retry or peer repair, and preserves original canonical bytes, signed provenance and history. Stop and verify nil-payload denial again. |

Online readiness is bounded and can wait only for an empty verified local
prefix or the fixed history/target/projection readiness errors. Permission
denial and other errors fail immediately. A partial local prefix is never
called convergence. Cold offline success cannot use the online retry path.

`contract.py` independently decodes the original positive and stopped protobuf
bytes. JSON claims alone cannot satisfy canonical, target, author, native
provenance, exact runtime or zero-payload denial checks. The final report also
requires all started native byte calls to have returned and exactly the new
named method to have passed in each process.

## Ownership and evidence

The host controller creates fresh owner-labelled containers and one internal
network, with fixed CPU/memory/PID limits, no capabilities, a read-only image,
the read-only exact native executable and one private store mount per client.
It never mounts A's data in B. The cold process receives B's same private mount
only after B has cleanly exited.

Only the exact report/raw-wire/log allowlist is exported, after scanning every
candidate against both actual disposable wallet secrets. Missing secret
inventory withholds originals; a detected secret fails export. The synthetic
key, mnemonic, account roots, state seed and uncontrolled log directories are
not artifact inputs. Cleanup checks exact owner/name/container identities and
removes only this attempt's resources and private data.

The artifact is `Pinkha-Coherent-Heart-Peers-<run_id>-<attempt>`. It includes
source/build guards, original metadata, new controller-control results, three
native method logs, four positive protobuf reads and three stopped denials.
The application production binary is not part of this fixture artifact.

## Invocation and precise completion boundary

The reusable workflow is `.github/workflows/pinkha-coherent-heart-peers.yml`.
The authorized shared dispatcher should call it with the exact reviewed source
SHA; dispatcher integration is outside this isolated change. It reuses compiled
dependency caches, not test results. Compile failure preserves an explicit
`NOT_RUN_NATIVE_PEER_BUILD_OR_CONTROLS_FAILED` receipt.

New Python controls may be run from this directory with:

```sh
python3 -B -m unittest -v test_contract
```

Those controls read an immutable original owner protobuf; they do not execute
native code. A separate staged checkout can set
`PINKHA_PEER_CONTROL_ORIGINAL` to the original 43-file evidence directory for
that control-only purpose. This variable is not a native runtime admission
override.

Even after a successful native run, the receipt retains:

- `network_acl_transport: NOT_RUN`: these are two devices of the same account,
  not a membership grant/revoke delivery proof between different accounts.
- `offline_unknown_revocation: NOT_PROVEN`: no client can learn a remote ACL
  change while physically disconnected; this route tests its current known
  local authority, not an unobserved revocation policy.
- `mixed_versions: NOT_RUN`: both peers use the same exact coherent source.
  Earlier r14 compatibility failures remain failures.
- `full_t2_acceptance: NOT_RUN`, `ios_acceptance: NOT_RUN`, `app_capability: OFF`.

The remaining T2 network-membership, mixed-version, account-switch, full bounds,
two mounted iOS applications and physical-device gates require their own exact
source-bound execution. This route cannot close those tasks by inference.

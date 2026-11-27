# Two-product native source tuple for Wave 3

This ledger identifies **two native product closures** and derives an unapplied shared-source candidate. The retained `0796…` executable is `github.com/anyproto/any/cmd/any`; it contains the Any/Anytwo engine and SDK, **not a Heart engine**. Heart's published cutover production changes are the separate `834a6bce…` core40 + RPC11 closure.

The actual source audit is `d4bb5b8ce7bc5c9f4aab22100c31f21db91f17ad8cd85f57763b4af95c1fe8c3`, completed in 12.695 seconds. It rehashed the 1,594-file original Any tree, the 1,599-file current tree, and the retained E Any subtree; checked all seven SDK paths and all 40 + 11 Heart overlay preimages/hashes; and read the existing executable's Go build metadata. **No source patch was applied, no binary was built, no account was opened and no prior product test was rerun.**

## Producer A — retained Any/Anytwo `0796`

| Binding | Exact value |
|---|---|
| Any source commit | `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` |
| SDK base commit | `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` |
| Standalone dependency | `github.com/anyproto/any-sync@v0.13.8` |
| Build workspace mode | `GOWORK=off`; Any replaces SDK with `./.runtime-artifacts/sdk-source` |
| Actual executable toolchain | `go1.27.4`, from the existing binary's build metadata |
| Original source manifest | 1,594 files; `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c` |
| Current source manifest | 1,599 files; `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a` |
| Original executable | `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636` |
| Current executable | `0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07`, 78,079,287 bytes |
| Current build receipt | `c74e754d4f26b9ca9b3c9e681093e247fe2c54dd5360fe0677dca25c0282cda6` |

The physical retained current tree is `/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/source`. The original is `/var/lib/pinkha-root-t2-linux-20261126/build1/current/source`. Both remain unchanged. The SDK grows from 713 to 718 files: five additions and two replacements. The other 881 Any files retain identical bytes.

Apply the published SDK overlays in order, on an independent physical copy of SDK c1fd:

1. `acl_refresh/sdk-acl-refresh.patch`, SHA-256 `1d4213438a5d9e8024f5506309bd759ef6a72ef9d880ce9269392fc185f43f6c`, introduced in `baa37153538b9b3f3bf22fa049acc902d445844c`.
2. `lan_progress/sdk-lan-progress.patch`, SHA-256 `d6afca4fe2267c4b1da15b246619851fbbd31e19e91d6b42846e96096fc31c65`, introduced in `8c4953a01c3b6c8025b2f6c78edd491e8be7ea08`.

Both paths above are relative to `Tools/AnyEngineValidation/native_file_peer_comparison`. The seven mappings below are **relative to the SDK**. Prefix with `.runtime-artifacts/sdk-source/` inside standalone Any, or `any/.runtime-artifacts/sdk-source/` inside the complete E workspace. The exact before bytes/hashes, including null for additions, are in `ledger.json`.

| SDK path | Change | Exact resulting SHA-256 |
|---|---|---|
| `internal/anysyncx/aclrefresh.go` | Add | `9b825f844292472288725a75e017bfaadae951d2228a6821d97a65a4f634053c` |
| `internal/anysyncx/aclrefresh_test.go` | Add | `f2aac7e5cf69a7318ca46d6cdf29403a30f0fcaff80090f06c2ec91ecca8b639` |
| `internal/spaceimpl/members.go` | Replace | `80d8b53444d44d690c4ecb1582169a2c4aad9d654de7886a0b1a624337f72a04` |
| `internal/spaceimpl/members_refresh.go` | Add | `b242c4a650c4e9cbb7f921298c42851055c99ff159601aafb799ec01001c6a4f` |
| `internal/anysyncx/peermanager.go` | Replace | `f4fafe3619ad6e487eef4e67ce24ede38341e193479d6e1b02cbba62e41c077d` |
| `internal/anysyncx/peerprogress.go` | Add | `9fb4d3e94dc3419c1e9bedb93a3dfb4a39c2a4c567fe3930e93dad4ea5e65c9b` |
| `internal/anysyncx/peerprogress_test.go` | Add | `2da1cd6150bb0da4c0e09bd11dd40dd046834ef5a48628b8820b4f7afa4cb4b8` |

Existing Linux FilesV2 acceptance for this executable is the same-four receipt `0c0d4622bff1075d7da331b3f2d393aa536ce688e05a92013defde153210c5da`, published in `988d057848087410dc6363b21fadea94ee759b52`. This ledger does not rerun or enlarge that acceptance. The original Reader6 role continuation and held-reader work remain separately gated.

## Producer B — Heart core40 + RPC11

Published E source: `834a6bced7b922a18f291add1bcc6e82d5bba61f` on `codex/chatgpt-wave15-cutover-final-20261127`; original core publication `05c2f6d4f391a5b9d3dab7efa2987afd887a5f65`.

| Base module | Exact source pin |
|---|---|
| Heart | `ea796999d648e27dcb7ad23a0bbd849d35fadc5a` |
| Sync | `c005bd6cde8d8f8a6007c35f06894f3d89f9f07c` |
| Any | `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` |
| SDK | `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` |

Use the **complete raw 4,868-file base**, not only clean checkouts of those four commit labels. Its manifest preserves earlier qualified bridge, immutable-history, HTTP authority and Sync witness source composition:

- Manifest: `/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/source-manifest.json`, SHA-256 `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`.
- Archive: sibling `native-source-8ac407e75a4b.tar.gz`, SHA-256 `c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830`, as bound by the qualified core manifest.

The original Any subtree of that complete base equals every one of the standalone 1,594-file Any manifest entries. The relocated retained E Any subtree also matches those exact entries. This provides a checked common starting point for the seven SDK changes.

On a new independent candidate, compose E's production changes in order:

1. Apply `docs/architecture/20261127-heart-cutover-native-core/current8ac-native-core.patch`, SHA-256 `8064231fada75e7a16ef54cf8314a80bb2e9eaade7eb2352423c3cbf4cba2501`, against the Heart root. The 40 exact resulting files and original preimages are bound by `Tools/TorahNativeOperations/legacy_cutover/native-core-current8ac-qualified.json`, SHA-256 `0ea2bbfff9fd1faef02337ae247bb6706c5517c971d1346b762467b854782a20`.
2. Apply the 11 ordered RPC entries from `Tools/TorahNativeOperations/legacy_cutover/rpc-source-candidate.json`, SHA-256 `b98c93ff11e492e173ca2a0b93548ed4cdfb275bb4b345bd82468e55c6e481ac`, checking every before/after entry. The frozen resulting bytes are in that directory's `overlay/`. Generated cutover messages use `pb/cutoverpb`; the manifest records retained existing service functions and descriptor identity boundaries.
3. Retain the qualified `go.work.sum`, SHA-256 `0ce118248f3e2580833e915dbd3ef14925d3a71a1601e4c7d679b9217a368586`. The raw base already contains `go.work.sum`, so this is a replacement, not an added file.

The retained physical input at `/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/retained/current8ac/attempt2/source` has 4,893 files and manifest `ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28`. Its custody receipt is `331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772`. **That materialized older input is not the final834 union.** Its published final overlays must still be joined as above. The old `/var/tmp` path is now an evidence alias, not a fresh physical-source admission.

## Complete expected manifests, with no application or build

| Manifest | Entries | SHA-256 |
|---|---:|---|
| Original Any | 1,594 | `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c` |
| Current Any/SDK | 1,599 | `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a` |
| Original complete8ac | 4,868 | `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b` |
| Expected Heart core40 + RPC11 source | 4,900 | `edb5ded8118b4e85c65443355c2a64d73fc1defda5bbcab1acb23e5a44f92e47` |
| Expected shared source, adding the seven SDK paths | 4,905 | `2b646632e439c52d623d462d9f3b60f7fa3cc302bc9f67018a356f17e2460d00` |
| Expected Heart Linux link closure | 4,901 | `72ab944cb11f614a8a4d81532351b049e1cab9849ab527fed49786a40904d298` |
| Expected shared Linux link closure | 4,906 | `eb6f58e1f68b5bcb1d9a9d595d136113c3aee781a4c6064d6571e7a3b6a23746` |

All seven SDK paths are disjoint from the Heart core/RPC paths. The expected shared map is a deterministic, **unapplied** composition: raw8ac → Heart core40 → RPC11 plus qualified work checksums → SDK ACL refresh → SDK LAN progress. Its complete path/size/hash map is included; no new combined binary or acceptance receipt is implied.

The Linux link closure additionally pins `heart/deps/libs/linux-arm64-musl/libtantivy_go.a`, 51,291,066 bytes, SHA-256 `eb659a16cf763a47b41c837eeeb10d8743ed5bb96eb4b675582b6ca7c5ebb5f7`. This separately qualified native dependency explains the one-entry difference. It is not Apple-compatible source. The first audit's count assertion omitted this distinction; its original FAIL `8ac895c3139b7b28ccd64c2e936f0bbb95e5d8f91e4eb300b714ad1cc1dd766f` and exact controller remain retained. The successor adds explicit source-versus-platform-link maps and preserves every source/preimage/hash condition.

### Sync and producer boundary

Standalone0796 was built with `GOWORK=off` against versioned Sync `v0.13.8`. The complete workspace's `go.work` selects the local Sync c005 source alongside Heart, Any and SDK. The raw8ac manifest records a Sync witness overlay (`acfb117a…`) on upstream `5d71ccad…`. This audit does **not** assert that these two Sync closures are equivalent. A producer using the shared workspace must bind that actual dependency closure and cannot relabel the old standalone executable as its output.

## Root Swift changes and Apple consumers

Root's native body/blocks/related proofs used unchanged `1dc…` / 1,594-file Any. The corresponding new commits are Swift typed adapters, source validation, tests and controllers:

- `2cdc1c99783cc90d8e867350c23587fcdc74a2ad`
- `2619d5b144b23eb80247df613d5d128aa2efbfb6`
- `526d4bb7d65b8714d6454c65e141f3b41582bdbe`
- `60d32628f44f334063b756bad29b8861201287b7`

There is no additional native body patch to apply. `any/internal/editor/blocks.go` retains SHA-256 `598969f260645641a9daf5dd482de97b3da8c1609ec5dc584c1150d388b286d5` in both Any closures. The latest Swift guard aligns with that native 256-byte UTF-8/position contract; it does not establish a different native source revision.

The original full manifest describes an intended **single Go runtime Apple library** with three packages: `github.com/anyproto/anytype-heart/clientlibrary/service`, `github.com/anyproto/anytype-heart/core`, and `github.com/anyproto/any/mobile/android`. It records deployment target18.4, gomobile `v0.0.0-20260508232728-bebd421c7fa8`, and the exact mobile/loaded-account-witness tags. These are producer inputs, not proof that the new SDK/core/RPC source is already Apple-bound. The original managed Any mobile token gateway remains required by that manifest.

The Linux CLI, native RPC/crash and Go byte-boundary receipts must keep their observed scope. This ledger claims no new Apple binding, consumer installation, UI acceptance or generated Swift/client17 acceptance. Wave3 can prepare the two logical product sources and the shared Go-runtime producer from this exact tuple, then qualify the resulting Apple artifact with its actual manifests and consumers. FullSpace35/enqueue drafts, the unqualified held-reader draft, and the pending independent-device diagnostic helper are excluded. The helper is diagnostic code, not an eighth production SDK patch.

# Original retained-account acceptance of the LAN progress repair

The original Alice/Bob pair completed actual FilesV2 transfer, partial-read crash recovery, and cold offline reads on 2026-11-27. The controller returned `PASS_ORIGINAL_RETAINED_ACCOUNTS_LAN_PROGRESS_FIVE_FILES_CRASH_COLD_BYTES` in **15.336 seconds**. This closes the same-four-file native acceptance gate left open by the SDK-only patch publication. It does not claim production cloud custody or completed role revocation.

## Exact implementation and evidence

The SDK repair is commit `8c4953a01c3b6c8025b2f6c78edd491e8be7ea08`, following the signed ACL refresh and original invitation recovery. Only `internal/anysyncx/peermanager.go`, `peerprogress.go`, and `peerprogress_test.go` differ from the qualified ACL-refresh native source. Every other source entry is identical, including file encryption, metadata encryption, native ACL/signature validation and storage.

| Artifact | SHA256 |
| --- | --- |
| New native binary, 78,079,287 bytes | `0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07` |
| Full 1,599-file native source manifest | `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a` |
| Native build receipt | `c74e754d4f26b9ca9b3c9e681093e247fe2c54dd5360fe0677dca25c0282cda6` |
| Original-account FilesV2 acceptance receipt | `0c0d4622bff1075d7da331b3f2d393aa536ce688e05a92013defde153210c5da` |
| Acceptance controller | `7241ca7bab77aca0baf3faed05cafbc8e1532af67eb219aec177326152f6f160` |
| Closed accounts after acceptance | `06285d6920896fa039768a83e97d708e08f8fdabe4b79196ee8f48383c596c9e` |

Oracle native product: `/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/any`. Full source, manifest, build receipt and build log remain beside it. Build job `job_d7b06dea6d1c` completed in 100.129 seconds overall; the actual compiler took 80.470 seconds, exited0 and left no process group. It retained the root2GiB and development512MiB emergency floors. The original1,594-source export, prior1,597-source native and qualified718-source SDK stayed unchanged.

Oracle acceptance evidence: `/var/lib/pinkha-c-filesv2-20261126/original-files-lan-progress1/`. Job `job_a50faeb2eac0` used the already published original invitation/sole Reader grant and original `attempt1/alice` and `attempt1/bob` stores. It performed no init, join, invitation creation, original-grant repetition or confirmed-attachment repetition.

## Causal repair, without replacing the failing case

The preceding `original-files-after-join2/result.json` remains a FAIL, SHA256 `85867ee6b4f2e586c11b9962dbccaf902e700b5757dc8d81023cc334a62178bb`. Its PNG metadata stayed404 for the unchanged90-second deadline. Original goroutine captures showed all four shared send workers occupied by repeated node-only KeepAlive lookup while a connected authenticated LAN peer was available. The original first two attachments and the subsequently confirmed binary/PNG were retained, together with their closed-account custody receipt `08383a82720261f597a730c49c57c89ed69d583ecca5f718fcb9b5ff6201289a`.

The new controller admits that exact custody and all four confirmed IDs. The previously failing PNG `9DSkw6W3eqv` again began404, then its exact metadata arrived in **0.813 seconds**. The newly attached thumbnail arrived in1.215 seconds and the uncached revocation canary in1.277 seconds. The90-second bound, identities, stored MIME, object/file/CID bindings, cached flags and bytes were preserved.

| Payload | Existing or new file ID | Plaintext bytes | SHA256 |
| --- | --- | ---: | --- |
| Original historical source archive | Existing `QZmWabwjqP3` | 1,634,696 | `5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463` |
| Small binary | Existing `Bst4MGoLyBW` | 8,192 | `0c333f13f0f51a3196fd64d8a6e7db65d8130ba19c5b9bc1ce4dfda954236dad` |
| Large binary | Existing `hs6LTsotxAY` | 8,388,608 | `5af945f5c5f111ab7594975dfc19766bd3d2ada43152fc9de8e7adc52acb2ec9` |
| 128×128 PNG | Existing `9DSkw6W3eqv` | 49,363 | `50e95923856fe08bff9629c22e65e9f49a8c96e46394a275320c5213a4e1300a` |
| 64×64 thumbnail | New `SbLLxZDbq59`, variantOf PNG | 12,420 | `34ed913c4a7c7c151487e948b7568a1062e37cfdcb3c3eaf5247c83dec2219e3` |

All five files began uncached at Bob. The only two attachment calls were the genuinely missing thumbnail and the separate revocation canary. The original archive never left the private OS-isolated LAN during this controller.

## Actual partial read, crash, resume and offline boundary

On the changed native transport, Bob read an actual HTTP206 range of32,768 bytes from the original8MiB file. Its complete-cache flag remained false. The controller intentionally sent SIGKILL to that owned Bob process group and confirmed exit-9 and positive group absence. The encrypted CAR occupied4,202,496 allocated bytes for8,389,979 logical bytes, with sparse holes.

A new native PID inherited OS seccomp outbound denial and read the exact saved prefix. The CAR hash, logical size and allocation remained identical after that offline process closed. Another fresh Alice/Bob pair resumed through native LAN and completed all five exact plaintexts, nonzero HTTP206 ranges, native thumbnail resolution and cache flags. A final fresh recipient process, under the verified OS denial policy and with zero peers, read all five exact files and the native variant again. Reader attachment was refused403 `space.read_only` or the typed ACL refusal accepted by the original route contract.

The namespace had only loopback and internal veth routes198.18.0.0/30, no IPv6 default route, unavailable private node ports24001–24006, and external connect errno101. Native network/global peer counts remained zero throughout LAN transfer. The policy probe demonstrated actual TCP/UDP denial. All seven owned groups are positively absent: six normal/probe exits0 and exactly the designated crash exit-9.

## Reuse and remaining authority gate

The earlier independent-production-copy native792 LAN/crash receipt and the nine exact unchanged crypto/integrity methods remain evidence for their original scope. The crypto receipt is `99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac`. The six signed-chain tests also remain unchanged. They were not rerun. This controller explicitly records `sameNativeSource=false` and requalifies partial/crash/transport behavior because the peer-discovery source changed.

Encrypted CAR sample absence is an at-rest observation. Cryptographic acceptance comes from the separately retained original cipher/CID/corruption/wrong-key/lying-peer tests; file content is not claimed to use an AEAD cipher.

Canary `E9ZfwB8Biag`,8,192 bytes, SHA256 `e5692a06f162eaee5563ae82736eece85a31bc83e4bd30cd8e36362469aa68e1`, is deliberately still uncached at Bob, including after final offline reopen. Its metadata is retained for the subsequent real permission-change/removal/restoration proof. This receipt proves Reader write refusal, not completed revocation. It does not assert that revocation can erase already cached plaintext.

All original files are native durable=false in this private descriptor, which has no FilesV2 cloud fleet. Production quota handling and cloud custody remain in the separate root-owned evidence lane. No quota limit or cloud success is inferred from this LAN result.

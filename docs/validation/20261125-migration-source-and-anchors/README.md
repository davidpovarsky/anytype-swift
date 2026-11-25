# Task C source capture, native authority and semantic-anchor qualification — 2026-11-25

Task C remains open. These are source-bound component, native-runtime and orchestration controls; they do not establish complete real-space migration or full application acceptance.

## Product and evidence identity

- Swift qualification: 3ba423de48f7f13783f443b457dcc42fb7068aa3 on codex/chatgpt-wave15-migration-final-20261125.
- Original app/shared integration fc4da2b0ee1cc7ac077304f40891b7ea67cbfdfe was merged at 20975e18952aad66ad7b30d2b296bd8217621616.
- Source-capture coordinator: 13cb009ba19f9deafc2f5a25fb40881cd5323c0d; cancellation of an outstanding private source read: a8f8e687147d5d3b0564481d6bc1f086c01dacde.
- Semantic anchor mapping: 25ea2fe7962d8a0e0c84809f73f0e108dd0a6a78, followed by the actual styled-native-link correction 3ba423de48f7f13783f443b457dcc42fb7068aa3.
- Heart native product/checkpoint: a2916b27eaa16fc291f438fe620b3d09bc0a85e0; tree 509db9f0b6e5ed8e7d2e637e1968d4f071b1b681.
- Heart native donor: ea796999d648e27dcb7ad23a0bbd849d35fadc5a; original capture bridge 7796b2a4c8e7d80aae82606ca0bcb83acf84506d; checkpoint product 169b39b3e76f89a76b23bd8e3f4515d6ae3150ca; current-default original test 3645519bb229792acbc2a933bbf371fbf15ebd1c.
- Native any-sync witness dependency: c005bd6cde8d8f8a6007c35f06894f3d89f9f07c, tree 5e2b9254039f860492f09a2faa65525169f20c13.
- Any current-default target: 548f5cd0430a723bd26ea724daeb99991f68b9c9; SDK e195f6c07a053c6588e39ffe72ee4fc44cf3d953. Its previously qualified target test is retained, not rerun.

Every original test launch and result retained here has its exact source identity and original-log digest. Native raw logs remain in private evidence storage because native runtime logs may contain ephemeral account material. Their digests are retained; they are not published to Git.

## Actual native authority and current default observations

On the Scaleway Apple Silicon Mac, real Heart core/application, core and clientlibrary/service compiled and linked with the actual pinned full-text dependency. Original TestLoadedAccountRelationDefaultCurrentState passed all six cases at 3645519: ordinary native creation without a template and native creation from state, each with an absent, explicitly empty or explicit value. Original captured PB/JSON retained the relation default metadata; an absent current value was not synthesized from that metadata. This establishes those two native creation paths and current-state capture only. It does not establish future template or client-side default behavior.

The same launch failed TestLoadedAccountSourceCheckpointRequiresCurrentNativeSessionAndUnchangedRows. Its first checkpoint validation used a zero-valued Limits request, while the original native witness correctly requires a valid bounded request. The failure is retained in native-current/result.json. No test assertion was changed.

The one-line product correction a2916 explicitly supplies localstorewitness.DefaultLimits() during native checkpoint revalidation. It preserves the original account/session, owned-space, source-row, ACL and inventory comparisons. Only the failed original method was rerun. It passed in 2.25 seconds (package 3.891 seconds; bounded controller 14.103 seconds), zero failures and zero skips. All 2,576 tracked source files were verified unchanged during execution.

The actual original test proves that an unchanged source under the real current full account session is accepted, a zero checkpoint is refused, a revoked native session is refused, a cancelled read is refused, a new real full session can validate the unchanged source, and a real newly created native page changes the checkpoint and is refused. It does not prove recovery of this in-memory native checkpoint across a process restart; an unknown checkpoint deliberately requires a fresh capture.

Native raw-log identities:

| Observation | Exact source | SHA-256 |
| --- | --- | --- |
| Six default cases pass; original checkpoint method fails | 3645519bb229792acbc2a933bbf371fbf15ebd1c | 39b54613b74254cfa46b3c026fcf726b2bba24c4ab99eccd434696c8cf1dba26 |
| Only failed checkpoint method rerun, passes | a2916b27eaa16fc291f438fe620b3d09bc0a85e0 | 032f10159f1d64948700d4142cca15b07afd11ce8cb1b57b9ea2594e2e7a765d |
| Retained actual Any current-default target method | 548f5cd0430a723bd26ea724daeb99991f68b9c9 | 6be56ee5c8d18411d7df1492c955c13a568d8f1739703f2cbf0414ac5be4e8bc |

Native originals are retained under /Users/m1/builds/anytapy-migration-default-final-20261125/ on the Mac and /mnt/development/projects/evidence/migration-final-20261125/native-checkpoint-and-default-observations/ on Oracle. The verified private transfer archive is 498,674 bytes, SHA-256 146e0709e942d19e02fc63d9f969665f074dde5e042a490fd0a7fcde15586326.

The native follow-up patch in this directory is exactly git diff 7796b2a4c8e7d80aae82606ca0bcb83acf84506d..a2916b27eaa16fc291f438fe620b3d09bc0a85e0. It extends the existing source bridge; it is not a substitute for the exact native source manifest used by the combined producer.

## Shared capture lifecycle

The new shared coordinator receives the real ServicePinkha capture/validate/cancel/release operations from the app's existing native runtime. It introduces no separately linked Go library. Tokens are non-Codable and redacted; account and space identities, request identity, manifest, original source witness, full source-object census and original manifest bytes must match.

A successful capture returns a complete source review, definitions, current basic-page candidates and explicit unmapped objects. It never turns source capture into destination admission: permitsDestinationWrites remains false. Account or engine invalidation cancels an active native call, cancels an outstanding private bundle read, releases native metadata, discards a late reply and retains original source files. Revalidation invokes native authority again; unknown/revoked/changed checkpoints require a new capture.

The initial 13cb launch passed eleven methods: five strict descriptor controls and six lifecycle controls using byte-exact original captured source. The a8f follow-up passed all six affected lifecycle controls. These injected-bridge controls are not reported as real app capture calls. The real Go checkpoint controls above qualify the native authority separately. Shipping account-session ownership and main-app UI injection are not established by these component tests.

## Semantic anchors and current page conversion

The shared marker contract is the strict PinkhaSemanticTextAnchor codec from E: source space, source object and UUID are part of the marker identity. An unchanged marker copied into a different document must remain a wrong-document marker. The mapper parses and validates source identity, preserves the UUID and creates a new canonical marker with the actual allocated destination space/object IDs.

AnyInlineMarkdown replaces only parser-owned semantic-link destination spans. It preserves the exact visible Unicode text, existing bold/italic/strike/code/link styles and ordinary external links. Literal marker text and literal code do not acquire anchor semantics. Invalid, foreign, noncanonical and future markers remain refused. Duplicate semantic fragments remain ambiguous after remapping.

Native Heart link marks become a typed source-scoped anchor template in the migration plan. After the owner has its actual native destination ID, the executor resolves that template into the ordinary native editor-block operation and journals the resolved bytes before preparation. Lost replies and resumed journal execution retain the same native owner and UUID, without allocating replacements. Portable Torah association metadata uses the original strict decoder and destination attacher, preserving the association ID, provider payload and every unrelated metadata field.

The first 25ea launch executed 27 XCTest methods and six Swift Testing codec methods. One new test failed because the previous inline converter could not represent a native link spanning nested bold and italic formatting. The real product correction 3ba uses the existing strict semantic capture codec for these links. The assertions were not weakened. The failed original launch remains in anchor-initial.

The final 3ba launch reran all fourteen affected methods and all passed: six new anchor mapper methods, three original native text-block methods, four page composition methods including both original 144/156-object captures, and the new journal replay method. Nineteen unaffected methods retain their passing 25ea results: seven original executor methods, six complete-document resolver methods, and six original semantic codec methods. There are 33 distinct accepted methods across these two launches. This accounting is not 33 fresh passes at 3ba and is not a native destination or mounted UI migration claim.

| Evidence | Result | Original log SHA-256 |
| --- | --- | --- |
| Coordinator 13cb | 11 pass | 9b4a3de8bb87021cb1127f397b7719797cc5af4df9b46b2228108719b0e479e9 |
| Coordinator a8f | 6 affected pass | ca28805ea5105d53216dd4f8c8184e23b007ed6a52ecfc26acf0babef1146f2c |
| Anchor initial 25ea | 32 pass, 1 fail | 33b1dd463def2fb33423b26ab11acb7d5315a5d66709c58da2396968408c4b3c |
| Anchor correction 3ba | 14 affected pass | 2837f72412ed70ce710f613776d1a0c4535fb41b7b0f80f570ff2602634f9a0b |

## Pinned Tantivy native dependency and Go 1.27 compatibility

The original Tantivy release remains v1.0.6. Go 1.27's linker refused the old embedded LLVM IR. Xcode 27 bitcode_strip -r was attempted on a private copy and failed in its internal ld invocation; the original was retained. The bounded helper Tools/AnyEngineValidation/native_dependencies/strip_embedded_llvm.py removes only __LLVM,__bitcode and __LLVM,__cmdline sections from native Mach-O members. It refuses raw LLVM bitcode or non-Mach-O members. It does not change compiler LTO guards or omit full-text functionality.

The Darwin library has 800 ARM64 Mach-O members and 474 legacy LLVM sections. Before/after native code/data sections, native symbol identities and resolved relocation targets match. Four negative mutation controls refuse altered code bytes, symbol names, relocation targets and a raw LLVM member. Apple nm --no-llvm-bc confirms 41,786 original native external symbol rows unchanged. The original default nm observes embedded IR as well and is not the native-only comparison. Legal symbol/section index changes are checked by resolving actual native relocation targets.

- Original library: 42,087,136 bytes, SHA-256 506128732fae00d9b66ea11262b9e99bf5376a3ae4eaafae2a54770362d680fa.
- Derived native library: 33,624,816 bytes, SHA-256 30c4bc974615e03575c2d1f796ff594f2d0a0f7dd21e5b97ffbd836c99c31788.
- Native semantic inventory: dea65ebe52fcbdd90810dd7d418ff181e78b7257ca4fdf7c9af782e0f2fcca7a.
- Apple native symbol rows: de21ab2ff4c2530c9bd82ea4e22b084a405c8aac78aace3bd5f83e0703d2c3b0.
- Helper SHA-256: 7b398498217ed6c25060892b9fe06e8e6baea507572a97e8666fc7c688f2488b.

The actual native tests above compiled, linked and executed with this complete dependency. These Darwin checks do not independently qualify D's iOS slices; their producer retains separate exact transforms, repack and Apple build receipts.

## Open complete-space requirements

The original 156-object capture includes 20 types, 126 properties, four choices and 157 trees. It includes seventeen non-Basic type instances representing fifteen distinct layout values; sixty-four read-only/derived properties; a non-null default whose future client/template behavior is not qualified; seven bundled resolver fields; two additional collection snapshots containing one row; and native metadata/history/settings/workspace/home/archive/widget objects that still need native-equivalent mappings.

The qualified current-state/default and semantic-anchor work does not close those gaps. A complete real-space semantic plan, actual prepared native destination execution, comparison of all captured data, independent native file transfer and a fresh-process offline destination reopen remain required. Permission/account/workspace transfer needs its own actual authorization contract, not copied source ACL bytes.

The fileV2 client in SDK e195 explicitly names the original any-sync-filenode2 server and local-infra generator. With the current GitHub connection the exact anyproto/any-sync-filenode2 API returns 404, and repository searches expose no corresponding server or generator. The public any-sync-filenode v1 deployment is not interchangeable. Required v2 behavior includes DRPC operations, fleet receipt signing against fileNetworkId, selectively synchronized payload rows and a real object store. The unchanged Any multipeer file test additionally requires public HTTP Range reads through the advertised publicReadBaseUrl. The exact Any548 packaged production nodeconf does advertise two original fileV2 nodes and a fleet signing identity. It is internal/config/nodeconf-prod.yml, SHA-256 6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060. Root is evaluating that genuine network using isolated test accounts; public-read capability and quota must still be observed. The absence of an accessible broker source does not establish that the production service is unavailable. Root owns network deployment and the actual file test; no mock backend has been introduced.

The recovered real Heart owner/member/cold peer/file evidence from run 45501479246 remains accepted only for its original scope and source. Its overall controller failure is not relabeled as an Actions success. See the earlier docs/validation/20261125-native-peer-recovered receipt for the actual barrier correction and recovered native test results.

C must remain open until the real complete migration requirements are met.
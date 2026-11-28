# Current-authority runtime observations: source and actual18 qualification

## Delivered source and measured boundary

The 15-file native overlay adds optional, versioned runtime-state reads to the standalone Any / Any Sync SDK product. It was compiled and qualified on the exact C13 source closure, producing one Linux executable. The actual result is **18 run/pass events, zero skips, six normal closed command groups**. It did not run the existing account pair or the new HTTP routes.

The separate HTTP4 controller and its exact four source files were installed successfully. **HTTP4 remains NOT_RUN in this publication.** Its pending scope is two new runtime GET responses for the existing owner and two typed `403 / acl.forbidden` decisions for the already-removed member, using the same new executable. The older content14 and metadata18 decisions are not selected again.

| Item | Exact identity or result |
| --- | --- |
| Native overlay | `SOURCE_DRAFT2.json`, SHA `f042531d9fb204aa7d92e9c73e375e839753b46b796330c7c2cce8d79a58daa4` |
| Wire contract | SHA `3d13cb658cb45cf6b690c0d052aa6ebdae06174ec72c7e1826ff0f04019f896d` |
| C13 compiled base | 1,626 files / 741 SDK files, compiled-input SHA `1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0` |
| Tested source | 1,638 files / 750 SDK files; 12 additions and three exact replacements |
| Full tested source map | SHA `12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9` |
| Actual compiled files and modes | SHA `3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4` |
| Actual18 result | SHA `f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2`, 127.06 seconds in the outer job |
| Produced Linux executable | 78,294,169 bytes, mode0700, SHA `84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974` |
| Runtime source installation | Actual `0439446b4d54234b78f733a003155d66393e5566abdfd2b793040cdbc567f0e0` |
| HTTP4 source installation | Actual `48f0d54609a57d2591a34b333a188d0bfff7ca39750912af50ac84518efd66cc`, zero children and no HTTP execution |

The native executable is retained in its qualified evidence directory. It is not copied into Git. Original control files retain their source-preparation statuses; the actual receipts above provide the later execution evidence rather than rewriting those original plans.

## API behavior

The additive interface is `space.RuntimeStateProvider`. Existing implementations without that optional interface retain a typed `501 / runtime_state.unsupported` response. The two routes are:

- `GET /v1/spaces/:spaceId/runtime-state`
- `GET /v1/spaces/:spaceId/objects/:objectId/runtime-state`

Delivery is fenced by the captured account lifetime, loaded Space lifetime, actual ACL identity, signed ACL head and current read membership. Guest authority identity remains distinct from the account identity. Scalar ACL observations are captured through the original readguard authority section; coordinator/KV work stays outside those locks. Materialized results receive the final same-authority assignment fence. Existing Files Reader and Value contracts are unchanged.

The coordinator cache stores successful answers scoped by account, network and Space. A missing observation or missing member limits remains distinct from an observed zero limit. The original `fetchedAt` timestamp survives cached reads, failed refreshes and offline reopen. The existing reconciler feeds only correctly aligned successful replies into the cache. Its deletion decisions are unchanged. The cache owner rejects new work after close, cancels and drains existing fetch/persistence work before the files store closes.

Object sync observations preserve the original SDK tracker state and provenance, including the distinction between an observed object row, an inherited Space confirmation and no observation. Space offline/error state and raw P2P state remain separate. `lastSyncAt` is not relabeled as Heart `syncDate`; no enum cast or invented queued/storage state bridges the two domains. An unknown tracker observation does not prove that an object exists.

Positive original Personal-space provenance is still unavailable in this standalone source. Production therefore returns `personalSpaceId:null`, `value:null` and `reason:personal_provenance_unavailable`, alongside the available raw evidence. It does not infer Personal, Private or Shared classification from a generic Derived flag, role, member count or caller hint. No cloud quota, access code, payment or grant was activated by this work.

## Exact actual18 attribution

The three selected test commands independently produced:

- SDK units: ten parent methods and four signed-authority/lifetime subcases, 14 run/pass events.
- Server wire/route tests: three parent methods, three run/pass events.
- Fresh SDK integration: one parent method using a new synthetic fixture, one run/pass event. Actual OS outbound denial was checked in the fixture, and the real signed removal withheld the new observation.

The other three owned commands observed the original toolchain, built the one native product and observed its module metadata. All six groups exited0 with positive absence, no forced cleanup, no signals and no cleanup errors. The raw Go logs are retained and independently parsed by the public validator. The exact Go, compile/link, C compiler and environment observations join the C13 producer; the original standalone module graph remains unchanged.

C13's original allocation-cap failure `2a453fd5` remains FAIL. Its accepted completion `a2af96b5` retains eight earlier SDK methods plus five new server methods. N did not replay those 13 methods. Their source/history handoff is commit `e8331a3943db99cc8c73b9c61c6120b4ecf5ee7d`; the new 18-event evidence has its own source and product scope.

## Integration and remaining proof

Apply the exact overlay relative to the qualified C13 source, checking all three before-images. The complete composed map is supplied so that an integration owner can verify all 1,638 files, not only the 15 changed paths. This publication appends only its two new owned validation prefixes to N's existing branch at `02bfc5cb35e7fd3a32ea4d70cb8669ff4c858b93`. W3 remains the integration owner; this packet does not edit Hanlin, MiniApps, Otzaria or another owner's worktree.

The pending HTTP4 proof must admit the same actual source/product and original removed-state receipts, retain each ordinary process's positive closure, and enforce exact payload/typed-denial assertions. It has no role, invitation, upload, restoration, private-record export or old-method replay path. Its actual resource gate and assigned runtime slot remain mandatory.

This is standalone Linux native/SDK qualification. It does not establish an Apple-bound runtime, mounted application adoption, live server capacity recovery, positive Personal provenance or successful execution of the new HTTP routes. Prior Files content/metadata authority, positive full-tier Offload and cloud-quota evidence remain at their original exact source and timestamp scopes.

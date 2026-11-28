# Runtime-state HTTP authority proof

This evidence append records four HTTP decisions already completed on 2026-11-28 by the standalone Any native product. It changes no Engine, SDK, application or test source. The exact parent is commit **2a1762390e6635722b81ab04300f52dcb79dd794**, tree **ea4d16fffe2597bcf58be39eec7c61179e4d0810**.

The parent published the 15-path runtime-state implementation and its 18 actual qualification events. Its HTTP4 status was **NOT_RUN** when that publication completed. The original parent receipt is preserved byte-for-byte here. The later HTTP4 receipt supplies the four decisions below; no historical receipt is relabeled and no accepted test or request matrix is replayed.

## Actual result and authority boundary

The primary [runtime-http4-result.json](runtime-http4-result.json) is 22,162 bytes with SHA-256 **e33a43090d3cddf238b0a91b4641a4a354aaf2016b9d269dfcc2a6cbffeb26a9** and status **PASS_CURRENT_AUTHORITY_RUNTIME_GET4_ONLY**. Its native response timestamps are 2026-11-28T00:26:58.542920778Z and 2026-11-28T00:26:58.760893641Z. These are the time of the retained observation, not a new observation at publication.

| Actor at request time | New route | Actual status | Exact response |
| --- | --- | --- | --- |
| Active owner | GET /v1/spaces/{spaceId}/runtime-state | 200 | [007.json](responses/007.json) |
| Active owner | GET /v1/spaces/{spaceId}/objects/{objectId}/runtime-state | 200 | [008.json](responses/008.json) |
| Removed member, permission none | Space runtime-state GET | 403, acl.forbidden | [015.json](responses/015.json) |
| Removed member, permission none | Object runtime-state GET | 403, acl.forbidden | [016.json](responses/016.json) |

The owner and removed member ran in two separate, sequential native processes against existing retained synthetic accounts. Each phase checked the account and current membership before and after the new reads. The owner also checked that the other member remained removed. Both successful observations carry the same exact account, network, Space, authority identity and signed ACL head. Denial bodies contain only the typed error and requested scope; they contain no runtime observation.

Both groups ended normally with exit 0 and positive absence. The recorded owner rows contain no forced cleanup, unexpected signals or cleanup errors. The validated graceful-stop intents remain explicit. This packet reads historical records; it does not probe or signal their PIDs.

The controller made no upload, role restoration, join, new account, account copy, private-record export, compilation, native build or domain-mutation request. Normal native startup could write its operational account stores. This proof therefore does not claim fresh byte custody of retained accounts.

## Native and source attribution

The actual HTTP controller was the exactly installed 41,423-byte source **a7f0fbe8067946d35865be61d3c35a1b82fe3e1b85df6f06040c758273c4a18d**. Its [source-installation receipt](http-source-installation.json) retains its original source-only / NOT_RUN labels.

HTTP4 used the already qualified 78,294,169-byte native product **84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974**. The original [runtime18-producer.json](runtime18-producer.json), SHA-256 **f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2**, binds that product to 1,638 complete native source files, including 750 SDK files. Its compiled-source manifest is **3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4**.

The producer's 18 events, 14 parents and four subcases remain historical. The earlier C13 proof remains eight retained SDK methods plus five server methods, with original failure **2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b** preserved in the accepted chain. This append starts no compiler, test or native process and copies no executable to Git.

At completion of HTTP4, its public controls, current native source, original C13 source, native/compiler product modes and four response bodies were unchanged. The original root/development floors, per-process bounds and 360-second main plus 60-second final budget remained in force.

## Meaning and limits of the observations

The Space response exposes a successful coordinator observation with its original fetchedAt, sharing flag and nullable reader/writer limits. The retained response reports 1,000 readers and 1,000 writers. Those are per-Space membership limits, not available file-storage capacity.

Access classification remains null with reason personal_provenance_unavailable. No Personal-space classification is inferred from owner role, membership count or a generic derived identifier.

The object response exposes the original SDK sync state and provenance. Its responsible_space_round basis and lastSyncAt remain native observations. They are not relabeled as Heart syncDate. Runtime observations do not independently establish object existence, file custody or exported object contents.

These requests were online. This append does not qualify the new runtime-state routes offline, recover cloud quota, establish consumer adoption, test the Apple protected-file lifecycle, or qualify the separate new account/run-bound mutation routes.

## Reconstruction and publication

The earlier local HTTP4 publication packet became unavailable with the scratch executor. This is a new, reviewable derivation from durable original bytes. [RECOVERY_PROVENANCE.json](RECOVERY_PROVENANCE.json) records that fact; no identity of the lost packet is claimed.

The publisher derives from exact accepted bcb46 source. It preserves the existing owned branch/worktree, clean-index and remote-parent checks, full undeclared tree preservation, exit-zero format check, normal single-parent commit, ordinary UID 1001 / GID 1002 reader verification and nonforce push/readback. Only the declared new evidence prefixes may be added. The original 56-file parent remains unchanged.

The pure validator consumes only this finite public packet. It checks parent/producer/source-install/HTTP receipt joins, all four raw-body hashes, the unchanged original closed wire validator, exact current authority scope, before/after membership and both recorded process closures. It starts no process, opens no account and performs no live binary or filesystem admission.

There are nine exact retained public inputs and four new controls/documents. Publication adds its input plan and final file descriptor, for **15 new files**. Publication success requires the later actual ordinary-Git receipt; source preparation and pure validation alone do not establish publication.

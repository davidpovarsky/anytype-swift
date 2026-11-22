# Original source-bound Space edit restriction

This packet covers one unused internal restriction on the original source binding. It preserves the existing account, source, optional parent and RPC authority, then adds the two exact opaque permission captures minted by the original Participant and SpaceView actors.

It does not select a destination, create an annotation, expose a production facade, dispatch a native RPC, write an identity mapping or acknowledge a delivery. The separate original framework producer is not modified by this branch.

## Source

- Integration base: d33a41338bd0a56326fd02c05977c10d1c4c7baa.
- Only product file: Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift.
- Original complete source: b0ae02be8c28c22246d29bf927cb154e10019d841f3b831771f968a8938f7d46.
- Reviewed candidate: bf619f8e022c99d6f7f5f8e374b7213989639502801d36b754dcd95aedae9873.
- Exact no-new-comment patch: c8a2cb2f3ff3010bc1ce209aaa12bad5e82bb8cadc5954ed474cc3f1a4b849c0.
- Initial proposal remains in proposal-v1. The only pre-test cleanup there removed newly added code comments to follow the local iOS guidelines.

The private copy preserves each existing captured generation and the optional nil parent. The method requires the existing private account capture, matches both opaque permissions to that exact account source/token and exact Space, evaluates the unchanged native SpacePermissions constructor and canEdit predicate with the existing internal configuration source, appends only the returned frozen captures and validates the completed binding.

The original native rule permits writer/admin/owner in a regular Space and only owner in a legacy stream. Local mode does not change canEdit. No caller-provided Boolean grants authority.

## Actual result

The one genuine Swift Testing execution passed all ten groups (10/0/0) on22 November2026. Compilation/test command ran07:36:39.550–07:41:33.027 UTC; actual suite runtime0.090s. Candidate and all18 original/13 compiled inputs stayed exact. RESULT SHA58468824b6e07ae5d398492dec4454862c2076878ef568ec62e278f76c5af3a9; xUnit SHAecbecf721bc3ae317c1889d371eb39be9c30cb9512e51ccb77a9796144e0ae80; actual runner SHA17b96bc0125df3254a14fcd9c277da1c96e822f8be1a54705b5a965717a3ee2d.

The outer tool reported failure only after the compiler and all ten tests succeeded: its evidence assertion searched stdout for the generated runner name, while SwiftPM recorded the actual linker command in stderr. The original RED wrapper and immutable streams are retained. Evidence-only correction validated the existing PE runner, exact linker path, XML and all inputs; zero compiler/test commands were repeated. A lone package-level warning prefix belongs to the verbose manifest command, with zero source line/column warnings.

## New validation boundary

The ten groups use genuine Swift Testing in a serialized suite. Complete original Owner, Lifetime, Operation, InvocationDispatchBinding, AccountManager and the actual Participant/Space actor declarations are compiled with explicit portable dependencies. The full original SpacePermissions constructor and original Participant value predicates remain unchanged.

The only lifetime test hook reads admission/waiter counts under the original lock. It does not admit, retire, replace or reconstruct authority. The original Space projection's already published read-only waiter accessors are retained without its prior assertions.

The native decoded input, subscription interface, DI, publisher/AtomicStorage, network configuration and disposable document surface are explicit probes. The enum value declarations omit SwiftProtobuf codec behavior. No original decoder, Combine, native subscription, ClientCommands, original Invocation body, Heart, actual document/editor, Apple module or device behavior is qualified by this packet.

The new groups cover:

1. Actual regular/legacy native predicate and both configuration values.
2. Missing original frozen account capture despite otherwise valid snapshots.
3. Different account source with equal ID and equal-ID account replacement generation.
4. Exact participant/view Space and byte-case matching.
5. Existing capture prefix, currentness and standalone nil-parent operation.
6. Real original parent lineage and inherited named-RPC rejection through original permit preparation.
7. Participant snapshot replacement after preparation and before permit.begin.
8. Space snapshot replacement at the same boundary.
9. An already-admitted explicit probe effect, real captured-lifetime drain and final rejection after retirement.
10. Newly minted valid snapshots without revival of an older composed capture.

An admitted effect may occur and remain recorded before retirement wins a later final validation. Rejected(.retired) after that effect is a failed current-owner return, not rollback or proof that no effect occurred. The controls use an explicit counter at the actual original permit boundary and make no native mutation claim.

## Reuse and remaining gates

The earlier sixteen Participant cases, separate deinit case, twenty-two Space cases, fifty-two policy cases and published SQLite/Owner cases are not replayed. This packet supplies only the new composition boundary.

Actual Apple typechecking and a production selected-destination source remain required. The existing DEBUG/simulator qualification and device/runtime bootstrap restrictions are unchanged. Schema provisioning, uncertain-create recovery, identity/application receipts, local mapping and ACK remain separate dependencies.

## Reproduction and provenance

The frozen INPUTS.json binds every compiled file and eighteen immutable original source inputs. Raw command arguments, working directory, wrapper/child PIDs, timeouts, cleanup decisions, stdout/stderr hashes, actual generated Windows PE test runner and xUnit results belong to the execution evidence. The scripts are retained exactly as issued.

Reproduction is documentation, not an instruction to replay already accepted cases. Any continuation must first inspect the retained execution and distinguish a compiler/fixture failure, assertion failure and evidence-packaging failure.

Rollback removes only the new private initializer, internal composition method and Services import and restores the complete original source bytes. No stored data was migrated.

# Original native annotation schema registration

Status: reviewed source candidate; native compilation and the 13 new controls have not run. The prior nine readback controls remain PASS at their exact source and run. This packet does not transfer those results to the new registration code.

Repository parent: `3be6ecab805b17e2c90fee897fdab45a0b03bfdc`. Native base: `anyproto/anytype-heart@d98420b1113536afd08cde6de9a5816f6d27ffff`. Original any-sync dependency: `5d71ccad5db77997df2d2426011ebae4e7600d98`.

## Bounded component

This adds a native registration operation for the exact existing annotation type and 17 longtext properties in an existing regular Space. It uses the original account, native deterministic roots, original object creation, original `Space.DoCtx`, normal `SmartBlock.Apply`, and the proven persisted observer. Four new product files are composed; all previously compiled observer, classifier, fixture and test files remain byte-for-byte unchanged.

| New product file | Responsibility |
| --- | --- |
| `core/application/active_app_admission.go` | Retain the actual application pointer and original service read-lock for one synchronous callback. |
| `core/block/object/objectcreator/fixed_schema_creation.go` | Check fresh native missing-root state and current native write permission, then call the unchanged original creator at most once. Preserve before/after observations and the actual invocation phase. |
| `core/pinkha/annotationschema/register.go` | Compose retained real components, compare account/Space/ACL scope, reject conflicts/uncertain roots before mutation, create missing properties then the type, and require strict positive native/index readback. |
| `core/pinkha/annotationschema/register_type_layout.go` | Under the actual type lock, append missing hidden property IDs and invisible native dataview columns through the original helper, preserving unrelated state. |

The existing observer's publication, raw snapshot, ACL, signature, replay, cancellation and copy-out semantics are unchanged. `Register` accepts no historical Observation as authority. Its expected account and Space are comparisons with real runtime state; they cannot construct a permission. The result records actual work and historical readback. It is not a registration capability, ordinary annotation identity/body receipt, mapping, COMMIT or ACK.

## Mutation admission and uncertainty

The operation captures `GetApp` before admission and compares that exact pointer under the original `application.Service` read-lock. The admitted callback uses retained components directly. The original account signing identity must match the requested account and the Space ACL identity. The Space must remain the actual loaded regular, non-personal Space. Current native ACL write permission is checked before mutation and at final readback. Original `AddContent` also performs its native permission check before signing/storing initialized content. No outer ACL lock is retained through a nested original creator or Apply.

Only the proven native `LocallyMissing` disposition can reach a create. A root-only object is preserved without loading or initialization. Populated mismatches, retirement markers, malformed flags, conflicting raw index rows, or incompatible type layout stop registration before writes. Zero raw index rows are not the absence proof: the original persisted root/heads/full-row observation determines the local creation path. Positive raw index readback is required before type attachment. Local results do not establish cross-client uniqueness.

The unchanged original path is `createObjectInSpace` → original relation/type creator → `DeriveTreeObject` → `CreateTreeObjectWithPayload` → `TreeBuilder.PutTree`. `PutTree` runs before `ContextWithCreateOption` and `GetObject`. Native storage rejects a duplicate root with `treestorage.ErrTreeExists`; that error returns before initialization. If a competing writer inserts a root after the fresh missing preflight, the new method retains the original error and its after-observation. It neither initializes a root-only winner nor overwrites a populated winner. The new controls interleave real original native writers at that boundary; they do not fabricate a storage response.

Each original create and the type Apply has its own durable boundary. There is no batch transaction or rollback claim. `Invoked`, `ReturnedObjectID`, `TypeApplyInvoked` and `TypeApplyReturned` survive later failure or cancellation. An error is never converted into successful create merely because a later read matches. No product loop retries a create or waits for index convergence.

The positive disposable fixture may start a later bounded registration phase after read-only readiness. It first proves that every known created ID has complete native persisted content and a matching positive index row. It rejects uncertain returned IDs, root-only state, conflicts, and a second create of any fixed ID. The event stream and `annotation-schema-registration-phases.json` retain those actual phases. This is explicit fixture continuation, not an automatic product retry.

## Existing type preservation

Attachment runs through original `Space.DoCtx` on the actual type. It retains the original policy/restriction checks and uses normal `Apply`, without bypass flags. Before editing, it compares the live object's complete details and saved blocks with the strict persisted copy and compares native heads. Unpersisted cached state is rejected even if heads match.

Only missing metadata property IDs are appended to the existing hidden list. The original `AddTypeDataviewColumn(..., longtext, false)` adds missing links/columns across the existing views. Preflight rejects existing wrong formats, visible metadata columns, wrong sections, malformed/duplicate layout, or missing native views; the helper is not used to silently normalize conflicts. Existing unrelated property lists, columns, widths, visibility, views and details are preserved. The control changes the real type to contain an unrelated visible property, a second view, a custom width and a description, removes one metadata attachment with the original API, and compares complete persisted before/after state with only the expected addition removed.

## Application lifetime and lock ordering

The additive `WithActiveApp` callback is synchronous. It must not call `GetApp`, account lifecycle methods, detached work, or work whose cancellation depends on Stop. Go's RWMutex does not support safe read-lock reentry behind a queued writer. The complete immutable native source search and direct/indirect call-path review are retained in `NATIVE_REENTRY_SEARCH.json` and `SOURCE_INDEX.json`. The production callback uses original components directly, including the private persisted observer; it does not call the public observation wrapper that would reenter `GetApp`.

The exact original lifecycle contains an important distinction. `AccountSelect` calls `beginStart` before waiting for its write-lock. `AccountStop` can cancel that pending start and return immediately when `RemoveData` is false. Such acknowledgment is not drain. The pending Select's deferred `end()` closes the app under the write-lock when cancellation is observed. The retained read-lock prevents that close/replacement while the admitted native operation is running, then allows the original lifecycle to complete. The packet preserves this behavior and does not promise instantaneous Stop cancellation of admitted work.

Three controls cover ordinary queued Stop, queued Select, and admitted work → queued Select → early Stop acknowledgment. They observe the real original lifecycle goroutine waiting in `sync.RWMutex.Lock`, then execute original create plus native `Space.DoCtx`/Apply and strict persisted readback. The combination control performs its writes after Stop has acknowledged cancellation, proves Select remains queued, and then reopens the account after Select's deferred close to verify persisted content and rejection of the retired app pointer. The ordinary Stop control cancels the admitted operation after writes and requires both actual entry and cancellation to survive.

The type-lock path does not reenter the same object-cache lock. The proven observer only derives original payloads, closes its owned raw ReadTx before ACL work, and constructs private original Tree/strict State replay views. It never calls `GetObject`, `DoCtx`, `InitObject`, normal loading/migration, or native Apply. `session.current` uses `Space.Get`: the loaded controller/loader returns the existing Space through short registry and loader locks. Original `StateMachine` releases its lock before closing or starting a process. This establishes the reviewed lock order; the new native controls remain the execution gate.

The admission is intended only for bounded synchronous work. It is not appropriate for the existing protobuf importer's unjoined background operation, whose cancellation/lifetime needs a separate design.

## Focused original-native controls

Only `TestOtzariaAnnotationSchemaRegistration` and these 13 new children are selected:

1. `ActualRegistrationAndStrictReadback`
2. `RepeatedRegistrationDoesNotMutate`
3. `MissingAttachmentUsesOneNativeApply`
4. `VisibleColumnRemainsConflict`
5. `RootOnlyStopsAllCreation`
6. `DifferentActiveAccountIsRefused`
7. `CancelledBeforeAdmissionWritesNothing`
8. `NativeRootCollisionDoesNotInitialize`
9. `NativePopulatedCollisionDoesNotOverwrite`
10. `NativeReaderRoleCannotRegister`
11. `QueuedAccountStopDrainsWithCancellation`
12. `QueuedAccountSelectDrainsNativeApply`
13. `StopCancelsQueuedSelectWithoutDraining`

The Reader control uses real original signed ACL additions and ownership transfer in a disposable LocalOnly Space. There is no fabricated permission object. The native collision controls use the original production storage and creator. All test accounts/directories are owned disposable fixtures; no user's native account is opened or mutated.

Prior strict 12, original native 13, V6 native 18, V7 native two, and readback nine passes remain associated with their original sources and are not replayed. The new runner enforces the 13 previously composed input hashes unchanged, then adds exactly four product and two test files. All 19 declared inputs must appear in the actual Go compilation closure. It retains the proven finite deadline/process-group cleanup, native dependency hashes, exact selected-case parser, post-execution checks and original streams. `RUNNER_DELTA.patch` is the derivative's source diff.

Completed local preparation: actual Sentinel Windows Go 1.25.6 gofmt accepted all six files; the new Python runner parses. These are source/format checks, not native compilation, tests, Apple SDK build or production acceptance. The planned native run requires actual Go 1.26.5/macOS ARM64/Xcode 27 and must accept frozen source formatting without rewriting it.

## Swift/RPC composition still required

The original mobile bridge uses C/gomobile `Command` → generated `service.CommandAsync`. Its command switch is closed, so a string-only extension cannot call this component. A future additive named request/response must use the original protobuf and command generators; this packet changes no generated protocol or public SDK API.

That request must carry expected account, actual selected destination Space and the exact schema protocol. Native results must preserve unresolved/conflict/error phases and actual attempted IDs. Responses remain data rather than capabilities. On Swift, the original `Invocation` must keep the actual selected-Space binding and account/participant/Space-view permission admission through the native call and completion drain. Swift task cancellation alone does not cancel the native command. Existing document ownership cannot manufacture a new-object or schema grant. The current native retained-app check is an additional boundary and does not replace that selected-Space/currentness composition.

Further root-only recovery, ordinary annotation creation/recovery, body/import-map semantics and ACK remain separate dependent work. This component deliberately does not turn a historical schema observation into authority for those operations.

## Original source references

Exact source blobs and SHA256 hashes are listed in `SOURCE_INDEX.json`. Principal originals:

- [Heart account selection](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/application/account_select.go), [Stop](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/application/account_stop.go), and [beginStart/end](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/application/app_start.go).
- [Original object creation/cache ordering](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/object/objectcache/tree.go) and [native storage insertion](https://github.com/anyproto/any-sync/blob/5d71ccad5db77997df2d2426011ebae4e7600d98/commonspace/object/tree/objecttree/storage.go).
- [Actual Space.DoCtx](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/clientspace/space.go), [Space loading](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/load.go), and [controller state-machine locking](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/internal/spaceprocess/mode/statemachine.go).
- [Original native creator](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/object/objectcreator/creator.go), [type creation](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/object/objectcreator/object_type.go), and [original property/layout behavior](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/detailservice/relations.go).
- [Proven nine-case readback evidence](https://github.com/davidpovarsky/anytype-swift/blob/3be6ecab805b17e2c90fee897fdab45a0b03bfdc/docs/pinkha/torah-integration/native-annotation-schema-readback-20261122/first-native-run-45032882624/README.md).

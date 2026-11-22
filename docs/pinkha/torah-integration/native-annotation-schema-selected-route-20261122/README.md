# Closed original selected-Space schema entry point

This is a separate source-only continuation candidate based on original SDK commit `edce5b975b173059522f90adb71271fb95adf963`. It is not part of the RPC generator-copy fix, the current SDK producer, or a production acceptance result.

The 27-line addition is confined to `OriginalActiveSpaceSelection` in `Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift`. Removing it reproduces original Git blob `66a2d5dd0237e883912b921c9fe7151df91a0d7a` exactly. No original selection, stop, subscription, account or binding body changes.

## Actual original source composition

The original `ActiveSpaceManager` publishes this nonconstructible selection only after its real `WorkspaceOpen`, account/selection validation and original subscriptions. Its private attempt retains the real account, selection and SpaceView generations. Account or selection retirement invalidates that handle.

The new schema-only method accepts only the drained-history callback. It obtains `ParticipantsStorage` and `SpaceViewsStorage` from the original `Container` singleton registrations in `ServicesDI.swift`, whose exact original Git blob is `dfc2b87f5e688b6fb5b89e24d58799f65751ea67`. It reads the current opaque permission records for the selection’s stored Space ID, checks the current SpaceView ID against the actual opened `AccountInfo`, and obtains the attempt’s existing private `workspaceBinding()`.

It then calls the already reviewed `performOriginalAnnotationSchemaRegistration`, supplying the selection’s own stored account and Space IDs. That composition retains the original `requiringSpaceEditPermission` rule, including both actual account-bound permission captures and the original `SpacePermissions` local-mode rule, and admits only `AnnotationSchemaRegister` through the original native invocation/drain path.

No caller account ID, Space ID, permission, Boolean, lifetime, document owner or current-identity closure is accepted. No generic binding is exposed. The private original binding is derived only from the generations that created this selection.

## Historical result and cancellation boundary

The returned response and separately copied drained history are historical observations. They do not create a writer, an object-body proof, a current account lease, uniqueness across clients or ACK authority. A missing copied native response does not establish that no mutation occurred.

This source change does not modify `ActiveSpaceManager.stopSubscription`. Its existing selection retirement must reject new admissions; this candidate does not claim that every stop acknowledgement waits for every already admitted schema call. The reviewed RPC/Invocation route still has to demonstrate actual failure response copyout and late-caller-cancellation drain behavior with real generated types and original native execution.

## Remaining execution and integration gates

1. Produce and review the actual original generated RPC outputs; confirm the generated names used by the existing composition.
2. Compose and compile the real native endpoint and full SDK source, including this exact original-file addition.
3. Exercise the closed route using actual selected account/Space subscriptions: ordinary success, wrong/retired account or selection, view retirement, permission loss, and already-admitted native error or late cancellation. Preserve actual phase history; do not fabricate zero-write outcomes from absent responses.
4. Connect the production destination callsite to the actual original selected handle. No generic public constructor or synthetic source binding is proposed.

`SOURCE_INDEX.json` binds all nine inspected immutable original files, the unchanged existing RPC composition, and this one candidate afterimage. No native control, generator, Swift compiler or app was run for this draft.

# Original account bootstrap readiness

This source checkpoint closes the readiness race between the original selected-Space hook and the embedded account facade. The original \`ActiveSpaceManager.performSelection\` already invokes \`PinkhaBootstrapHook.handleSpaceActivated\`. The facade now awaits the state manager for that same original bootstrap operation, then reads the persisted manifest and all three role type objects before delivering the existing \`onReady\` callback.

## Exact boundary

Only \`OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift\` changes. The actual existing \`PinkhaSpaceManifestStore\`, shared \`PinkhaSpaceManifest\` model, original bootstrap service and original \`ObjectSearch\`/\`ObjectShow\` dispatch are used. There is no second provisioner, Factory replacement, generated manifest, public initializer, credential path or new public API.

The original runtime, account, selected-Space, participant-edit and Space-view captures are frozen before schema registration. The readiness read binding retains those exact captures through the actual original RPC boundary. Failure/cancellation/retirement cannot deliver \`onReady\`: close retires the lifetime first, clears the callback, cancels selection and uses original authentication Stop to drain original bootstrap/runtime work.

The 120-second wait observes the same hook; it does not retry a schema mutation. After the wait, every capture is revalidated. The genuine read-only manifest store discovers an unambiguous persisted manifest. The facade requires schema1, full provisioning, all original property/folder/template identities, exactly three distinct registered role IDs, three actual native objectType-layout/unique-key witnesses in the selected Space, and unchanged persisted manifest JSON across the type reads. Discovery is repeated before accepting readiness. The private immutable observation retains the real ObjectShow responses.

This is an initial readiness observation. It is neither a remote ACK nor a long-lived current revision token. Every later native conditional operation still obtains and checks its own original root, Archive, manifest and type witnesses.

## Compatibility and evidence

The source is based on the reviewed original MiniApps union \`0ae997abd5184b6afb93bf41203f0559fd1e8c6a\`, merged at \`bc36cee366f8a225b034f69d98f974ff28ffa948\`. The public host contract is byte-identical: 260 public requirements plus 22 Debug-only requirements; SHA-256 \`b8a02497aeabab316d85daf2dab5045b1d94dac98a14b7ccc89a3b7c9a6509c0\`. Native Go, generated RPC, ABI inputs, public signatures and all original historical receipts are unchanged by this increment.

Independent source review traced the original store, cancellation/retirement and actual original Stop. It found no blocking lifetime or false-readiness defect. That review is not Apple compilation or live bootstrap acceptance. The focused complete-context Apple typecheck and the normal Maktabah account/lifecycle UI are the execution gates.

The separate real native promotion type fixture was inspected without reading credentials or note bodies. Both genuine type ZIP entries have SmartBlock type528, internal \`Snapshot.Data.Key\`, and full marshaled \`details.uniqueKey\`, as documented in \`OBSERVED_TYPE_METADATA.json\`. The existing Swift lifecycle validator reads the full native detail key and validates exact ID/Space/type; it does not incorrectly compare the internal key against a marshaled key. No validator was weakened.

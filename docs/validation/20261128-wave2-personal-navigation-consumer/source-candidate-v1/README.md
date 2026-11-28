# Personal navigation consumer — frozen source candidate

This is a five-file W2 source candidate against immutable bae68131a20fd7ef351c2b4034ebdf520c6d3b39. It consumes the published d1 Host APIs and the exact W1-declared nonoptional `AnyEmbeddedSession.expectedNetworkID: String`. The complete Runtime/native-export successor is not yet part of this packet. Publication, compilation and runtime adoption remain held until that exact source tuple is available and integrated. The existing W3 App producer and first Apple queue remain separate.

## Behavior

The original workspace owns one navigation store. It captures the expected network from its original boot before awaits, obtains the binding once through the original session, and propagates every acquisition failure through the existing connection failure/drain path. There is no guessed HTTP availability status or legacy fallback. Optional defaults preserve existing injected callers only.

Library Home is an explicit action. Existing document menus can select a Home document and the Home context menu can explicitly unset it. Stored absence, empty, built-in and unsupported values remain distinct. Built-in views have no invented route. Existing recovered navigation is never replaced automatically. All labels use the existing Hebrew/English AnyUIErrorText helper; opposite App/OS language execution is still pending.

A document records an actual open only after a successful current-owner read and real foreground mount. A separate mount identity prevents refreshes and child sheet dismissal from repeating the operation. The same document waits for a cancelled preceding observation to drain before dispatching a newer timestamp. The existing editor write authority and draft/recovery logic are preserved.

Prepared intents are retained before dispatch. A synchronous locked holder retains only a matching native ACK before awaited postflight, including when the original session later rejects delivery. No automatic resend, imported-clock replay or durable crash-reconciliation claim is introduced. Actor attempt bounds remain finite; existing lifetime drains join the caller tasks.

## Evidence

- All five original complete bodies join at bae and match the earlier 1ae originals.
- Fourteen complete nonrecursive Git trees were rehashed; the five d1 production API blobs also match at bae.
- literal-replacements.json contains 26 exact reversible rules; source-proof.json binds full source identities and preserved original IDs.
- Candidate bodies are complete files under candidate/, not product paths in a working tree.
- implementation-matrix.json records the next real validation obligations. No test methods, Package/PBX entries, controllers or gates are changed. No compiler, tests, Native/account or host runtime actions were performed.

The previous 14,466-byte c868 proposal remains unchanged at ../consumer-proposal.json. C's imported catalog and cold restoration remain separate from this current-native consumer.

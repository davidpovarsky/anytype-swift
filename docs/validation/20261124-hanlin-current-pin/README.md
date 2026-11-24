# Current Hanlin dependency pin after actual catalog regression qualification

The current application materializer and all of its live checkout steps now select immutable Hanlin 6bd6036dbca16c969689a5722550a54bebc1e851. The actual engine comparison is retained in the adjacent 20261124-hanlin-host-catalog/actual-mac-comparison proof: the original engine failed the exact continuation method, then the reviewed candidate passed that unchanged method and the cancellation method.

This source change touches only downstream dependency configuration, current admission constants and current usage guidance. It makes no additional App, native, generated protocol or SDK implementation change. The canonical source repository remained clean at 6bd throughout materialization.

The unchanged prepare_sdk.py successfully materialized and verified all 409 files in the three requested packages. The resulting marker is retained as hanlin-snapshot.json (SHA256 59962cde7a8ff214a57d4711bf8cac7bda0b75c2ef3a7df63ed0c1091552135b). Its Engine and both test bytes exactly match the actual Mac comparison. The original ProviderResponseFixtures.swift remains byte-identical at both 116cc and 6bd, with the same qualified sourceSHA.

Fifteen workflow files contain 18 live checkout occurrences. They all follow the global source.json pin; the current example and contracts.HANLIN agree. The current fixture verifier advances its revision only, retaining its exact fixture source hash. No provider schema, assertion, selector or wait was relaxed.

Historical SDK manifests, product origins, original fixture receipts and retained product snapshots remain unchanged. Qualified/tagged SDK compilation reuse still binds the original d254 cache. The unchanged equality gate refuses the new source.json; no new cache adapter or historical-source inversion is claimed. Those historical SDK routes are not the current acceptance route and are not dispatched by this work. Existing successful SDK06 evidence retains its original scope and source.

A subsequent binding commit will bind only current helper inputs/trees and current product revision metadata to this frozen source. Actual new App/NativeUI and Release acceptance remain NOT_RUN. The already-running Page 45498082340 remains on immutable 96fadb and its original 116cc dependency. Original D diagnostics continue using fb5 Products and source.

# Anytype canonical Hanlin SDK dependency integration

## Implemented scope

The isolated branch starts at the published shared owner source fd6f3357cd03da840c00b54a6248dd1a3553ba07. HanlinSDK.lock.json selects the original eight public products from canonical producer2548eac1155239e76cb1a2c6d978e00131340e1f.

The existing host Swift, Anytype app UI, editor, Heart, protobuf, runtime observers, selector probes and quiescence controllers are unchanged. The three Xcode package references and two Pinkha package manifests now consume one shared root profile at Dependencies/Hanlin. The host's original parser and SwiftSyntax pins are retained; the original renderer's missing dependencies are added from the canonical lock, without unrequested version upgrades.

Tools/Hanlin/prepare_sdk.py preserves --source, --check and verify(directory), and delegates installation to the shared sparse SDK installer. It preserves the existing .pinkha-source.json receipt path/revision/files contract used by current controllers. This one generated marker is explicitly excluded from the SDK Git status, while all original source bytes, complete selected directories and the two generated SDK manifests remain independently verified. Existing archived dependencies are preserved instead of being overwritten.

## Actual source/configuration verification

- One actual sparse installation at the immutable producer pin, with no managed native targets or unrelated runtime roots.
- Four real-file rejection controls PASS: forged marker, original source plus forged marker hash, ignored extra compiler input, and modified generated manifest with matching forged hashes. All owned files were restored exactly.
- Two actual Swift package manifest dumps PASS for the host modules. These are graph/syntax checks, not dependency resolution or Apple compilation.
- Nine workflow files / ten checkout steps change only the authoritative pin read and checkout ref. All other parsed workflow job/step/input semantics compare equal. Four pin-reader cases cover the current lock, explicit legacy source, malformed current lock rejection and the relocated Page154 app checkout.
- The original provider fixture Git object is unchanged at the new pin. The selected SDK need not materialize unrelated test trees. No unchanged provider fixture or native test was repeated.
- A small real SwiftPM resolver experiment establishes explicit host revision precedence over a renderer's transitive version requirement. It does not establish compatibility of the actual renderer against Anytype's retained parser revision; that remains part of Apple integration.

An initial ad-hoc configuration reporter asserted the wrong SwiftPM JSON field name; the actual successful manifest output provided nameForTargetDependencyResolutionOnly. The reporter was corrected without a product change. The same four pin-reader cases are not counted as eight distinct tests. The strict source-retention planner also stopped on module files added after its older baseline; their exact immediate-parent deltas are recorded separately and bound as sharedSources of the valid source.json baseline mapping. The verifier itself is unchanged.

## Ownership and publication

The current SDK06 continuation is https://app.asana.com/0/0/1220769818981326. Existing owners retain selector/enumeration, owned process quiescence, live runtime mapping and original Products qualification. This branch does not merge or edit their active worktrees.

Code and workflow commits use [skip ci]. The workflow file updates require the connected GitHub app's authorized contents write route; the intermediate code-only ref is not a native dispatch target. After those identical workflow commits are merged back, the root agent will coordinate one coherent handoff to the existing Anytype owner.

## Acceptance boundary

The retained native1/UI1 results from45096079315 remain passes at their original source, while that run's missing live-runtime mapping remains failed. SDK23methods/32cases and acknowledgement7 remain open in the existing owner lane. Old45087685319 Products retain their original source/tree/dependency identity and cannot be relabeled as builds of the new SDK pin.

No Anytype native build, simulator, provider transcript, mounted UI, physical-device or release acceptance is claimed for this upgrade. No CI was dispatched by this lane.

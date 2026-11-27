# RTL hosted profile: exact current editor compatibility

This source-only successor changes exactly one literal in the historical RTL
hosted profile: the whole `AnyNativeEditor.swift` source hash, from `e25deb24…`
to `8b461efe…`. It does not change any RTL test, assertion, six-method/ten-case
inventory, selector, enumeration/result validation or compiler-proof check.
All eight original helper declarations are unchanged.

Five original source files were read directly from the published final commit
`3559f6010d1ae837d12e4eda9fd7cbcb40870a3d` and verified against both SHA256 and
their Git blob identities. The other four source hashes already match the old
profile and remain unchanged. This records actual source identity only; it is
not evidence that the final commit has compiled or passed UIKit tests.

The complete current editor is independently restored to the old RTL editor
through exact inverses for the four published changes, in reverse order:

1. Styled observation arguments (`7380a797…`, `8b461efe…` to `c0c04557…`).
2. Native Hanlin entry (`dfbb4811…`, `c0c04557…` to `4b7a6fea…`).
3. Original DesignKit typography and Dynamic Type (`33e31c64…`, `4b7a6fea…` to `26a3876c…`).
4. The shared Add block menu (`dc582ba3…`, `26a3876c…` to `e25deb24…`).

Each step requires the entire input and restored output hash, not a matching
function excerpt. The typography inverse includes its two retained review
corrections. The profile itself restores exactly to its original SHA256
`80ebc56005110ee78615322f56b876b5b6fd4fae23975b86d249ae05ebcac8ea`
by the single inverse literal. The new profile is
`f16a16071fadf66ca0b1cd8a0583e41aadf7439e567a7c51daf72d56ad83885c`.

## Execution boundary

This helper has no runner or authority to open a product. Its original usage
contract still requires successful shared producer/product admission first.
The preparation metadata leaves future source freeze, producer receipt and
shared admission null, with `readyForExecution: false`. No old runtime gate is
modified. A future exact consumer closure must explicitly bind this helper's
new complete hash together with its matching source and actual compiler proof.

The source compiler witness remains tied to real `swiftc` log invocations and
their exact `AnytypeTests` FileLists. It checks the actual directly compiled
original sources and named literal arguments; no FileList-only acceptance or
component-to-UI credit is introduced.

The original portable controls were reused without replay. This change was
checked by current primary source reads, complete source inverses and AST
identity of the original helpers and inventories. No Apple/compiler/native
invocation, test execution, simulator or physical-device action occurred.
RTL component execution and the requested mounted language/device matrix
remain open until the matching shared product is available.

`prepare_rtl_current_editor.py` reproduces the exact source qualification from
the pinned original profile, retained five-file readback and three retained
published inverse records. It writes only into a new directory and refuses an
existing output. The complete source chain and resulting receipt are retained
alongside this note. Wave3 owns final integration, builds and execution.

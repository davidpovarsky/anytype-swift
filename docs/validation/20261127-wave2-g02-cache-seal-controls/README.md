# G02 cache-seal correction: exact source pins in the closed consumer

This is a separate control successor over `831a7dfb90164c55fa87c32273f2f61062d52c92`. The native test correction is `67e0f612fbb166cf9a80c21ae9c97f6641daef45`, directly over the preserved `63fb8c03749f7bad44cc183c6d35503e1217a48c`. The UI remains the exact `28bb60e4d4403251b1fde909ccfa1c84aa3966ba` source. The source-level hold concerned the old reader's stable-cache-seal assumption; no historical Native test failure is invented or discarded.

Only four existing runtime-control files change:

| File | Change |
| --- | --- |
| `g02_word_consumer.py` | Exact native source hash becomes `b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed`; the existing closed-gate error names that successor. |
| `g02_native_phase.py` | Exact appended native suffix hash becomes `1363c0f8679dab6b4d1feeeaabac63abce7a9fe733f7e15d3b4b2f3ed857afd9`. |
| `g02-closed-profile.json` | Exact native commit/full-source and native-adapter byte pins change together. |
| `materialize_g02_control.py` | Exact native-adapter hash changes to `bccc446085987c881d6ed21aa6317a570947492c652682500d8ac9b61cff1f11`. |

The UI collector remains byte-identical at `a357c7b35c5a273d4e92c7ee9d7316c22074693d04b5145ef522072a2cfd7091`. Every original function body remains byte-identical except the closed-gate diagnostic hash text. `pin-inverse.json` records exact full-file inverses; no lifecycle, receipt, invocation, failure-retention, source-witness or assertion logic changes.

`require_runtime_ready` still raises unconditionally before product cloning or simulator creation. The current `8f2c1171…` products cannot qualify either G02 revision. No common producer/admission/source pin is replaced, no readiness switch is introduced, and the original 13-file common closure remains unchanged. The future G02 derivative still adds four files for the same 17-file shape.

## Bounded validation

One targeted portable control method executed against the actual corrected Swift bytes. It accepted only their source declaration, rejected the old `bd988815…` reader, rejected the original prefix without the addition, and rejected a one-byte changed successor. It also confirmed unconditional runtime rejection with an empty admission and with a supplied `runtimeReady=true`. This control does not execute Swift or verify native semantics.

The corrected materializer ran once against the unchanged exact original F donor `2e57294dc7a00d4302a9dd5f316b2419e75d6a08a4f55b47451d6c822335ec44`. The resulting F host remains exactly `cf1d79a8db7ea912cc796453333e20a51f5476d9ab65b90a2b6959fdd139d74b`, matching the earlier derivative. The new materialization **receipt** is `01f78099830f62a79092975d3a3c919bbaaa0148e6be4426ce853a7fad77d95b`; that hash is distinct from the unchanged host hash. All original inverse/finally/budget validations passed while `runtimeReady=false`.

The earlier ten portable methods and their failure-retention receipts were not rerun. The retained new control source was executed in the staged local layout recorded by its exact command receipt. To reproduce it, place the four corrected runtime modules beside it, place the corrected native full file one directory above, and place the original `63fb` native full file in that parent's `originals` directory; validate all recorded hashes before invocation. This is a source-control evidence fixture, not an App or Native simulator fixture.

Actual Apple compilation, both native readback phases, the two UI stages, visual inspection and physical-device acceptance remain pending the qualified shared future build. The Native engine, protobuf contract, original preparation, three document types, shared fixture and all historical evidence remain unchanged.

The first scoped publication RPC errors and absent-branch observations remain in `retained-source-publication-attempts.json`. Root subsequently published and read back the unchanged native commit; `root-source-publication.json` is the exact successful receipt, SHA-256 `789d58a27e41e96c5e25e542bda146e2701a5f76685ddcee30b0e67eee2b8c3f`. These publication events are separate from Native or XCTest outcomes.

Root independently reviewed the exact four-file successor and all seven literal substitutions, reversed them to the original files, and verified the unchanged collector, generated F host and closed runtime boundary. The exact source-only review is `root-pin-review.json`, SHA-256 `9a9c9156c4911e3bf84eb796cf6d4387ae0e5f5d7bbe2be1e4fff2b90beed702`. No additional controls or runtime tests were performed for that review.

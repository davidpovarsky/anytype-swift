# Existing mixed-language lane: two required observations

**Status: OPEN / NOT_RUN.** This note adds observation requirements to the existing coordinated acceptance lane. It adds no selector, test suite, controller, timeout, fixture, product admission or execution request.

Use only the matching shared App and the existing owned fixture/startup controls. Retain the original source/product/device/fixture identities and the selected lane's actual results. The source-only audit at `e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff` is not a substitute for these observations.

| Existing language direction | Observation 1: actual runtime locale and resources | Observation 2: actual title/error and visual presentation |
|---|---|---|
| **Hebrew App / English OS** | Retain the actual device/OS-language receipt and the App's observed current locale/language identity. Confirm that the matching built App contains the required Hebrew resources and that the bundle used by the original `Loc` lookup selects the intended language. Bind any retained runtime/resource readback to this App/run/device. | In the same owned document, retain the Properties association row and the related-document sheet title for the same prepared association. Compare their labels with the real prepared Hebrew/English values and the existing formatter's fallback rules. Retain an existing deliberately triggered, known `AnyUIErrorText` message and its Hebrew wording. Review the corresponding original AX/screenshot for intended RTL presentation and clipping. |
| **English App / Hebrew OS** | Retain the corresponding actual device/OS-language receipt and observed English App locale/language identity. Confirm the matching built App's English resource availability and the actual `Loc` bundle language selection, with the same source/run/device bindings. | Retain the same kind of row/title identity and the existing known error in English, comparing actual prepared values and fallbacks. Review the original AX/screenshot for intended LTR interface presentation and clipping. Content-specific paragraph direction remains governed by the existing editor tests. |

## Evidence limits

- Configured launch arguments, controller fields, source `.lproj` directories and expected language strings are setup evidence. They are not an observation of the running App's locale or selected resources.
- Reuse the existing capture/readback facilities. If the current lane does not expose an actual runtime-locale or resource-selection observation, mark that specific item **MISSING** and report it to the lane owner. Do not manufacture a value from the configured expectation or add a controller in this handoff.
- A canonical reference or a legitimate alternate-label fallback alone cannot prove which language was selected. Use the original fixture's actual labels. Missing bilingual fixture values remain an explicit observation limit; they do not justify changing canonical data or silently replacing the fixture.
- Use only an already approved error stimulus in the existing journey. If no appropriate known-error fixture/readback is available, retain that item as **OPEN**. Do not invent permission state or perform an extra mutation to obtain a message.
- The exact source/document/Space association and the original test result remain authoritative. A language observation cannot turn an unrelated or failed journey into a pass.
- Preserve all previous evidence and failures. No replay of the historical T5 36+9 calls is requested.

The two language directions remain open until the actual shared-product receipts and visual observations establish them. Properties component execution, when separately performed, can establish only its selected model/test behavior; it does not satisfy this UI handoff.

# Page154 — original visual evidence review

**Scope:** five original screenshots from App source `379ca3568f247d2fc218ed63df24796d461713c0`, Native manifest `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`. This is an inspection of retained evidence, not a new UI run or acceptance result.

## Provenance

The exact retained archive has SHA256 `467da5b58ea673206f76a3519566d08545a1fc264d6fc79fc170a8105c4fa373` (13,775,784 bytes). Each selected PNG is linked by its original xcresult attachment manifest to the exact test identifier and device in the corresponding `mounted/result.json` or `linked-ui/result.json`. Both original results report one passed test, zero failed or skipped tests. Their original status is unchanged.

The selected images total 1,566,245 bytes. They were exported without modification, transferred into private scratch, checked byte-for-byte by SHA256, and actually viewed with `view_image`. No crop, re-encoding, screenshot recreation, simulator action, native call or test invocation was performed.

The original result identifies an iPad Pro 13-inch (M5), arm64 iOS Simulator, iOS 27.0 build 24A434. All five PNGs are 2064 × 2752. The visible layout is portrait, light appearance, with English interface/text; the linked-ui captures show an English QWERTY keyboard. The OS language is not inferred from the image.

## Image findings

| ID | Original stage / capture | Visible evidence | Main limit |
| --- | --- | --- | --- |
| V01 | mounted — selection/cancel confirmation | Anchor is selected with handles; the complete Create/Cancel dialog and both buttons are readable. | The still image precedes the action and does not prove cancellation or unchanged storage. |
| V02 | mounted — labeled cold reopen | Anchor is underlined; the next Unselected line is present and legible. | Underline and capture name do not prove native anchor identity or a process restart. |
| V03 | linked-ui — canonical visible link | Sources for anchored text shows the Genesis 1:1 chip, query, tabs and source rows. | The modal covers background content and the lower list edge only partly shows a further row. |
| V04 | linked-ui — replacement selection | The full Anchor word is blue-selected with handles; Cut/Copy/Paste/MiniApps menu is visible. | The menu covers part of the next line; later keystrokes and exact native range are not shown. |
| V05 | linked-ui — labeled cold reopen | Changed is visibly underlined behind the sheet; the Genesis 1:1 source chip remains visible. | Rendered continuity does not replace the missing independent native readback. |

## Clipping, direction and layout boundaries

The main selection dialog, its action labels, the source chip, the sheet title and the inspected search/tab controls are legible in the selected captures. There is no observed cut-off in those named controls. This does **not** establish that the whole UI is free of clipping.

V01 and V02 contain phase banners (`CANCEL_CONFIRMATION_VISIBLE` and `PASS_COLD_REOPEN_MOUNTED`) that partly cover the top Pinkha/Heart header. The images establish the overlap only; they do not establish whether it is a production UI defect. V03 and V05 intentionally show a modal over part of the document, and V04 has a context menu over part of the next line. A fragment of another source-result row/icon is visible at the bottom of V03. Hidden content and scroll behavior cannot be judged from that frame.

There is no Hebrew or RTL text in these five images. They provide no visual credit for Hebrew/RTL, language inversion, iPhone, dark appearance, landscape, VoiceOver or a physical device.

## Remaining acceptance and retained failures

The three historical preparation/mounted/linked-ui PASS outcomes, the PNG-collector FAIL, and the later linked-native-enumerate OWNED_TIMEOUT remain unchanged. This review does not diagnose the timeout or execute any missing stage. The original fixture is expired under its unchanged 7,200-second contract; the new-source continuation still needs the original six-stage renewal with the old evidence linked. Its present expiry is not the cause of the earlier timeout.

The native identity of the anchor and association, precise persisted text ranges, full unchanged surrounding content, ACL/Space isolation, independent linked-native readback, unlink and final native readback cannot be certified from these pixels.

## Exact image mapping

### V01 — mounted

- Original member: `execution/evidence/mounted/private-attachments/27A8C7AA-C7B7-487E-90CF-B8A4E475C383.png`
- Original attachment name: `semantic-anchor-actual-selection-and-cancel-confirmation_0_65CC6A5F-49E5-4839-964E-2B2940A497E9.png`
- PNG SHA256: `323c596436662b2056332f81b33616a4169077bb0b57ef7c76274d7a91667566`
- Result SHA256: `e5e288762a4519fd70b6413d307dea4e794b55666153f66da8f7b54c8e1433fd`
- Attachment-manifest SHA256: `5e1728d927d74632ea854649deeeb8692d9d57a3d25d0f603a8b3390131fd871`

### V02 — mounted

- Original member: `execution/evidence/mounted/private-attachments/9B80AE70-B446-40DB-8936-FC0D688ACF1C.png`
- Original attachment name: `semantic-anchor-persisted-in-cold-editor_0_A00BE126-A928-44EB-9CA1-260E124D0BD9.png`
- PNG SHA256: `9efe3b4065f46c6e8916c9db82322884a3abdcd646222ded8f54edfcd7318fed`
- Result SHA256: `e5e288762a4519fd70b6413d307dea4e794b55666153f66da8f7b54c8e1433fd`
- Attachment-manifest SHA256: `5e1728d927d74632ea854649deeeb8692d9d57a3d25d0f603a8b3390131fd871`

### V03 — linked-ui

- Original member: `execution/evidence/linked-ui/private-attachments/37E128E6-FE41-4E6A-AACB-7A4FB91C5DCD.png`
- Original attachment name: `heart-semantic-source-canonical-visible-link_0_5AE99102-78D2-4A00-B78F-5D241CD09C0C.png`
- PNG SHA256: `73f9895d2ba03ae95e36c380a7725137e960c2f565d90b0ee07e25db915d2327`
- Result SHA256: `062cc88c2cb2a6bf558ee134fe5df8691f596144af4af0d3263ae61c11d9836b`
- Attachment-manifest SHA256: `cdad51421bf0998fba284a6fd3c527b7c07ab81fd1b50edbc0689f4edf22afed`

### V04 — linked-ui

- Original member: `execution/evidence/linked-ui/private-attachments/41766CCB-679D-479B-A7AC-BE002CA74981.png`
- Original attachment name: `heart-semantic-source-replacement-selection-visual_0_A16396C1-F472-48D8-A570-A48D57FFDA22.png`
- PNG SHA256: `1906a12ba4720982369a7bf458a496becbed26c0fdeb879d1891dd3f004f53f1`
- Result SHA256: `062cc88c2cb2a6bf558ee134fe5df8691f596144af4af0d3263ae61c11d9836b`
- Attachment-manifest SHA256: `cdad51421bf0998fba284a6fd3c527b7c07ab81fd1b50edbc0689f4edf22afed`

### V05 — linked-ui

- Original member: `execution/evidence/linked-ui/private-attachments/58326DBB-0D40-4EB0-8518-141F0D556E51.png`
- Original attachment name: `heart-semantic-source-cold-reopen_0_A852131E-B4C2-4F88-A7DC-FD4E1E3F3C41.png`
- PNG SHA256: `93bbcab679fb36c36ab1cc937e5fac0411d67297909f5976f3353f80240f179d`
- Result SHA256: `062cc88c2cb2a6bf558ee134fe5df8691f596144af4af0d3263ae61c11d9836b`
- Attachment-manifest SHA256: `cdad51421bf0998fba284a6fd3c527b7c07ab81fd1b50edbc0689f4edf22afed`

## Retained receipts

- Exact Oracle export receipt: `export-receipt.json`, SHA256 `15c43520d8b0500bed4635a3a5bae1a0d8ce3339a8fddf0bdf5ea8d86d070525`.
- Exact private scratch intake: `scratch-intake.json`, SHA256 `2cfa44850c2fc692d04a6005991aca6e1945b511e1c895525289b68a4377d532`.
- Detailed review: `visual-review.json`, SHA256 `793e585ab2dced86f90fbe71e0465dc4e772dbcced036f4d9716f4b944386f6e`.

The original PNGs remain private fixture evidence. Their bytes are not included in a public source-control or Asana attachment.

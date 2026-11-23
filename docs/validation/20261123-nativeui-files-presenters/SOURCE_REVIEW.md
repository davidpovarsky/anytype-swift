# Files presenter separation and real destination feedback

Original run 45087682296 at 7293e4fd0bcabdcdb643d5768b777b8e87ff1b73 failed before its first Save: the live system picker showed the folder title Pinkha, an empty-folder message, and an enabled Save action. No Exports control existed in its actual AX tree. Both its original AX and screenshot were exported without rerunning the product; their exact hashes and selected non-content observations are retained here.

This is not a text-role selector mismatch. The previous source-bound 450382 diagnosis already observed a successful export in Pinkha followed by an empty importer in Exports. Adding a default-directory modifier to each dialog in the shared chain did not resolve the exporter behavior in 7293. The new candidate gives the exporter and importer distinct initiating-button subtrees and first constructs both with a concrete directory returned by the unchanged directory validation. The inference being addressed is configuration/presentation scope; the precise internal SwiftUI cause is not claimed as proven.

The real exporter success callback now displays the returned destination folder's human name. It uses the returned URL, not the requested directory, and does not display a full container path or provider UUID. The Files-only nested helper adds a check that this actual callback folder is Exports. All original current-directory, real Save, filename, import selection, explicit mapping, exact native body, cold reopen, and three-export checks are unchanged. No waits were lengthened and no retry was added.

The read-only postflight remains unchanged: it must read the exact three UUID-named files from the owned app container's Documents/Exports and validate their JSON bytes, digests, provenance and mapping. No alternative folder or synthetic URL is accepted. The current failed attempt stopped before Save and therefore provides no actual returned URL; the repaired Apple run remains required to establish the callback destination and complete roundtrip.

## Declaration and route boundary

Only AnyNativeArchiveTransferView's state/body and its two new private button helpers change in production. AnyNativeArchivePresentation, the canonical FileDocument, the directory validation and remainder are byte-identical. The sole presentation entry remains the unchanged any-native-canonical-transfer action, which sets the initially-false showsArchiveTransfer flag and presents its existing sheet.

Both newly passed 7293 methods remain byte-identical, as do every class helper reachable from each. Their source contains no canonical-transfer route or archive action. The whole test file outside the separately reviewed SourceDrag member and Files member is byte-identical to 7293. The Files member itself gains only the actual returned-folder assertion. The source-declaration review records exact hashes, reachable members and unchanged route guards for the parent's retention qualification.

Swift syntax parsing passed for the two edited files. Zero XCTest methods were executed here. Real UIKit compilation, the new folder callback observation and the complete failed Files roundtrip remain pending the parent's bounded Apple continuation.

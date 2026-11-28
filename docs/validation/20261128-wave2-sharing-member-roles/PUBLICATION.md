# Per-member role choices: publication and acceptance

This commit corrects the Native sharing role menus through the existing shared capability model. It is a source publication; the five new XCTest methods and actual UI/Native permission acceptance remain NOT_RUN.

## Resulting behavior

A member's change-role choices now come from the same per-member capability accessor used by mutation validation. Approval keeps its separate ordinary grant list. Native refreshes its real snapshot before validating and dispatching the original lease-authorized request.

| Actor | Current active target | Offered changes, excluding its current role |
| --- | --- | --- |
| Owner | Reader | Guest, Writer, Admin |
| Owner | Writer | Reader, Admin |
| Owner | Admin | Reader, Writer |
| Admin | Reader | Guest, Writer |
| Admin | Writer | Reader |
| Owner or Admin | Guest | No role changes; retain separately authorized removal |

Original Owner, self, nonactive and Admin-target restrictions remain. The optional map defaults to nil for existing Heart and other callers. A supplied map denies absent targets and validates keys/roles instead of falling back to a broader global grant list. All 28 current accessibility identifiers, including the earlier 23 additions, are retained.

The change does not introduce Native routes or invitation identities. Decline remains identity-only. W1 owns the separate consumed-request error correction. Guest approval and ownership transfer are not inferred from role parsing; fresh pending recipients and actual invitation/permission/error journeys remain necessary.

## Source and evidence

Base: `6ade3661c261e66c987b7017a6181bdfcebc1d58`, the already published sharing-identifier correction. There are three changed product files and two appended existing test inputs. No Package, PBX, controller, backend/wire or Heart service file changes.

The complete original twelve-file candidate packet is preserved at `/mnt/development/projects/evidence/pinkha-wave2-sharing-member-roles-20261128`. Its seven metadata/evidence files are copied here unchanged. Its five `candidate/<repository-path>` bodies are installed at their real repository paths, with the exact manifest identities; they are not duplicated beneath this docs directory. The retained `README.md`, proposal and manifest describe their original pre-publication phase and paths. `root-source-review.json` records this mapping and independent reconstruction; `torah-independent-source-review.json` preserves the separate peer verdict.

All nine literal replacements reverse to the complete five originals. The original test prefixes of 5,693 and 16,585 bytes remain exact. `superseded-role-gap-assessment.json` preserves the earlier conservative proposal; its removal of the valid Reader-to-Guest option is not implemented.

## Required verification

The three new Shared XCTest methods use the real complete eight-file PinkhaSharing package with zero external dependencies. The 4 original authority and 5 presentation methods remain unselected. Linux cannot qualify the SwiftUI views. The two new NativeApplicationTests methods need the complete original Native target and its actual Apple dependencies; they must not be run against a stub or extracted projector.

Every new method is NOT_RUN at publication. Internal matrix rows are not additional XCTest leaves. Future compiler/source/product admission and resource ownership must match these exact bytes. Preserve the original first Apple 22-focus-method/34-case sequence, real preparation and four Stage1 UI methods, followed by their existing scoped acceptance routes. No historical sharing/T5/drag/component proof is replayed or broadened by this source fix.

`native-two-apple-readiness.json` binds the two exact Native selectors and concrete unchanged Apple dependencies. W3 should identify the existing matching package/test bundle and artifact provenance; an already coherent verified Native artifact may be reused. The report does not authorize a new Linux substitute or require an extra backend compilation.

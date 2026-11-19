# Properties native postflight: use installed test artifacts

The original run 44584920580 at 5fa5fb572f90a9e7b6c97b99591d164ce280f0b8 built successfully and passed native preparation plus both selected UI methods. The first stopped controlled installation preserved all observed native data bytes. Native postflight then failed its original path/device/inode check after XCTest installed the host again. The semantic canonical/Tag/link comparisons were not reached. This is not a demonstrated data-loss result or accepted Properties preservation.

This correction changes only the native Properties postflight selection to the documented `UseDestinationArtifacts` mode. It identifies the already-installed host and native test bundle, excludes the three local installation paths, and preserves the original injection environment. Both standalone and batch execution use the same existing configuration boundary. The native Swift checks, preparation and SDK routes, and timeouts are unchanged.

Before use, the controller captures the selected Xcode executable/version and both raw manuals, verifies the documented no-install capability, and binds the installed native test executable to the original code-carrier inventory. Unsupported selected-runner schemas or capabilities stop the gate. All prior native container and semantic assertions remain mandatory.

Independent review checked the exact c787 Git base. Three stale unchanged local validation dependencies were found and refreshed before publication; the five candidate source/test files were unchanged. The resulting 98 portable controls passed without skips. The original 97-control freeze and its drift evidence remain in the working checkpoint.

Actual Apple execution is still required. These source and portable results do not accept the native postflight, the complete Properties feature, or the release matrix. See `ROOT_INDEPENDENT_REVIEW.json`, `SOURCE_AND_CONTROLLER_VALIDATION.json`, and the original qualified failure report.

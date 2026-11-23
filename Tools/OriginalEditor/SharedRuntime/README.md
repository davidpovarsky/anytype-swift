# Original editor shared Firebase runtime

This is a dependency packaging repair in progress, bound to reproduced Maktabah
Stage B run 45174533607 and the admitted original editor producer de63125b97cd5b91a1fa4f4b71d03738076e735f.

The current producer includes Firebase 11.8.1 implementations inside
AnytypeOriginalEditor.framework, while Maktabah links Firebase 12.8.0 through
CocoaPods. The original compiler log reports duplicate module maps; retained
native symbol output also proves that FIRApp, FIRInstallations, and FBLPromise
are actually defined by the original editor image. Suppressing module maps
alone cannot establish one runtime owner.

This package keeps the original FirebaseMessaging product and its complete
upstream target graph, aligns Firebase/Google/Promises upward to the exact
host sources, and links that graph into one real dynamic product. All Google
Utilities products and Promises Swift are included because the host uses them.
No upstream sources or public module names are changed.

The nanopb versions differ only in their packaging labels: CocoaPods 3.30910.0
and SwiftPM 2.30910.0 resolve to the same commit. The adjacent source receipt
records each C/header/privacy blob and the matching compiler defines.

The branch-only native workflow builds this provider and an independently
compiled importer with Xcode 27, checks its real definitions and dynamic load
commands, and requires an actual iOS 27 process to observe exactly one owning
image for each required Firebase/Promises/transport class. The observed
resolver graph, checkout SHAs, compiler/linker logs, Mach-O symbols, and runtime
nonce/PID are retained. Any unresolved drift, duplicate definition, missing
framework, failed signature, or runtime failure leaves this prerequisite open.

This prerequisite does not qualify the original editor or Stage B. Subsequent
work must compose the accepted dependency boundary with the full original
framework and host CocoaPods/SwiftPM closure, prove each shared implementation
has one owner, and then run the original edit/save/exit/new-PID/reopen acceptance
in English and Hebrew. All original implementation/resource trees and existing
framework acceptance remain unchanged by this isolated probe.

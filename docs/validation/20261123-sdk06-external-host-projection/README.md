# SDK06 external host projection repair

The actual component build returned 70 before any test method ran. The original staged App's executable shim and debug dylib were both present. The retained original successful link command uses the shim as bundle loader and the debug dylib as an explicit symbol input.

This source candidate changes only build-time host linkage and freezes the three empty workspace directories actually added by Xcode. The runtime hosted descriptor, projected Swift bytes, source path validation, and exact result gates remain unchanged. One new pure control is pending; no compiler, simulator, previous control or product method has been rerun.

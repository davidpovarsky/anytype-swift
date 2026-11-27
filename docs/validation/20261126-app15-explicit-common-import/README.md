# Explicit App15 Python dependency

The first root F invocation failed before commands or tests because the shared runtime input qualifier referenced importlib.util without explicitly importing that submodule. Previous freezer imports had masked the dependency. The original F failure and original f31cf1 intake remain unchanged.

This successor adds only import importlib.util. Removing that exact line restores the entire original common file byte-for-byte; every function and class AST is unchanged. The successor canonical admission changes only controllerSHA256 and keeps the actual frozen source/products and original producer proofs unchanged.

Two fresh /opt/homebrew/bin/python3.12 -S -B processes were executed. The first independently reproduced the original missing-submodule failure. The second imported the successor with importlib.util initially absent and passed the actual App15 source/native-slice/runtime-proof qualifier. No engine, XCTest, simulator, build, or source/product mutation occurred.

The original successful immutable freeze remains fad25bdc. The new canonical common is 1dcd02a4 and admission is 87c47c35 under the private Mac control-import-dependency1 directory.

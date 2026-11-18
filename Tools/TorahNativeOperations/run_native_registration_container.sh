#!/bin/sh
# Disposable native registry proof only. No application account or user Space.
set -eu
umask 022
mkdir -p /workspace/evidence/toolchain
apk add --no-cache python3 git build-base > /workspace/evidence/toolchain/apk-install.log 2>&1
apk info -v musl gcc libgcc binutils > /workspace/evidence/toolchain/packages.txt
gcc -v > /workspace/evidence/toolchain/compiler.log 2>&1
gcc -dumpmachine > /workspace/evidence/toolchain/compiler-target.txt
case "$(gcc -dumpmachine)" in
  *-linux-musl*) ;;
  *) echo "Compiler and unwind runtime must target musl" >&2; exit 1 ;;
esac
go version | tee /workspace/evidence/toolchain/go-version.txt
test "$(go version)" = "go version go1.26.5 linux/amd64"
for tree in control heart; do git config --global --add safe.directory "/workspace/$tree"; done
cat > /tmp/t2-qsort-probe.c <<'C'
#define _GNU_SOURCE
#include <stdlib.h>
static int compare(const void *a, const void *b, void *context) {
    (void)context;
    return (*(const int *)a > *(const int *)b) - (*(const int *)a < *(const int *)b);
}
int main(void) {
    int values[] = {2, 1};
    qsort_r(values, 2, sizeof(values[0]), compare, NULL);
    return values[0] != 1 || values[1] != 2;
}
C
gcc -static -Werror /tmp/t2-qsort-probe.c -o /tmp/t2-qsort-probe > /workspace/evidence/toolchain/qsort-link.log 2>&1
/tmp/t2-qsort-probe
python3 -B /workspace/control/Tools/TorahNativeOperations/run_native_registration.py \
  --heart-source /workspace/heart --work /workspace/work/registration \
  --evidence /workspace/evidence --expected-app-sha "$EXPECTED_APP_SHA"

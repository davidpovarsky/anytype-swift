#!/bin/sh
# Only disposable native unit fixtures are opened by this gate.
set -eu
umask 022
mkdir -p /workspace/evidence/toolchain
apk add --no-cache python3 git build-base > /workspace/evidence/toolchain/apk-install.log 2>&1
apk info -v musl gcc libgcc binutils > /workspace/evidence/toolchain/packages.txt
gcc -v > /workspace/evidence/toolchain/compiler.log 2>&1
gcc -dumpmachine > /workspace/evidence/toolchain/compiler-target.txt
case "$(gcc -dumpmachine)" in
  *-linux-musl*) ;;
  *) echo "The compiler must target musl" >&2; exit 1 ;;
esac
go version > /workspace/evidence/toolchain/go-version.txt
test "$(go version)" = "go version go1.26.5 linux/amd64"
# These settings belong only to this disposable process and its children.
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0=/workspace/control
export GIT_CONFIG_KEY_1=safe.directory
export GIT_CONFIG_VALUE_1=/workspace/heart
cat > /tmp/t5-attachment-qsort-probe.c <<'C'
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
gcc -static -Werror /tmp/t5-attachment-qsort-probe.c -o /tmp/t5-attachment-qsort-probe > /workspace/evidence/toolchain/qsort-link.log 2>&1
/tmp/t5-attachment-qsort-probe
python3 -B control/Tools/PinkhaNativeDerived/run_t5_native_attachment.py \
  --control control --heart heart --work work --evidence evidence

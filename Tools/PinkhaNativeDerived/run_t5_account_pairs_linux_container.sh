#!/bin/sh
# Creates one fresh synthetic account; never opens a personal account or Space.
set -eu
umask 022
mkdir -p /workspace/proof/toolchain
apk add --no-cache python3 git build-base > /workspace/proof/toolchain/apk-install.log 2>&1
apk info -v musl gcc libgcc binutils > /workspace/proof/toolchain/packages.txt
gcc -v > /workspace/proof/toolchain/compiler.log 2>&1
gcc -dumpmachine > /workspace/proof/toolchain/compiler-target.txt
case "$(gcc -dumpmachine)" in
  *-linux-musl*) ;;
  *) echo "The compiler must target musl, including its unwind runtime" >&2; exit 1 ;;
esac
go version | tee /workspace/proof/toolchain/go-version.txt
test "$(go version)" = "go version go1.26.5 linux/amd64"
for tree in control source heart-old heart-new; do
  git config --global --add safe.directory "/workspace/$tree"
done
cat > /tmp/t5-account-qsort-probe.c <<'C'
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
gcc -static -Werror /tmp/t5-account-qsort-probe.c -o /tmp/t5-account-qsort-probe > /workspace/proof/toolchain/qsort-link.log 2>&1
/tmp/t5-account-qsort-probe
python3 -B control/Tools/PinkhaNativeDerived/test_run_t5_pairs_ci.py > proof/toolchain/pair-ci-controls.log 2>&1
cat proof/toolchain/pair-ci-controls.log
python3 -B control/Tools/PinkhaNativeDerived/run_t5_account_pairs_ci.py \
  --source source --heart-old heart-old --heart-new heart-new \
  --work pair-work --artifacts artifacts \
  --evidence "proof/$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT/account-pairs"

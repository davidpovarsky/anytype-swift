#!/bin/sh
# Run only inside the pinned official Go/Alpine image for this disposable CI job.
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
for tree in control source heart; do
  git config --global --add safe.directory "/workspace/$tree"
done
cat > /tmp/t5-qsort-probe.c <<'C'
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
gcc -static -Werror /tmp/t5-qsort-probe.c -o /tmp/t5-qsort-probe > /workspace/proof/toolchain/qsort-link.log 2>&1
/tmp/t5-qsort-probe
python3 control/Tools/PinkhaNativeDerived/test_run_t5_coverage_ci.py > proof/toolchain/ci-controller.log 2>&1
cat proof/toolchain/ci-controller.log
python3 control/Tools/PinkhaNativeDerived/run_t5_coverage_ci.py \
  --source source --heart heart --component "$T5_COMPONENT" \
  --evidence "proof/$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT/$T5_COMPONENT"

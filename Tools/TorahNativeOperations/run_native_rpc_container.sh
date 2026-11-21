#!/bin/sh
set -eu
apk add --no-cache python3 git build-base > /workspace/evidence/toolchain/apk-install.log 2>&1
git config --global --add safe.directory /workspace/control
git config --global --add safe.directory /workspace/heart
go version > /workspace/evidence/toolchain/go-version.txt
gcc --version > /workspace/evidence/toolchain/compiler.txt
gcc -dumpmachine > /workspace/evidence/toolchain/compiler-target.txt
apk info -v musl musl-dev gcc g++ python3 > /workspace/evidence/toolchain/packages.txt
cat > /workspace/work/qsort-probe.c <<'EOF'
#define _GNU_SOURCE
#include <stdlib.h>
static int cmp(const void *a, const void *b, void *arg) { return *(const int*)a - *(const int*)b; }
int main(void) { int values[] = {2,1}; qsort_r(values, 2, sizeof(int), cmp, NULL); return values[0] != 1; }
EOF
gcc -static /workspace/work/qsort-probe.c -o /workspace/work/qsort-probe > /workspace/evidence/toolchain/qsort-link.log 2>&1
/workspace/work/qsort-probe
case "${RPC_STAGE:-test}" in test|account) ;; *) exit 2 ;; esac
exec python3 -B /workspace/control/Tools/TorahNativeOperations/run_native_rpc.py "${RPC_STAGE:-test}" \
  --control /workspace/control --heart-source /workspace/heart --work /workspace/work \
  --evidence /workspace/evidence --expected-app-sha "$EXPECTED_APP_SHA" \
  --rpc-profile "${RPC_PROFILE:-retained-v1}"

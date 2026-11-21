#!/bin/sh
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
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0=/workspace/control
export GIT_CONFIG_KEY_1=safe.directory
export GIT_CONFIG_VALUE_1=/workspace/heart
export GIT_CONFIG_KEY_2=safe.directory
export GIT_CONFIG_VALUE_2=/workspace/source
python3 -B control/Tools/PinkhaNativeDerived/t5_signed_revocation.py \
  --control control --source source --heart heart --work work --evidence evidence

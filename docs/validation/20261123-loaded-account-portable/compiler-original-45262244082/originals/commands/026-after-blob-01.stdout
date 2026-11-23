#!/bin/sh
# Compiler-package acquisition only. No project source, Go, or native test is mounted.
set -eu
umask 022
test "$(cat /etc/alpine-release)" = "3.24.4"
test "$(apk --print-arch)" = "aarch64"
test "$(sha256sum /etc/apk/repositories | cut -d ' ' -f 1)" = "7b8b3e6fe030eeb4ee7619b42c9419aa846bff1c632442d3f00ed9fb97c6fa36"
test "$(sha256sum /lib/apk/db/installed | cut -d ' ' -f 1)" = "da766c29d2a171e8b2688c8eb215f47a514023a788775a9b6a42a27875d14e3c"
mkdir /out/packages /out/index-cache /out/base-keys
cp /etc/apk/keys/*.pub /out/base-keys/
cp /etc/apk/repositories /out/repositories.txt
cp /etc/alpine-release /out/alpine-release.txt
cp /lib/apk/db/installed /out/base-installed.txt
apk --version > /out/apk-version.txt
printf 'update\n' >> /out/phases.txt
apk --cache-dir /out/index-cache update > /out/update.log 2>&1
(cd /out/index-cache; find . -type f -exec sha256sum '{}' ';' | sort) > /out/index-before.sha256
printf 'fetch-recursive\n' >> /out/phases.txt
apk --cache-dir /out/index-cache fetch --recursive --output /out/packages gcc g++ musl-dev binutils > /out/fetch.log 2>&1
(cd /out/index-cache; find . -type f -exec sha256sum '{}' ';' | sort) > /out/index-after.sha256
cmp /out/index-before.sha256 /out/index-after.sha256
printf 'verify-signatures\n' >> /out/phases.txt
apk --no-network verify /out/packages/*.apk > /out/verify.log 2>&1
test "$(sha256sum /lib/apk/db/installed | cut -d ' ' -f 1)" = "da766c29d2a171e8b2688c8eb215f47a514023a788775a9b6a42a27875d14e3c"
printf 'acquisition-complete\n' >> /out/phases.txt
